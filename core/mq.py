# -*- coding: utf-8 -*-
import pika

class MQ(object):
    def __init__(self, config):
        """
        NOTE: for multiprocessing with ouka separate chanel should be used for each process or threaded
        http://lists.rabbitmq.com/pipermail/rabbitmq-discuss/2013-September/030535.html
        """
        self.config = config
        self.url = pika.URLParameters('amqp://guest:guest@{0}:5672/%2F?backpressure_detection=t'.format(self.config.host))
        self.Connection = pika.BlockingConnection(self.url)#pika.ConnectionParameters(host=self.config.host))

    def initInChannelElse(self):
        try:
            inChannel = self.Connection.channel()
            inChannel.queue_declare(queue=self.config.inqueue)
            #inChannel.basic_qos(prefetch_count=300)
            #inChannel.basic_consume(fun, queue=self.config.inqueue, no_ack=True)
        except pika.exceptions.ConnectionClosed:
            inChannel = None
        return inChannel

    def initOutChannel(self):
        try:
            outChannel = self.Connection.channel()
            outChannel.queue_declare(queue=self.config.outqueue)
        except pika.exceptions.ConnectionClosed:
            outChannel = None
        return outChannel
