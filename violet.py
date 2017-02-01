# -*- coding: utf-8 -*-
import sys
import os
import signal
import time
from core.mq import MQ
from core.processing import Factory, Sender, Consumer
from core.tools import draftClass, parseConfig, initLogging, getUniqueID

workingDir = os.path.dirname(os.path.abspath(__file__))
violetConfig = workingDir + '/config/violet_config.json'

class Violet(object):
    def __init__(self, configFile):
        self.config = parseConfig(configFile)
        self.log = initLogging(self.config.log) # init logging
        self.MQ = MQ(self.config.queue)
        self.identifier = self.MQ.getConnectionId()
        self.senderStatsChannel = self.MQ.initMonitoringOutChannel()
        self.checks = self.preparePluginDict()
        self.factory = Factory()
        self.factory.prepareWorkers(procCount=self.config.process_count,
                                    logger=self.log,
                                    checks=self.checks,
                                    ssh_config=self.config.ssh)
        self._prepareConsumers() # separate consumer thread
        self._prepareSenders() # separate sender thread

    def __call__(self, signum, frame):
        print 'sigint captured'
        self.destroy()

    def preparePluginDict(self):
        tPlugDict = dict()
        for path in self.config.plugin_paths.split(';'):
            if path:
                try:
                    scripts = os.listdir(path)
                except OSError as (errno, strerror):
                    self.log.warning("Unable to access directory {0} to get plugins. Reason: {1}.".format(path, strerror))
                    continue
                if not len(scripts):
                    self.log.warning("No plugins found in directory {0} directory is empty. Skipping it.".format(path))
                else:
                    for script in scripts:
                        tPlugDict[script] = "{0}/{1}".format(path, script)
        return tPlugDict

    def startProcesses(self):
        print 'starting'
        self.factory.startWork()
        while True:
            time.sleep(self.config.heartbeat_interval)
            self._sendStats(self.config.heartbeat_interval)

    def destroy(self):
        self.factory.goHome()
        print 'workers_went_home'
        sys.exit(0)

    def _sendStats(self, interval=0):
        statistics = self.factory.gatherStats(interval)
        statistics.identifier = self.identifier
        self.MQ.sendM(self.senderStatsChannel, statistics.tojson())

    def _prepareConsumers(self):
        for i in range(self.config.queue.consumer_amount):
            self.factory.\
                consumers.\
                append(Consumer(mqQueue=self.MQ.initInRabbitPyQueue(),
                                pQueue=self.factory.in_process_queue_f))

    def _prepareSenders(self):
        for i in range(self.config.queue.sender_amount):
            self.factory.\
                senders.\
                append(Sender(mqChannel=self.MQ.initOutRabbitPyChannel(),
                              mqQueue=self.config.queue.outqueue,
                              pQueue=self.factory.out_process_queue_f))

if __name__ =='__main__':
    VioletApp = Violet(violetConfig)
    signal.signal(signal.SIGINT, VioletApp)
    VioletApp.startProcesses()
