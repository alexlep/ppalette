import pika

class MQ(object):
    def __init__(self, type, config):
        self.config = config
        if type == 'c': # consumer
            self.inChannel = self.initConsumer()
        elif type == "s": #sender
            self.outChannel = self.initSender()
        elif type == 'm': # mixed
            self.inChannel = self.initConsumer()
            self.outChannel = self.initSender()

    def initConsumer(self):
        try:
            inConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.config.host))
            inChannel = inConnection.channel()
            inChannel.queue_declare(queue=self.config.inqueue)
        except pika.exceptions.ConnectionClosed:
            inChannel = None
        return inChannel

    def initSender(self):
        try:
            outConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.config.host))
            outChannel = outConnection.channel()
            outChannel.queue_declare(queue=self.config.outqueue)
        except pika.exceptions.ConnectionClosed:
            outChannel = None
        return outChannel

    def sendMessage(self, msg):
        self.outChannel.basic_publish(exchange='', routing_key=self.config.outqueue, body=msg)
