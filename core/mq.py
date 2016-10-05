# -*- coding: utf-8 -*-
import pika

class MQ(object):
    def __init__(self, config):
        """
        NOTE: for multiprocessing with ouka separate chanel should be used for each process or threaded
        http://lists.rabbitmq.com/pipermail/rabbitmq-discuss/2013-September/030535.html
        """
        self.config = config
        self.Connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.config.host))

    def initInChannel(self, fun):
        try:
            inChannel = self.Connection.channel()
            inChannel.queue_declare(queue=self.config.inqueue)
            inChannel.basic_consume(fun, queue=self.config.inqueue, no_ack=True)
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
