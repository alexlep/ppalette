# -*- coding: utf-8 -*-
import time

from configs import vConfig, vLogger
from mq import MQ
from processing import Factory
from rabbitpy import Message

class Violet(object):
    def __init__(self, testing=False):
        self.active = True
        if not testing:
            self.MQ = MQ(vConfig.queue, violet=True)
            self.factory = Factory(self.MQ.PyConnection, vConfig)
            self.factory.stats.identifier = self.MQ.getConnectionId()

    def __call__(self, signum, frame):
        vLogger.info('Catched SIGINT. Shutting down violet gracefully.')
        self.destruct()

    def startProcesses(self):
        vLogger.info('Starting violet factory')
        self.factory.startWork()
        self._startMonitoring()


    def destruct(self, signum, frame):
        self.factory.goHome()
        vLogger.info('Factory was closed.')
        self.active = False
        self.MQ.PyConnection.close()
        vLogger.info('Violet is terminated.')

    def _prepareStats(self, interval):
        stats = self.factory.gatherStats()
        stats.interval = interval
        return stats.tojsonAll()

    def _startMonitoring(self):
        vLogger.info('Starting to collect and launch statistics')
        with self.MQ.initMonitoringOutChannel() as ch:
            while self.active:
                time.sleep(vConfig.heartbeat_interval)
                stMsg = Message(ch,
                                self._prepareStats(vConfig.heartbeat_interval))
                stMsg.publish(str(), vConfig.queue.monitoring_outqueue)
                vLogger.info("Statistics were sent to RMQ. Waiting next "\
                             "{} seconds...".format(vConfig.heartbeat_interval))
