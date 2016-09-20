import pika

class MQ(object):
    def __init__(self, type, conf):
        self.conf = conf
        self.MQhost = self.conf['host']
        if type == 'c': # consumer
            self.initConsumer()
        elif type == "s": #sender
            self.initSender()
        elif type == 'm': # mixed
            self.initConsumer()
            self.initSender()

    def initConsumer(self):
        self.inQueue = self.conf['inqueue']
        self.inConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.MQhost))
        self.inChannel = self.inConnection.channel()
        self.inChannel.queue_declare(queue=self.inQueue)

    def initSender(self):
        self.outQueue = self.conf['outqueue']
        self.outConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.MQhost))
        self.outChannel = self.outConnection.channel()
        self.outChannel.queue_declare(queue=self.outQueue)

    def sendMessage(self, msg):
        self.outChannel.basic_publish(exchange='', routing_key=self.outQueue, body=msg)
