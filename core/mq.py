import pika

class MQ(object):
    def __init__(self, type, config):
        """
        NOTE: for multiprocessing with ouka separate chanel should be used for each process or threaded
        http://lists.rabbitmq.com/pipermail/rabbitmq-discuss/2013-September/030535.html
        """
        self.config = config
        if type == 'c': # consumer
            self.inConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.config.host))
        elif type == "s": #sender
            self.outConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.config.host))
        elif type == 'm': # mixed
            self.inConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.config.host))
            self.outConnection = pika.BlockingConnection(pika.ConnectionParameters(host=self.config.host))

    def initInChannel(self):
        try:
            inChannel = self.inConnection.channel()
            inChannel.queue_declare(queue=self.config.inqueue)
        except pika.exceptions.ConnectionClosed:
            inChannel = None
        return inChannel

    def initOutChannel(self):
        try:
            outChannel = self.outConnection.channel()
            outChannel.queue_declare(queue=self.config.outqueue)
        except pika.exceptions.ConnectionClosed:
            outChannel = None
        return outChannel

    def sendMessage(self, conn, msg):
        getattr (conn, (basic_publish(exchange='', routing_key=self.config.outqueue, body=msg)))
