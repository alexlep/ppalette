# -*- coding: utf-8 -*-
#import threading as mpt
import multiprocessing as mpt
import signal
from threading import Thread
from multiprocessing import Manager
from datetime import datetime
from pika.exceptions import BodyTooLongError
import tools
from sshexecutor import SSHConnection
from rabbitpy import Message

class outChannelThread(Thread):
    def __init__(self, mqChannel, mqQueue, pQueue):
        super(outChannelThread, self).__init__()
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

class inChannelThread(Thread):
    def __init__(self, mqQueue, pQueue):
        super(inChannelThread, self).__init__()
        self.name = 'mqInChannelThread'
        #self.mqChannel = mqChannel
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
                    self.in_process_queue.put(message.body)
                    if counter == 1000:

                        print datetime.now(), self.in_process_queue.qsize(), 'mqsize' ,len(self.mqQueue)
                        counter = 0
            #print message.json()
            """
                        try:
                for method_frame, properties, body in self.mqChannel.consume(self.mqQueue, no_ack=True):
                    self.in_process_queue.put(body)
                    #self.mqChannel.basic_ack(method_frame.delivery_tag)
                    counter += 1
                    #print counter
                    if counter == 1000:
                        print datetime.now(), self.in_process_queue.qsize()
                        counter = 0
            except AttributeError as ae:
                print ae
                print body, type(body)
            except BodyTooLongError as btle:
                print body
                print "GOT BTLE Exception", btle
            except Exception as e:
                print e
                pass"""


    def stop(self):
        print '[*] Stopping consumer'
        self.mqChannel.stop_consuming()
        print 'stopped consuming'
        self.mqChannel.close()
        print 'closed channel'

class Worker(mpt.Process):
    """
    http://jhshi.me/2015/12/27/handle-keyboardinterrupt-in-python-multiprocessing/index.html
    """
    def __init__(self, serviceType, InPQueue, OutPQueue, logger, checks = {}):
        super(Worker, self).__init__()
        self.in_process_queue = InPQueue
        self.out_process_queue = OutPQueue
        self.logger = logger
        self.checks = checks
        self.serviceType = serviceType
        self.workingMode = True

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
                output = tools.executeProcessViaSSH(job)
            else:
                output = tools.executeProcess(job)
            self.logger.info('Worker {0} successfully executed {1} for host {2} (ip:{3})'.format(self.name, output.script, output.hostname, output.ipaddress))
        elif job.type == 'task':
            if job.action == 'discovery':
                output = tools.executeDiscovery(job)
                self.logger.info('Worker {0} successfully executed {1} for ip:{2})'.format(self.name, output.action, output.ipaddress))
        return output

class Factory(object):
    def __init__(self, serviceType, workers_count, mq_config, mq_handler, logger, checks = {}):
        self.in_process_queue_f = Manager().Queue()
        self.out_process_queue_f = Manager().Queue()
        self.mqOutQueue = mq_config.outqueue
        self.mqInQueue = mq_config.inqueue
        self.logger = logger
        self.checks = checks
        self.MQ = mq_handler
        self.workers = self._prepareWorkersList(workers_count, serviceType)
        self.in_mq_threads = list()
        self.out_mq_threads = list()

    def _prepareWorkersList(self, procCount, serviceType):
        print procCount
        return [ Worker(InPQueue = self.in_process_queue_f,
                        OutPQueue = self.out_process_queue_f,
                        serviceType = serviceType,
                        logger = self.logger,
                        checks = self.checks) for _ in range(procCount) ]

    def startWork(self):
        for w in self.workers: # start each worker for executing plugins
            w.daemon = True
            w.start()
        for c in self.in_mq_threads: # start each worker for executing plugins
            c.daemon = True
            c.start()
            print ' in started'
        for s in self.out_mq_threads: # start each worker for executing plugins
            s.daemon = True
            s.start()

    def stopWork(self):
        for w in self.workers: # start each worker for executing plugins
            w.workingMode = False
        for c in self.in_mq_threads: # start each worker for executing plugins
            #c.in_process_queue.put("break")
            c.active = False
        for s in self.out_mq_threads: # start each worker for executing plugins
            #s.out_process_queue.put("break")
            s.active = False

    def goHome(self):
        self.stopWork()
        for c in self.in_mq_threads: # start each worker for executing plugins
            if c.isAlive():
                #c.mqQueue.close()
                c.join()
        for s in self.out_mq_threads: # start each worker for executing plugins
            if s.isAlive():
                s.mqChannel.close()
                s.join()
        for w in self.workers:
            w.join(1)
            print w.name, " joined"
