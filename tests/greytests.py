import unittest
import os
import time
import sys
import json

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)
os.chdir(parentdir)

import core.pvars as pv
from core.tools import checkDev, Message, getPluginModule
from core.grey import Grey, db_session
from core.daemons import prepareRed

from core.configs import cConfig, gLogger

monit = getPluginModule(cConfig.mon_engine,
                        cConfig.mon_plugin_path,
                        gLogger)

if not checkDev():
    print 'Development is disabled - refusing to execute destructive tests!'
    sys.exit(1)

class apiTestClass(unittest.TestCase):
    def setUp(self):
        self.greyApp = Grey(pv.greyConfigFile, testing=True)
        self.redApp = self.RedApi.test_client()
        self.redApp.testing = True

    @classmethod
    def setUpClass(self):
        super(apiTestClass, self).setUpClass()
        self.RedApi = prepareRed()[0]

    def tearDown(self):
        db_session.close()

    def test_0100(self):
        # insert common stats
        self.removeRRDFile()
        self.assertRaises(Exception, self.greyApp.updateCommonStats())
        params = dict(type='common',
                      period='last')
        result = self.redApp.get(pv.MONITORING, data=params)
        self.assertEqual(result.status_code, 200)

    def removeRRDFile(self, violetID=None):
        try:
            if violetID:
                os.remove('{}/{}.rrd'.format(monit.rrdDataDir, violetID))
            else:
                os.remove(monit.statRRDFile)
        except OSError:
            pass

    def test_0110(self):
        # insert violet stats
        violetID = 'violet-testID001'
        self.removeRRDFile(violetID)
        violet_stats = {
            "last_update_time": "22:18:44:19:03:2017",
            "publishers_alive": 16,
            "identifier": violetID,
            "max_throughput": 49, "input_queue_size": 0,
            "worker_count": 32, "interval": 5, "worker_alive": 32,
            "throughput": 40, "consumers_count": 16,
            "publishers_count": 16, "consumers_alive": 16
            }
        self.assertRaises(Exception,
                          self.greyApp.\
                          updateVioletStats(json.dumps(violet_stats)))
        params = dict(type='violet',
                      violet_id=violetID,
                      period='last')
        result = self.redApp.get(pv.MONITORING, data=params)
        self.assertEqual(result.status_code, 200)
        assert 'consumers_alive": 16.0' in result.data

    def test_0120(self):
        # insert violet stats
        violetID = 'violet-testID00200'
        self.removeRRDFile(violetID)
        violet_stats = {
            "last_update_time": "22:18:44:19:03:2017",
            "publishers_alive": 300,
            "identifier": violetID,
            "max_throughput": 400, "input_queue_size": 0,
            "worker_count": 200, "interval": 800, "worker_alive": 800,
            "throughput": 80, "consumers_count": 130,
            "publishers_count": 300, "consumers_alive": 400
            }
        self.assertRaises(Exception,
                          self.greyApp.\
                          updateVioletStats(json.dumps(violet_stats)))
        params = dict(type='violet',
                      violet_id=violetID,
                      period='last')
        result = self.redApp.get(pv.MONITORING, data=params)
        self.assertEqual(result.status_code, 200)
        assert 'worker_count": 200' in result.data

    def test_0130(self):
        # non-existant ID
        params = dict(type='violet',
                      violet_id='WrongTestID',
                      period='last')
        result = self.redApp.get(pv.MONITORING, data=params)
        self.assertEqual(result.status_code, 400)
        assert 'No statistics found for' in result.data

    def test_0140(self):
        # add host after discovery, including already added host
        # delete host if exists
        params = dict(ipaddress='151.101.65.140')
        self.redApp.delete('/redapi/host', data=params)

        # imitating successful discovery, with callback method execution
        discoveryResult = {
            "subnet_id": None, "type": "task", "hostname": "reddit.com",
            "suite_id": None, "exec_time": "13:10:23:20:03:2017",
            "action": "discovery",
            "output": "whatever",
            "ipaddress": "151.101.65.140", "exitcode": 0,
            "scheduled_time": "13:10:28:20:03:2017"
            }
        self.greyApp.callback(json.dumps(discoveryResult))

        # check if new host is available via API
        params = dict(ipaddress='151.101.65.140')
        result = self.redApp.get(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)
        assert 'reddit.com' in result.data

        # disabling maintenance mode for host
        params = dict(ipaddress='151.101.65.140', maintenance='off')
        result = self.redApp.put(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

        # trying to add the same host via direct method call
        gRes = self.greyApp.tryAddingNewHost(Message(
                                                json.dumps(discoveryResult),
                                                fromJSON=True))
        assert 'is already in db' in gRes


    def test_0150(self):
        # discovery with incorrect exitcode, skip adding host
        discoveryResult = {
            "subnet_id": None, "type": "task", "hostname": "protonmail.com",
            "suite_id": None, "exec_time": "13:10:28:20:03:2017",
            "action": "discovery",
            "output": "whatever",
            "ipaddress": "185.70.40.182", "exitcode": 1,
            "scheduled_time": "13:10:28:20:03:2017"
            }
        self.greyApp.callback(json.dumps(discoveryResult))

        params = dict(ipaddress='185.70.40.182')
        result = self.redApp.get(pv.HOST, data=params)
        self.assertEqual(result.status_code, 404)
        assert 'not found' in result.data

    def test_0160(self):
        # get id for host and plugin
        params = dict(ipaddress='212.58.246.90')
        hostRes = self.redApp.get(pv.HOST, data=params)
        self.assertEqual(hostRes.status_code, 200)
        assert 'bbc-vip011.cwwtf.bbc.co.uk' in hostRes.data

        params = dict(customname='check_ping1')
        plugRes = self.redApp.get(pv.PLUGIN, data=params)
        self.assertEqual(plugRes.status_code, 200)
        assert 'check_ping' in plugRes.data

        hostInfo = json.loads(hostRes.data)
        plugInfo = json.loads(plugRes.data)

        # update status table
        checkRes = {"ssh_wrapper": False, "interval": 15,
                    "exec_time": "17:07:07:20:03:2017", "suite_id": None,
                    "host_id": hostInfo.get('id'),
                    "ipaddress": "212.58.246.90",
                    "login": "violet", "scheduled_time": "17:07:07:20:03:2017",
                    "hostname": "bbc-vip011.cwwtf.bbc.co.uk",
                    "script": "check_ping", "params": None, "details": "-6]",
                    "executor": "/usr/lib/nagios/plugins//check_ping",
                    "output": "test_output_BBC",
                    "plugin_id": plugInfo.get('id'),
                    "type": "check", "exitcode": 3}
        self.greyApp.callback(json.dumps(checkRes))

        # fetch inserted info
        params = dict(ipaddress='212.58.246.90')
        hostRes = self.redApp.get(pv.HOST, data=params)
        self.assertEqual(hostRes.status_code, 200)
        assert 'test_output_BBC' in hostRes.data

        # put update into history
        msg = Message(json.dumps(checkRes),fromJSON=True)
        msg.convertStrToDate()
        self.greyApp.updateHistory(msg)


if __name__ == '__main__':
    unittest.main()
