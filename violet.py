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

    def prepareTask(self, item):
        try:
            data = json.loads(item)
            task = tools.createClass(data)
        except KeyError as ke:
            print "Cannot find value in decoded json: {0}".format(ke)
            self.logger.WARN("Error while decoding JSON. Problematic JSON is {0}".format(item))
            task = None
        return task

    def checkPluginAvailability(self, task):
        try:
            executor = self.checks[task.plugin]
        except:
            print 'Plugin {0} not found in configuration'.format(task.plugin)
            self.logger.WARN('Plugin {0} not found in configuration'.format(task.plugin))
            executor = None
        return executor

    def prepareCommand(self, task, executor):
        if not task.params:
            command = "{0} {1}".format(executor, task.ip)
        else:
            command = "{0} {1} {2}".format(executor, task.params, task.ip)
        return command

    def run(self):
        while True:
            print "working", os.getpid()
            item = self.pQueue.get(True)
            task = self.prepareTask(item)
            if not task:
                continue
            executor = self.checkPluginAvailability(task)
            if not executor:
                continue
            command = self.prepareCommand(task = task, executor = executor)
            output = tools.executeProcess(command)
            output['ip'] = task.ip
            output['taskid'] = task.taskid
            msg = json.dumps(output)
            self.mqChannel.basic_publish(exchange='', routing_key=self.mqQueueName, body=msg)
            print "finished", os.getpid()

class Violet(object):
    def __init__(self, configFile):
        self.config = tools.parseConfig(configFile)
        self.logConfig = tools.createClass(self.config.log)
        self.queueConfig = tools.createClass(self.config.queue)
        self.log = tools.initLogging(self.logConfig) # init logging
        self.MQ = MQ('m', self.queueConfig)
        self.inChannel = self.MQ.initInChannel() # from red
        if (not self.inChannel):
            print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
            sys.exit(1)
        self.inChannel.basic_consume(self.callback, queue=self.queueConfig.inqueue, no_ack=True)
        self.cProc = mp.Process(target=self.startConsumer) # separate consumer process
        self.PQ = mp.Queue()
        self.workers = []
        for _ in range(self.config.process_count): # workers for executing checks
            self.workers.append (Worker(pQueue = self.PQ,
                                mqChannel = self.MQ.initInChannel(),
                                mqQueueName = self.queueConfig.outqueue,
                                logger = self.log,
                                checks = self.config.checks))

    def startConsumer(self):
        print(' [*] Waiting for messages. To exit press CTRL+C')
        self.inChannel.start_consuming()

    def startProcesses(self):
        for w in self.workers: # start each worker for executing plugins
            w.daemon = True
            w.start()
        self.cProc.start() # start separate consumer process

    def callback(self, ch, method, properties, body):
        self.PQ.put(body)

    def destroy(self):
        self.cProc.close()

if __name__ =='__main__':
    VioletApp = Violet(violetConfig)
    #try:
    VioletApp.startProcesses()
    #    print "lalala"
    #except:
    #    print "OOOOOOOOOOOOPS"
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        VioletApp.destroy()

    print "aborted with your little filthy hands!"
