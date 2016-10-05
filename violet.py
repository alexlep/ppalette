# -*- coding: utf-8 -*-
import json, sys, os, signal, time
import multiprocessing as mp
from core.mq import MQ
from core.processing import Factory
from core.tools import draftClass, parseConfig, initLogging

violetConfig = './config/violet_config.json'

class Violet(object):
    def __init__(self, configFile):
        self.config = parseConfig(configFile)
        self.logConfig = draftClass(self.config.log)
        self.queueConfig = draftClass(self.config.queue)
        self.log = initLogging(self.logConfig) # init logging
        self.MQ = MQ(self.queueConfig)
        self.inChannel = self.MQ.initInChannel(self.callback)
        if not self.inChannel:
            self.log.error('Unable to connect to RabbitMQ. Please check config and RMQ service.')
            print "Unable to connect to RabbitMQ. Please check config and RMQ service."
            sys.exit(1)
        self.cProc = self.prepareWorkerForMQ()# separate consumer process
        self.checks = self.preparePluginDict()
        self.factory = Factory(serviceType = 'violet',
                               workers_count = self.config.process_count,
                               mq_out_queue = self.queueConfig.outqueue,
                               mq_handler = self.MQ,
                               logger = self.log,
                               checks = self.checks)

    def prepareWorkerForMQ(self):
        return mp.Process(target=self.startConsumer)

    def preparePluginDict(self):
        tPlugDict = {}
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

    def startConsumer(self):
        print(' [*] Waiting for messages. To exit press CTRL+C')
        try:
            self.inChannel.start_consuming()
        except:
            print "ABORTING VIOLET LISTENER"

    def startProcesses(self):
        self.factory.startWork()
        self.cProc.start() # start separate consumer process

    def callback(self, ch, method, properties, body):
        self.factory.processQueue.put(body)

    def destroy(self):
        self.inChannel.close()
        self.factory.goHome()


if __name__ =='__main__':
    VioletApp = Violet(violetConfig)
    VioletApp.startProcesses()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        VioletApp.destroy()
        print "aborted with your little filthy hands!"
