# -*- coding: utf-8 -*-
import rabbitpy
import logging
import functools
from threading import Thread
from multiprocessing import Process, Manager
from concurrent.futures import ThreadPoolExecutor

import tools
from monitoring.violetstats import Stats
from configs import vLogger

class ProcessingException(Exception):
    def __init__(self, message=None):
        super(ProcessingException, self).__init__(message)
        #self.errors = errors

class Publisher(Thread):
    def __init__(self, ch, qName, pQueue=None, callback=None):
        super(Publisher, self).__init__()
        self.name = 'mqOutChannelThread'
        self.ch = ch
        self.qName = qName
        self.pQueue = pQueue
        self.callback = callback
        self.daemon = True
        self.active = True
        self.counter = 0
        self.max_counter = 0

    def run(self):
        while self.active:
            try:
                if self.pQueue:
                    msg = self.pQueue.get(True)
                elif self.callback:
                    msg = self.callback()
                if msg == 'break':
                    self.active = False
                    self.ch.close()
                    break
                message = rabbitpy.Message(self.ch, msg)
                message.publish('', self.qName)
                self.counter += 1
            except EOFError:
                print self.name, 'IOERROR, expected'
                self.active = False
            except Exception as e:
                print "{}, unexpected".format(e)

    def getProcessedTasksCounter(self):
        if self.counter > self.max_counter:
            self.max_counter = self.counter
        res = (self.counter, self.max_counter)
        self.counter = 0
        return res

    def stop(self):
        self.pQueue.put('break')

class Consumer(Thread):
    def __init__(self, ch, qName, pQueue=None, callback=None):
        super(Consumer, self).__init__()
        self.name = 'mqInChannelThread'
        self.ch = ch
        self.qName = qName
        self.daemon = True
        self.active = True
        self.pQueue = pQueue
        self.callback = callback

    def run(self):
        self.queue = rabbitpy.Queue(self.ch, self.qName)
        for message in self.queue:
            try:
                if self.pQueue:
                    self.pQueue.put(message.body)
                elif self.callback:
                    self.callback(message.body)
                message.ack()
            except Exception as e:
                vLogger.error(e)

    def getMQSize(self):
        return len(self.queue)

    def stop(self):
        self.queue.stop_consuming()

class Worker(Process):
    def __init__(self, inPQueue, outPQueue,
                 tCount, ssh_config, checks):
        super(Worker, self).__init__()
        self.in_process_queue = inPQueue
        self.out_process_queue = outPQueue
        self.tCount = tCount
        self.checks = checks
        self.ssh_config = ssh_config
        self.ssh_config.expandPaths()
        self.workingMode = True
        self.daemon = True

    def run(self):
        with ThreadPoolExecutor(max_workers=self.tCount) as executor:
            while self.workingMode:
                try:
                    jobMessage = self._getMessageFromQueue()
                    if jobMessage == 'exit':
                        vLogger.info('Worker {} received exit message'.\
                                         format(self.name))
                        self.workingMode = False
                        break
                    executor.submit(self.performJob, jobMessage)
                except ProcessingException:
                    pass
                except Exception as e:
                    vLogger.error(e)

    def performJob(self, jobMessage):
        job = self._prepareJobMessage(jobMessage)
        result = self._executeJob(job)
        jresult = result.tojson()
        self._putMessageToQueue(jresult)

    def _prepareJobMessage(self, msg):
        try:
            res = tools.Message(msg, fromJSON=True)
            vLogger.debug('Parsed message {0}, body: {1}'.format(res.message_id,
                                                                 msg))
            return res
        except Exception as e:
            vLogger.warning("Worker {0} is unable " \
                            "to process incoming message. Problematic JSON " \
                            "is {1}".format(self.name, msgBody))
            raise ProcessingException

    def _getMessageFromQueue(self):
        try:
            return self.in_process_queue.get(True)
        except Exception as e:
            vLogger.error("Worker {0} was unable " \
                          "to get message from process query: " \
                          "{1}".format(self.name, e))
            raise ProcessingException

    def _putMessageToQueue(self, message):
        try:
            self.out_process_queue.put(message)
        except Exception as e:
            vLogger.error("Worker {0} was unable " \
                          "to send message to out process query: ",
                          "{1}".format(self.name, e))
            raise ProcessingException


    def _checkPluginAvailability(self, check_script):
        return self.checks[check_script]

    def _executeJob(self, job):
        if job.type == 'check':
            job.executor = self._checkPluginAvailability(job.script)
            if job.ssh_wrapper:
                try:
                    output = tools.executeProcessViaSSH(job, self.ssh_config)
                except IOError as e:
                    vLogger.warning("Unable to execute SSH command " \
                                    "- cannot reach some of configuration " \
                                    "files({0} and {1})!".\
                                    format(self.ssh_config.rsa_key_file,
                                           self.ssh_config.host_key_file))
                    vLogger.warning(e)
            else:
                output = tools.executeProcess(job)
            vLogger.debug("Worker {0} successfully executed " \
                         "{1} for host {2} (ip:{3})".format(self.name,
                                                            output.script,
                                                            output.hostname,
                                                            output.ipaddress))
        elif job.type == 'task':
            if job.action == 'discovery':
                output = tools.executeDiscovery(job)
                vLogger.debug("Worker {0} successfully executed " \
                             "{1} for ip:{2})".format(self.name,
                                                      output.action,
                                                      output.ipaddress))
        return output

    def stop(self):
        self.in_process_queue.put('exit')

class Factory(object):
    def __init__(self, mqConn, config):
        self.mqConn = mqConn
        self.procCount = config.process_count
        self.inQ = config.queue.inqueue
        self.outQ = config.queue.outqueue
        self.config = config
        self.in_queues = self.prepareQueues()
        self.out_queues = self.prepareQueues()
        self.consumers = self.prepareConsumers()
        self.publishers = self.preparePublishers()
        self.workers = self.prepareWorkers()
        self.processedCount = 0
        self.processedCountMax = 0
        self.stats = Stats()
        vLogger.info('Factory initialized successfully')

    def prepareQueues(self):
        return [ Manager().Queue() for _ in range(self.procCount) ]

    def inCallback(self, **kwargs):
        q.put(body)

    def outCallback(self, **kwargs):
        return q.get(True)

    def prepareConsumers(self):
        return [ Consumer(self.mqConn.channel(),
                          self.inQ, Manager().Queue()) \
                          for _ in range(self.procCount) ]

    def preparePublishers(self):
        return [ Publisher(self.mqConn.channel(),
                           self.outQ, Manager().Queue()) \
                           for _ in range(self.procCount) ]

    def prepareWorkers(self):
        return [ Worker(inPQueue=self.consumers[numb].pQueue,
                        outPQueue=self.publishers[numb].pQueue,
                        tCount=self.config.threads_per_process,
                        checks=tools.pluginDict(self.config.plugin_paths),
                        ssh_config=self.config.ssh) \
                        for numb in range(self.procCount) ]

    def startWork(self):
        for numb in range(self.procCount):
            self.publishers[numb].start()
            self.workers[numb].start()
            self.consumers[numb].start()
        vLogger.info('Factory was started')

    def stopWork(self):
        for w in self.workers:
            w.stop()
        for c in self.consumers:
            c.stop()
        for p in self.publishers:
            p.stop()

    def goHome(self):
        self.stopWork()
        for w in self.workers:
            w.join(1)
            vLogger.info("{} joined".format(w.name))

    def gatherStats(self):
        self.stats.worker_count = len(self.workers)
        self.stats.worker_alive = self._getAliveCount(self.workers)
        self.stats.consumers_count = len(self.consumers)
        self.stats.consumers_alive = self._getAliveCount(self.consumers)
        self.stats.publishers_count = len(self.publishers)
        self.stats.publishers_alive = self._getAliveCount(self.publishers)
        self.stats.input_queue_size = self.consumers[0].getMQSize()
        self.stats.throughput, self.stats.max_throughput = self.\
                                                    _getProcessedTasksAmount()
        self.stats.last_update_time = tools.dateToStr()
        return self.stats

    def _getAliveCount(self, elemList):
        alive_count = 0
        for _ in elemList:
            if _.is_alive():
                alive_count += 1
        return alive_count

    def _getProcessedTasksAmount(self):
        for p in self.publishers:
            c, m  = p.getProcessedTasksCounter()
            self.processedCount += c
            self.processedCountMax += m
        res = (self.processedCount, self.processedCountMax)
        self.processedCount, self.processedCountMax = (0,0)
        return res
