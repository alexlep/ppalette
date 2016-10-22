import json
import threading as mpt
from multiprocessing import Process, Manager
#from Queue import Queue
import signal
#import multiprocessing as mp
from tools import Message, executeProcess, executeProcessViaSSH, resolveIP
from sshexecutor import SSHConnection

class inChannelProcess(Process):
    def __init__(self, mqChannel):
        super(inChannelProcess, self).__init__()
        self.name = 'mqInChannelThread'
        self.mqChannel = mqChannel
        self.daemon = True

    def run(self):
        print '[*] Waiting for messages. To exit press CTRL+C'
        self.mqChannel.start_consuming()
        print "TADADADA"

    def stop(self):
        print '[*] Stopping consumer'
        self.mqChannel.stop_consuming()
        print 'stopped consuming'
        self.mqChannel.close()
        print 'closed channel'

class Worker(mpt.Thread):
    """
    http://jhshi.me/2015/12/27/handle-keyboardinterrupt-in-python-multiprocessing/index.html
    """
    def __init__(self, serviceType, pQueue, mqChannel, mqQueueName, logger, checks = {}):
        super(Worker, self).__init__()
        self.pQueue = pQueue
        self.logger = logger
        self.checks = checks
        self.mqChannel = mqChannel
        self.mqQueueName = mqQueueName
        self.serviceType = serviceType
        self.workingMode = True

    def decodeJob(self, item):
        try:
            data = json.loads(item)
            job = Message(data)
        except KeyError as ke:
            print "Cannot find value in decoded json: {0}".format(ke)
            self.logger.warning("Error while decoding JSON. Problematic JSON is {0}".format(item))
            job = None
        return job

    def checkPluginAvailability(self, task):
        try:
            executor = self.checks[task.script]
        except:
            print 'Plugin {0} not found in configuration'.format(task.script)
            self.logger.warning('Plugin {0} not found in configuration'.format(task.script))
            executor = None
        return executor

    def prepareCommand(self, task, executor):
        ip = '' if task.ssh_wrapper else task.ipaddress
        if not task.params:
            command = "{0} {1}".format(executor, ip)
        else:
            command = "{0} {1} {2}".format(executor, task.params, ip)
        return command

    def run(self):
        while self.workingMode:
            try:
                print 'running', self.name
                jobMessage = self.pQueue.get(True)
                if self.serviceType == 'red':
                    msg = jobMessage
                elif 'violet':
                    msg = self.performJob(jobMessage)
                self.sendMessage(msg)
            except Exception as e:
                #self.shutdown()
                print 'got interruption: {}'.format(e)
        return

    def performJob(self, jobMessage):
        job = self.decodeJob(jobMessage)
        if job.type == 'check':
            result = self.executeCheck(job)
        elif 'task':
            result = self.executeCommonTask(job)
        if job.type == 'check':
            self.logger.info('Worker {0} successfully executed {1} for host {2} (ip:{3})'.format(self.name, result.script, result.hostname, result.ipaddress))
        elif 'task':
            self.logger.info('Worker {0} successfully executed {1} for ip:{2})'.format(self.name, result.action, result.ipaddress))
        return json.dumps(result.__dict__)

    def sendMessage(self, msg):
        #print msg
        self.mqChannel.basic_publish(exchange='', routing_key=self.mqQueueName, body=msg)

    def executeCheck(self, check):
        executor = self.checkPluginAvailability(check)
        if not executor:
            return
        command = self.prepareCommand(task = check, executor = executor)
        if check.ssh_wrapper:
            output = executeProcessViaSSH(command, check)
        else:
            output = executeProcess(command, check)
        return output

    def executeCommonTask(self, task):
        if task.action == 'discovery':
            command = self.prepareDiscoveryCommand(task.ipaddress)
            output = executeProcess(command, task)
            output.hostname = resolveIP(task.ipaddress)
        return task

    def prepareDiscoveryCommand(self, ip):
        return "ping -c1 -W1 {0}".format(ip)

class Factory(object):
    inWorker = False
    def __init__(self, serviceType, workers_count, mq_out_queue, mq_handler, logger, checks = {}):
        self.processQueue = Manager().Queue(workers_count)
        self.mqOutQueue = mq_out_queue
        self.logger = logger
        self.checks = checks
        self.MQ = mq_handler
        self.workers = self.prepareWorkersList(workers_count, serviceType)

    def prepareWorkersList(self, procCount, serviceType):
        return [ Worker(pQueue = self.processQueue,
                        serviceType = serviceType,
                        mqChannel = self.MQ.initOutChannel(),
                        mqQueueName = self.mqOutQueue,
                        logger = self.logger,
                        checks = self.checks) for _ in range(procCount) ]

    def startWork(self):
        for w in self.workers: # start each worker for executing plugins
            w.setDaemon(True)
            w.start()

    def stopWork(self):
        for w in self.workers: # start each worker for executing plugins
            w.workingMode = False

    def goHome(self):
        self.stopWork()
        if self.inWorker:
            self.inWorker.stop()
            self.inWorker.join(1)
            if self.inWorker.is_alive():
                self.inWorker.terminate()
        #self.processQueue.join()
        for w in self.workers:
            w.mqChannel.close()
            print w.name, ' closed'
            w.join(1)
            print w.name, " joined"
            print w.isAlive()
