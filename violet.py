# -*- coding: utf-8 -*-
import json, sys, os, signal, time
from core.mq import MQ
from core.threaded import Factory, inChannelThread, outChannelThread
from core.tools import draftClass, parseConfig, initLogging

workingDir = os.path.dirname(os.path.abspath(__file__))
violetConfig = workingDir + '/config/violet_config.json'

class Violet(object):
    def __init__(self, configFile):
        self.config = parseConfig(configFile)
        self.logConfig = draftClass(self.config.log)
        self.queueConfig = draftClass(self.config.queue)
        self.log = initLogging(self.logConfig) # init logging
        self.MQ = MQ(self.queueConfig)
        """if not self.inChannel:
            self.log.error('Unable to connect to RabbitMQ. Please check config and RMQ service.')
            print "Unable to connect to RabbitMQ. Please check config and RMQ service."
            sys.exit(1)"""
        self.checks = self.preparePluginDict()
        self.factory = Factory(serviceType = 'violet',
                               workers_count = self.config.process_count,
                               mq_config = self.queueConfig,
                               mq_handler = self.MQ,
                               logger = self.log,
                               checks = self.checks)
        self._prepareWorkerForMQInput() # separate consumer thread
        self._prepareWorkerForMQOutput() # separate sender thread

    def __call__(self, signum, frame):
        print 'sigint captured'
        self.destroy()

    def _prepareWorkerForMQInput(self):
        for i in range(4):
            self.factory.in_mq_threads.append(inChannelThread(mqQueue =self.MQ.initInRabbitPyQueue(), pQueue = self.factory.in_process_queue_f))

    def _prepareWorkerForMQOutput(self):
        for i in range(4):
            self.factory.out_mq_threads.append(outChannelThread(mqChannel = self.MQ.initOutRabbitPyChannel(), mqQueue = self.queueConfig.outqueue, pQueue = self.factory.out_process_queue_f))

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
        self.factory.startWork()
        while True:
            time.sleep(1)

    def destroy(self):
        self.factory.goHome()
        print 'workers_went_home'
        sys.exit(0)

if __name__ =='__main__':
    VioletApp = Violet(violetConfig)
    signal.signal(signal.SIGINT, VioletApp)
    VioletApp.startProcesses()
