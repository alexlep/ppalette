import pika, json, sys, multiprocessing, os, signal
from core.mq import MQ
from core import tools
violetConfig = './config/violet_config.json'

class Violet(object):
    def __init__(self, configFile):
        self.config = tools.parseConfig(configFile)
        self.logConfig = tools.createClass(self.config.log)
        self.queueConfig = tools.createClass(self.config.queue)
        self.log = tools.initLogging(self.logConfig) # init logging
        self.MQ = MQ('m', self.queueConfig)
        if (not self.MQ.inChannel) or (not self.MQ.outChannel):
            print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
            sys.exit(1)
        self.MQ.inChannel.basic_consume(self.callback, queue=self.queueConfig.inqueue, no_ack=True)
        self.PQ = multiprocessing.Queue()
        self.PPool = multiprocessing.Pool(10, self.executeCheck,(self.PQ,))

    def startConsumer(self):
        print(' [*] Waiting for messages. To exit press CTRL+C')
        self.MQ.inChannel.start_consuming()

    def executeCheck(self, queue): #plugin, params, ip):
        while True:
            item = queue.get(True)
            try:
                data = json.loads(item)
                task = tools.createClass(data)
            except KeyError as ke:
                print "Cannot find value in decoded json: {0}".format(ke)
                self.log.WARN("Error while decoding JSON. Problematic JSON is {0}".format(item))
                continue
            #plugin, params, ip = data['plugin'], data['params'], data['ip']
            try:
                executor = self.config.checks[task.plugin]
            except:
                print 'Plugin {0} not found in configuration'.format(task.plugin)
                self.log.WARN('Plugin {0} not found in configuration'.format(task.plugin))
            print task.params, data
            print type(task.params)
            if not task.params:
                command = "{0} {1}".format(executor, task.ip)
            else:
                command = "{0} {1} {2}".format(executor, task.params, task.ip)
            output = tools.executeProcess(command)
            output['ip'] = task.ip
            output['taskid'] = task.taskid
            msg = json.dumps(output)
            self.MQ.sendMessage(msg)
        #os.kill(os.getpid(), signal.SIGTERM)
        #return output

    def callback(self, ch, method, properties, body):
        self.PQ.put(body)

if __name__ =='__main__':
    VioletApp = Violet(violetConfig)
    try:
        VioletApp.startConsumer()
    except KeyboardInterrupt:
        print "aborted with your little filthy hands!"
