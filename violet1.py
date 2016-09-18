import pika, json, sys, subprocess
from datetime import datetime
config = './config/violet_config.json'

class Violet(object):
    def __init__(self, config):
        self.config = self.parseConfig(config)
        self.checks =  self.config['checks']
        self.conf = self.config['configuration']
        self.MQconf = self.conf['queue']
        self.inQueue = self.MQconf['inqueue']
        self.outQueue = self.MQconf['outqueue']
        self.MQhost = self.MQconf['host']
        self.inConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.MQhost))
        self.outConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.MQhost))
        self.inChannel = self.inConnection.channel()
        self.outChannel = self.outConnection.channel()
        self.inChannel.queue_declare(queue=self.inQueue)
        self.outChannel.queue_declare(queue=self.outQueue)
        self.inChannel.basic_consume(self.callback, queue=self.inQueue, no_ack=True)
        print(' [*] Waiting for messages. To exit press CTRL+C')
        try:
            self.inChannel.start_consuming()
        except KeyboardInterrupt:
            print "aborted with your little filthy hands!"

    def parseConfig(self, config):
        try:
            with open(config) as config_file:
                config_data =  json.load(config_file)
                config_file.close()
            return config_data
        except ValueError as ve:
            print "Error in configuration file {0}: {1}".format(config, ve)
            config_file.close()
            sys.exit(1)
        except IOError as ie:
            print "Error in opening configuration file {0}: {1}".format(config, ie)
            sys.exit(1)

    def executeCheck(self, plugin, params, ip):
        try:
            executor = self.checks[plugin]
        except:
            print 'Plugin {0} not found in configuration'.format(plugin)
        if not params:
            command = "{0} {1}".format(executor, ip)
        else:
            command = "{0} {1} {2}".format(executor, params, ip)
        output = self.executeProcess(command)
        output['ip'] = ip
        return output

    def executeProcess(self, command):
        feedback = {}
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = process.communicate()[0].rstrip() # here subprocess is killed
        try:
            feedback['output'], feedback['details'] = out.split("|")
        except ValueError:
            feedback['output'], feedback['details'] = out, None
        feedback['exitcode'] = process.returncode
        feedback['time'] = datetime.now().strftime("%H:%M:%S:%d:%m:%Y")
        return feedback

    def callback(self, ch, method, properties, body):
        print (" [x] Received %r" % body)
        try:
            jbody = json.loads(body)
            output = self.executeCheck(jbody['plugin'], jbody['params'], jbody['ip'])
            output['taskid'] = jbody['taskid']
            msg = json.dumps(output)
            self.outChannel.basic_publish(exchange='', routing_key=self.outQueue, body=msg) #msg)
        except KeyError as ke:
            print "Cannot find value in decoded json: {0}".format(ke)
        #except Exception as e:
        #    print e


VioletApp = Violet(config)
