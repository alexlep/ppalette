# -*- coding: utf-8 -*-
import pika, json, sys, os, signal, time
import multiprocessing as mp
from core.mq import MQ
from core import tools

violetConfig = './config/violet_config.json'

class Worker(mp.Process):
    """
    http://jhshi.me/2015/12/27/handle-keyboardinterrupt-in-python-multiprocessing/index.html
    """
    def __init__(self, pQueue, mqChannel, mqQueueName, logger, checks):
        super(Worker, self).__init__()
        self.pQueue = pQueue
        self.logger = logger
        self.checks = checks
        self.mqChannel = mqChannel
        self.mqQueueName = mqQueueName

    def decodeJob(self, item):
        try:
            data = json.loads(item)
            job = tools.draftClass(data)
        except KeyError as ke:
            print "Cannot find value in decoded json: {0}".format(ke)
            self.logger.warning("Error while decoding JSON. Problematic JSON is {0}".format(item))
            job = None
        return job

    def checkPluginAvailability(self, task):
        try:
            executor = self.checks[task.script]
        except:
            print 'Plugin {0} not found in configuration'.format(task.plugin)
            self.logger.warning('Plugin {0} not found in configuration'.format(task.plugin))
            executor = None
        return executor

    def prepareCommand(self, task, executor):
        if not task.params:
            command = "{0} {1}".format(executor, task.ipaddress)
        else:
            command = "{0} {1} {2}".format(executor, task.params, task.ipaddress)
        return command

    def run(self):
        try:
            while True:
                jobMessage = self.pQueue.get(True)
                job = self.decodeJob(jobMessage)
                if job.type == 'check':
                    result = self.executeCheck(job)
                elif 'task':
                    result = self.executeCommonTask(job)
                msg = json.dumps(result.__dict__)
                print msg
                self.mqChannel.basic_publish(exchange='', routing_key=self.mqQueueName, body=msg)
                if job.type == 'check':
                    self.logger.info('Worker {0} successfully executed {1} for host {2} (ip:{3})'.format(self.pid, result.script, result.hostname, result.ipaddress))
                elif 'task':
                    self.logger.info('Worker {0} successfully executed {1} for ip:{2})'.format(self.pid, result.action, result.ipaddress))
        except KeyboardInterrupt:
            print "KeyboardInterrupt for {0}".format(os.getpid())
            return

    def executeCheck(self, check):
        executor = self.checkPluginAvailability(check)
        if not executor:
            return
        command = self.prepareCommand(task = check, executor = executor)
        output = tools.executeProcess(command)
        check.updateWithDict(output)
        return check

    def executeCommonTask(self, task):
        if task.action == 'discovery':
            command = self.prepareDiscoveryCommand(task.ipaddress)
            output = tools.executeProcess(command)
            task.hostname = tools.resolveIP(task.ipaddress)
            task.updateWithDict(output)
        return task

    def prepareDiscoveryCommand(self, ip):
        return "ping -c1 -W1 {0}".format(ip)

class Violet(object):
    def __init__(self, configFile):
        self.config = tools.parseConfig(configFile)
        self.logConfig = tools.draftClass(self.config.log)
        self.queueConfig = tools.draftClass(self.config.queue)
        self.log = tools.initLogging(self.logConfig) # init logging
        self.MQ = MQ('m', self.queueConfig)
        self.inChannel = self.MQ.initInChannel() # from red
        if (not self.inChannel):
            print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
            sys.exit(1)
        self.inChannel.basic_consume(self.callback, queue=self.queueConfig.inqueue, no_ack=True)
        self.cProc =  self.prepareWorkerForMQ()# separate consumer process
        self.PQ = mp.Queue()
        self.checks = self.preparePluginDict()
        self.workers = self.prepareWorkersList()

    def prepareWorkerForMQ(self):
        return mp.Process(target=self.startConsumer)

    def preparePluginDict(self):
        tdict = {}
        for path in self.config.plugin_paths.split(';'):
            if path:
                try:
                    scripts = os.listdir(path)
                except OSError as (errno, strerror):
                    self.log.warning("Unable to access directory {0} to get plugins. Reason: {1}.".format(path, strerror))
                    continue
                if not len(scripts):
                    self.log.warning("No plugins found in directory {0} directory is empty. Skipping it.".format(path))
                else:
                    for script in scripts:
                        tdict[script] = "{0}/{1}".format(path, script)
        return tdict

    def prepareWorkersList(self):
        tworkers = []
        for _ in range(self.config.process_count): # workers for executing checks
            tworkers.append(Worker(pQueue = self.PQ,
                            mqChannel = self.MQ.initInChannel(),
                            mqQueueName = self.queueConfig.outqueue,
                            logger = self.log,
                            checks = self.checks))
        return tworkers

    def startConsumer(self):
        print(' [*] Waiting for messages. To exit press CTRL+C')
        try:
            self.inChannel.start_consuming()
        except:
            print "ABORTING VIOLET LISTENER"

    def startProcesses(self):
        for w in self.workers: # start each worker for executing plugins
            w.daemon = True
            w.start()
        self.cProc.start() # start separate consumer process

    def callback(self, ch, method, properties, body):
        self.PQ.put(body)

    def destroy(self):
        self.inChannel.close()
        for w in self.workers:
            try:
                w.mqChannel.close()
                w.join()
            except:
                w.terminate()

if __name__ =='__main__':
    VioletApp = Violet(violetConfig)
    VioletApp.startProcesses()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        VioletApp.destroy()

    print "aborted with your little filthy hands!"
