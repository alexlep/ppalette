import json
import multiprocessing as mp
from tools import draftClass, executeProcess, executeProcessViaSSH, resolveIP
from sshexecutor import SSHConnection

class Worker(mp.Process):
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

    def decodeJob(self, item):
        try:
            data = json.loads(item)
            job = draftClass(data)
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
        try:
            while True:
                print 'running', self.pid
                jobMessage = self.pQueue.get(True)
                if self.serviceType == 'red':
                    msg = jobMessage
                elif 'violet':
                    msg = self.performJob(jobMessage)
                self.sendMessage(msg)
        except KeyboardInterrupt:
            print "KeyboardInterrupt for {0}".format(self.pid)
        '''except EOFError as eofe:
            print 'Smth is fucked up, caught EOFError in multiprocessing'
            '''
        return


    def performJob(self, jobMessage):
        job = self.decodeJob(jobMessage)
        if job.type == 'check':
            result = self.executeCheck(job)
        elif 'task':
            result = self.executeCommonTask(job)
        if job.type == 'check':
            self.logger.info('Worker {0} successfully executed {1} for host {2} (ip:{3})'.format(self.pid, result.script, result.hostname, result.ipaddress))
        elif 'task':
            self.logger.info('Worker {0} successfully executed {1} for ip:{2})'.format(self.pid, result.action, result.ipaddress))
        return json.dumps(result.__dict__)

    def sendMessage(self, msg):
        print msg
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
    def __init__(self, serviceType, workers_count, mq_out_queue, mq_handler, logger, checks = {}):
        self.processQueue = mp.Manager().Queue()
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
            w.daemon = True
            w.start()

    def goHome(self):
        for w in self.workers:
            try:
                w.mqChannel.close()
                w.join()
            except:
                w.terminate()
