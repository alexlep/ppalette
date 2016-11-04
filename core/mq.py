# -*- coding: utf-8 -*-
import sys
import rabbitpy

class MQ(object):
    def __init__(self, config, logger):
        self.config = config
        self.pyurl = 'amqp://guest:guest@{0}:5672/%2F'.format(self.config.host)
        try:
            self.PyConnection = rabbitpy.Connection(self.pyurl)
        except RuntimeError:
            logger.error('Unable to connect to RabbitMQ. Please check config and RMQ service.')
            print "Unable to connect to RabbitMQ. Please check config and RMQ service."
            sys.exit(1)

    def initInRabbitPyQueue(self):
        inChannel = self.PyConnection.channel()
        Queue  = rabbitpy.Queue(inChannel, self.config.inqueue)
        Queue.durable = True
        Queue.declare()
        return Queue

    def initOutRabbitPyChannel(self):
        outChannel = self.PyConnection.channel()
        exchange = rabbitpy.Exchange(outChannel, self.config.outqueue)
        exchange.declare()
        return outChannel

    def prepareMsg(self, ch, data):
        return rabbitpy.Message(ch, data)
