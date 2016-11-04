# -*- coding: utf-8 -*-
import pika
import rabbitpy

class MQ(object):
    def __init__(self, config):
        """
        NOTE: for multiprocessing with ouka separate chanel should be used for each process or threaded
        http://lists.rabbitmq.com/pipermail/rabbitmq-discuss/2013-September/030535.html
        """
        self.config = config
        self.pyurl = 'amqp://guest:guest@{0}:5672/%2F'.format(self.config.host)
        self.PyConnection = rabbitpy.Connection(self.pyurl)

    def initInChannel(self, fun):
        try:
            inChannel = self.Connection.channel()
            inChannel.queue_declare(queue=self.config.inqueue)
            #inChannel.basic_qos(prefetch_count=300)
            inChannel.basic_consume(fun, queue=self.config.inqueue, no_ack=True)
        except pika.exceptions.ConnectionClosed:
            inChannel = None
        return inChannel


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

    def initInRabbitPyQueue(self):
        #try:
        inChannel = self.PyConnection.channel()
        Queue  = rabbitpy.Queue(inChannel, self.config.inqueue)
        Queue.durable = True
        Queue.declare()
            #inChannel.basic_qos(prefetch_count=300)
            #inChannel.basic_consume(fun, queue=self.config.inqueue, no_ack=True)
        #except: #pika.exceptions.ConnectionClosed:
        #    Queue = None
        return Queue

    def initOutRabbitPyChannel(self):
        #try:
        outChannel = self.PyConnection.channel()
        exchange = rabbitpy.Exchange(outChannel, self.config.outqueue)
        exchange.declare()
            #Queue  = rabbitpy.Queue(inChannel, self.config.inqueue)
            #inChannel.basic_qos(prefetch_count=300)
            #inChannel.basic_consume(fun, queue=self.config.inqueue, no_ack=True)
        #except: #pika.exceptions.ConnectionClosed:
        #    outChannel = None
        return outChannel

    def prepareMsg(self, ch, data):
        return rabbitpy.Message(ch, data)
