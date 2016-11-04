# -*- coding: utf-8 -*-
import signal
from threading import Thread
from multiprocessing import Process, Manager
from datetime import datetime
import tools
from rabbitpy import Message

class Sender(Thread):
    def __init__(self, mqChannel, mqQueue, pQueue):
        super(Sender, self).__init__()
        self.name = 'mqOutChannelThread'
        self.mqChannel = mqChannel
        self.mqQueue = mqQueue
        self.daemon = True
        self.active = True
        self.out_process_queue = pQueue

    def run(self):
        counter = 0
        while self.active:
            try:
                msg = self.out_process_queue.get(True)
                if msg == 'break': break
                message = Message(self.mqChannel, msg)
                message.publish('', self.mqQueue)
                counter += 1
                if counter == 1000:
                    print datetime.now()
                    counter = 0
            except EOFError:
                print self.name, 'IOERROR, expected'
                self.active = False

    def stop(self):
        print '[*] Stopping consumer'
        self.mqChannel.stop_consuming()
        print 'stopped consuming'
        self.mqChannel.close()
        print 'closed channel'

class Consumer(Thread):
    def __init__(self, mqQueue, pQueue):
        super(Consumer, self).__init__()
        self.name = 'mqInChannelThread'
        self.mqQueue = mqQueue
        self.daemon = True
        self.active = True
        self.in_process_queue = pQueue

    def run(self):
        counter = 0
        print "ololo"
        while self.active:
            if len(self.mqQueue) > 0:
                message = self.mqQueue.get(acknowledge=False)
                if message: # sometimes message is None... to check rabbitpy issues
                    counter += 1
                    try:
                        self.in_process_queue.put(message.body)
                    except IOError:
                        self.active = False
                        break
                    if counter == 1000:
                        print datetime.now(), self.in_process_queue.qsize(), 'mqsize' ,len(self.mqQueue)
                        counter = 0

    def stop(self):
        print '[*] Stopping consumer'
        self.mqChannel.stop_consuming()
        print 'stopped consuming'
        self.mqChannel.close()
        print 'closed channel'

class Worker(Process):
    """
    http://jhshi.me/2015/12/27/handle-keyboardinterrupt-in-python-multiprocessing/index.html
    """
    def __init__(self, InPQueue, OutPQueue, logger, ssh_config, checks = {}):
        super(Worker, self).__init__()
        self.in_process_queue = InPQueue
        self.out_process_queue = OutPQueue
        self.logger = logger
        self.checks = checks
        self.workingMode = True
        self.ssh_config = ssh_config

    def run(self):
        counter = 0
        while self.workingMode:
            try:
                jobMessage = self._getMessageFromQueue()
                reply = self._performJob(jobMessage)
                self._putMessageToQueue(reply)
                counter += 1
                if counter == 100:
                    print "{0} Another 100 messages were sent by thread {1}".format(datetime.now(), self.name)
                    counter = 0
            except AssertionError as ae:
                pass
            except Exception as e:
                print "Unhandled Exception:", e
                pass
        print 'exit'
        return

    def _checkPluginAvailability(self, check_script):
        try:
            return self.checks[check_script]
        except:
            print 'Plugin {0} not found in configuration'.format(check_script)
            self.logger.warning('Plugin {0} not found in configuration'.format(check_script))
            executor = None

    def _getMessageFromQueue(self):
        try:
            return self.in_process_queue.get(True)
        except Exception as e:
            print "Exception during receiving message via process queue", e
            self.logger.error('Worker {0} was unable to get message from process query'.format(self.name))
            raise AssertionError

    def _putMessageToQueue(self, message):
        try:
            self.out_process_queue.put(message)
        except Exception as e:
            print "Exception during sending message to out process queue", e
            self.logger.error('Worker {0} was unable to send message to out process query'.format(self.name))
            raise AssertionError

    def _prepareJobMessage(self, data):
        try:
            return tools.Message(data, fromJSON = True)
        except Exception as e:
            print "Cannot find value in decoded json: {0}".format(e)
            self.logger.warning("Worker {0} is unable to process incomming message. Problematic JSON is {1}".format(self.name, data))
            raise AssertionError

    def _performJob(self, jobMessage):
        job = self._prepareJobMessage(jobMessage)
        result = self._executeJob(job)
        try:
            jresult = result.tojson()
        except UnicodeDecodeError:
            result.removeWrongASCIISymbols()
            jresult = result.tojson()
        return jresult

    def _executeJob(self, job):
        if job.type == 'check':
            job.executor = self._checkPluginAvailability(job.script)
            if job.ssh_wrapper:
                try:
                    output = tools.executeProcessViaSSH(job, self.ssh_config)
                except IOError:
                    print 'Unable to execute SSH command - cannot reach some of ssh configuration files({0} and {1})!'.format(self.ssh_config.rsa_key_file, self.ssh_config.host_key_file)
                    self.logger.warning('Unable to execute SSH command - cannot reach some of ssh configuration files({0} and {1})!'.format(self.ssh_config.rsa_key_file, self.ssh_config.host_key_file))
            else:
                output = tools.executeProcess(job)
            self.logger.info('Worker {0} successfully executed {1} for host {2} (ip:{3})'.format(self.name, output.script, output.hostname, output.ipaddress))
        elif job.type == 'task':
            if job.action == 'discovery':
                output = tools.executeDiscovery(job)
                self.logger.info('Worker {0} successfully executed {1} for ip:{2})'.format(self.name, output.action, output.ipaddress))
        return output

class Factory(object):
    def __init__(self): #mq_config, mq_handler, logger, checks = {}):
        self.in_process_queue_f = Manager().Queue()
        self.out_process_queue_f = Manager().Queue()
        self.senders = list()
        self.consumers = list()

    def prepareWorkers(self, procCount, logger, checks, ssh_config):
        self.workers =  [ Worker(InPQueue = self.in_process_queue_f,
                        OutPQueue = self.out_process_queue_f,
                        logger = logger,
                        checks = checks,
                        ssh_config = ssh_config) for _ in range(procCount) ]

    def startWork(self):
        for w in self.workers: # start each worker for executing plugins
            w.daemon = True
            w.start()
        for c in self.consumers: # start each worker for executing plugins
            c.daemon = True
            c.start()
            print ' in started'
        for s in self.senders: # start each worker for executing plugins
            s.daemon = True
            s.start()

    def stopWork(self):
        for w in self.workers: # start each worker for executing plugins
            w.workingMode = False
        for c in self.consumers: # start each worker for executing plugins
            #c.in_process_queue.put("break")
            c.active = False
        for s in self.senders: # start each worker for executing plugins
            #s.out_process_queue.put("break")
            s.active = False

    def goHome(self):
        self.stopWork()
        for c in self.consumers: # start each worker for executing plugins
            if c.isAlive():
                #c.mqQueue.close()
                c.join()
        for s in self.senders: # start each worker for executing plugins
            if s.isAlive():
                s.mqChannel.close()
                s.join()
        for w in self.workers:
            w.join(1)
            print w.name, " joined"
