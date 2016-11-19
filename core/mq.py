# -*- coding: utf-8 -*-
import sys
import rabbitpy
import requests
#from rabbitpy import Connection, Channel0
#from rabbitpuy import __version__ as rabbitpy_version
from rabbitpy.channel0 import Channel0
from pamqp import specification
from tools import getUniqueID

class myChannel0(Channel0):
    def _build_start_ok_frame(self):
        """Build and return the Connection.StartOk frame.
        :rtype: pamqp.specification.Connection.StartOk
        """
        properties = {
            'product': 'rabbitpy',
            'platform': 'Python {0}.{1}.{2}'.format(*sys.version_info),
            'capabilities': {'authentication_failure_close': True,
                             'basic.nack': True,
                             'connection.blocked': True,
                             'consumer_cancel_notify': True,
                             'publisher_confirms': True},
            'information': 'See https://rabbitpy.readthedocs.io',
            'version': rabbitpy.__version__,
            'connection_id' : "violet-{}".format(getUniqueID(short=True))
                        }
        self.client_properties = properties
        return specification.Connection.StartOk(client_properties=properties,
                                                response=self._credentials,
                                                locale=self._get_locale())

class myConnection(rabbitpy.Connection):
    def _create_channel0(self):
        return myChannel0(connection_args=self._args,
            events_obj=self._events,
            exception_queue=self._exceptions,
            write_queue=self._write_queue,
            write_trigger=self._io.write_trigger,
            connection=self)

class MQ(object):
    def __init__(self, config, logger):
        self.config = config
        self.pyurl = 'amqp://{0}:{1}@{2}:{3}/%2F'.format(self.config.user,
                                                         self.config.password,
                                                         self.config.host,
                                                         self.config.port)
        try:
            self.PyConnection = myConnection(self.pyurl)
        except RuntimeError:
            logger.error('Unable to connect to RabbitMQ. Please check config and RMQ service.')
            print "Unable to connect to RabbitMQ. Please check config and RMQ service."
            sys.exit(1)

    def initInRabbitPyQueue(self, mqInQueue = None):
        inChannel = self.PyConnection.channel()
        if not mqInQueue:
            Queue = rabbitpy.Queue(inChannel, self.config.inqueue)
        else:
            Queue = rabbitpy.Queue(inChannel, mqInQueue)
        Queue.durable = True
        Queue.declare()
        return Queue

    def initOutRabbitPyChannel(self, mqOutQueue = None):
        outChannel = self.PyConnection.channel()
        if not mqOutQueue:
            exchange = rabbitpy.Exchange(outChannel, self.config.outqueue)
        else:
            exchange = rabbitpy.Exchange(outChannel, mqOutQueue)
        exchange.declare()
        return outChannel

    def prepareMsg(self, ch, data):
        return rabbitpy.Message(ch, data)

    def getActiveClients(self):
        res = requests.get('http://{0}:{1}/api/connections'.\
                           format(self.config.host,
                                  self.config.monitoring_port),
                           auth=(self.config.user, self.config.password))
        return res.json()
