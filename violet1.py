import pika, json, sys, subprocess
from core.mq import MQ
from core import tools
violetConfig = './config/violet_config.json'

class Violet(object):
    def __init__(self, configFile):
        self.configFile = tools.parseConfig(configFile)
        self.checks =  self.configFile['checks']
        self.conf = self.configFile['configuration']
        self.log = tools.initLogging(self.conf['log']) # init logging
        self.MQ = MQ('m', self.conf['queue'])
        self.MQ.inChannel.basic_consume(self.callback, queue=self.MQ.inQueue, no_ack=True)
        print(' [*] Waiting for messages. To exit press CTRL+C')

    def startConsumer(self):
        self.MQ.inChannel.start_consuming()

    def executeCheck(self, plugin, params, ip):
        try:
            executor = self.checks[plugin]
        except:
            print 'Plugin {0} not found in configuration'.format(plugin)
        if not params:
            command = "{0} {1}".format(executor, ip)
        else:
            command = "{0} {1} {2}".format(executor, params, ip)
        output = tools.executeProcess(command)
        output['ip'] = ip
        return output

    def callback(self, ch, method, properties, body):
        print (" [x] Received %r" % body)
        try:
            jbody = json.loads(body)
            output = self.executeCheck(jbody['plugin'], jbody['params'], jbody['ip'])
            output['taskid'] = jbody['taskid']
            msg = json.dumps(output)
            self.MQ.sendMessage(msg) #msg)
        except KeyError as ke:
            print "Cannot find value in decoded json: {0}".format(ke)
        #except Exception as e:
        #    print e


VioletApp = Violet(violetConfig)
try:
    VioletApp.startConsumer()
except KeyboardInterrupt:
    print "aborted with your little filthy hands!"
