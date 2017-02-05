# -*- coding: utf-8 -*-
import sys
import rabbitpy
import requests
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
    def __init__(self, config, violet=False):
        self.config = config
        self.pyurl = 'amqp://{0}:{1}@{2}:{3}/%2F'.format(self.config.user,
                                                         self.config.password,
                                                         self.config.host,
                                                         self.config.port)
        try:
            self.PyConnection = myConnection(self.pyurl) if violet\
            else rabbitpy.Connection(self.pyurl)
        except:
            print "Unable to connect to RabbitMQ. Please check config and RMQ service."
            sys.exit(1)

    def initInRabbitPyQueue(self, mqInQueue=None):
        inChannel = self.PyConnection.channel()
        Queue = rabbitpy.Queue(inChannel, mqInQueue or self.config.inqueue)
        Queue.durable = True
        Queue.declare()
        return Queue

    def initOutRabbitPyChannel(self, mqOutQueue=None):
        outChannel = self.PyConnection.channel()
        exchange = rabbitpy.Exchange(outChannel,
                                     mqOutQueue or self.config.outqueue)
        exchange.declare()
        return outChannel

    def prepareMsg(self, ch, data):
        return rabbitpy.Message(ch, data)

    def sendM(self, ch, msg):
        message = self.prepareMsg(ch, msg)
        message.publish(str(), self.config.outqueue)

    def sendStatM(self, ch, msg):
        message = self.prepareMsg(ch, msg)
        message.publish(str(), self.config.monitoring_outqueue)

    def getActiveClients(self):
        res = requests.get('http://{0}:{1}/api/connections'.\
                           format(self.config.host,
                                  self.config.monitoring_port),
                           auth=(self.config.user, self.config.password))
        return res.json()

    def getWorkersList(self):
        workers = self.getActiveClients()
        res = dict()
        for worker in workers:
            if 'connection_id' in worker['client_properties']:
                worker_id = worker['client_properties']['connection_id']
                res[worker_id] = worker.get('host')
        return res

    def getConnectionId(self):
        return self.PyConnection._channel0.client_properties['connection_id']

    def initMonitoringOutChannel(self):
        return self.initOutRabbitPyChannel(self.config.monitoring_outqueue)
