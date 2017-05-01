import unittest
import os
import time
import sys
import json

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)
os.chdir(parentdir)

import signal
from core.violet import Violet
from core.pvars import violetConfigFile
from core.processing import Factory
from core.tools import initStdoutLogger, dateToStr
import datetime as dt

WORKERS_COUNT = 2
# VioletApp.startProcesses()

'''

'''


class apiTestClass(unittest.TestCase):
    def setUp(self):
        pass

    @classmethod
    def setUpClass(self):
        super(apiTestClass, self).setUpClass()
        self.VApp = Violet(violetConfigFile, testing=True)
        signal.signal(signal.SIGINT, self.VApp)
        factory = Factory()
        factory.prepareWorkers(procCount=WORKERS_COUNT,
                               logger=initStdoutLogger(),
                               checks=self.VApp.preparePluginDict(),
                               ssh_config=self.VApp.config.ssh)
        self.VApp.factory = factory
        self.VApp.factory.startWork()

    def tearDown(self):
        pass

    def test_0001(self):
        assert 'check_dummy' in self.VApp.preparePluginDict().keys()

    def test_0002(self):
        method = self.VApp.factory._getAliveCount
        assert method(self.VApp.factory.workers) == WORKERS_COUNT
        assert method(self.VApp.factory.senders) == 0
        assert method(self.VApp.factory.consumers) == 0

    def test_0010(self):
        # check basic ping
        timeStr = dateToStr(dt.datetime.now())
        request = {
            "type": "check",
            "ssh_wrapper": false,
            "hostname": "localhost",
            "ipaddress": "127.0.0.1",
            "script": "check_ping",
            "scheduled_time": timeStr,
            "pluginUUID" : "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA",
            "hostUUID" : "BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB",
            "interval": 15,
            "params": null,
            "host_id": 5,
            "plugin_id": 3,
            "suite_id": 2,
            "login": "test"}

    def test_9999(self):
        self.VApp.destroy()


if __name__ == '__main__':
    unittest.main()
