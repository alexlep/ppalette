import unittest
import os
import time
import sys

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
os.chdir(parentdir)

from core.tools import checkDev
import core.pvars as pv

if not checkDev():
    print 'Development mode is disabled - refusing to erase DB!'
    sys.exit(1)
else:
    # empty db
    from core.database import init_db
    init_db(True)


from red import RedApi

class apiTestClass(unittest.TestCase):
    def setUp(self):
        self.app = RedApi.test_client()
        self.app.testing = True

    def tearDown(self):
        pass
    # Host API tests
    def test0300(self):
        # post_create_localhost
        params = dict(ipaddress='127.0.0.1')
        result = self.app.post(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

        # post_create_googledns
        params = dict(ipaddress='8.8.8.8',
                      hostname='googledns',
                      login='googleuser')
        result = self.app.post(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

        # post_create_googlesite_with_resolve
        params = dict(ipaddress='216.58.214.206')
        result = self.app.post(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

        # post_create_bbc.com_with_resolve
        params = dict(ipaddress='212.58.246.90')
        result = self.app.post(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

        # post_create_newyorker.com_with_resolve
        params = dict(ipaddress='151.101.0.239')
        result = self.app.post(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

    def test0600(self):
        # put_edit_googledns
        params = dict(ipaddress='8.8.8.8',
                      hostname='googlednsnew',
                      login='googleusernew')
        result = self.app.put(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

    def test0700(self):
        # delete_remove_googledns
        params = dict(ipaddress='8.8.8.8')
        result = self.app.delete(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

    def test0800(self):
        # get_fetch_localhost
        params = dict(ipaddress='127.0.0.1')
        result = self.app.get(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

    def test0900(self):
        # check_hosts_else
        result = self.app.get(pv.HOSTS)
        self.assertEqual(result.status_code, 200)

    def test0910(self):
        # put_edit_localhost maintenance off
        params = dict(ipaddress='127.0.0.1',
                      maintenance='off')
        result = self.app.put(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

        # put_edit_google maintenance off
        params = dict(ipaddress='216.58.214.206',
                      maintenance='off')
        result = self.app.put(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

        # put_edit_bbc maintenance off
        params = dict(ipaddress='212.58.246.90',
                      maintenance='off')
        result = self.app.put(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

        # put_edit_newyorker maintenance off
        params = dict(ipaddress='151.101.0.239',
                      maintenance='off')
        result = self.app.put(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

    # Plugin API tests
    def test1000(self):
        # post_create_plugin
        params = dict(customname='check_mysql_linux_test',
                      script='check_mysql')
        result = self.app.post(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)

    def test1100(self):
        # post_edit_plugin
        params = dict(customname='check_mysql_linux_test',
                      params='-w10 -c20')
        result = self.app.put(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)

    def test1200(self):
        # get_fetch_plugin
        params = dict(customname='check_mysql_linux_test')
        result = self.app.get(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)
        assert '-w10 -c20' in result.data

    def test1300(self):
        # post_create_plugin_with_unknown_suite
        params = dict(customname='check_load_linux_test',
                      script='check_load',
                      suite='defLinuxRemoteSuite')
        result = self.app.post(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 400)
        assert 'Suite is not in DB' in result.data

    def test1300(self):
        # delete_remove_plugin check_mysql_linux_test
        params = dict(customname='check_mysql_linux_test')
        result = self.app.delete(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)

    def test1305(self):
        # get_removed_plugin check_mysql_linux_test, should be 404
        params = dict(customname='check_mysql_linux_test')
        result = self.app.get(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 404)

    def test1400(self):
        # post_create_plugin
        params = dict(customname='check_ping1',
                      script='check_ping')
        result = self.app.post(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)

        # post_create_plugin
        params = dict(customname='check_ping2',
                      script='check_ping')
        result = self.app.post(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)

        # post_create_plugin
        params = dict(customname='check_https_local',
                      script='check_https')
        result = self.app.post(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)

    def test1430(self):
        # put_edit_plugin
        params = dict(customname='check_ping1',
                      interval=10)
        result = self.app.put(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)

        # put_edit_plugin
        params = dict(customname='check_ping2',
                      interval=15)
        result = self.app.put(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)

        # put_edit_plugin
        params = dict(customname='check_https_local',
                      interval=20)
        result = self.app.put(pv.PLUGIN, data=params)
        self.assertEqual(result.status_code, 200)

    def test5000(self):
        # get_fetch_bbc
        params = dict(ipaddress='151.101.0.239')
        result = self.app.get(pv.HOST, data=params)
        self.assertEqual(result.status_code, 200)

    def test5010(self):
        # post_create_suite with hosts
        params = dict(name='defaultSuite',
                      ipaddress='216.58.214.206,212.58.246.90,151.101.0.239')
        result = self.app.post(pv.SUITE, data=params)
        self.assertEqual(result.status_code, 200)

    def test5012(self):
        # get_fetch_suite
        params = dict(name='defaultSuite')
        result = self.app.get(pv.SUITE, data=params)
        self.assertEqual(result.status_code, 200)
        assert '212.58.246.90' in result.data

    def test5014(self):
        # delete_remove_suite
        params = dict(name='defaultSuite')
        result = self.app.delete(pv.SUITE, data=params)
        self.assertEqual(result.status_code, 200)

    def test5016(self):
        # get_removed_suite_must_fail
        params = dict(name='defaultSuite')
        result = self.app.get(pv.SUITE, data=params)
        self.assertEqual(result.status_code, 404)

    def test5018(self):
        # post_create_suite must fail due to unknown ip
        params = dict(name='defaultSuite',
                      ipaddress="216.58.214.206,212.58.246.90,151.101.0.239,127.0.0.200")
        result = self.app.post(pv.SUITE, data=params)
        self.assertEqual(result.status_code, 400)
        assert 'Host is not in DB' in result.data

    def test5020(self):
        # post_create_suite with plugins and hosts
        params = dict(name='defaultSuite',
                      ipaddress='216.58.214.206,212.58.246.90,151.101.0.239',
                      plugin='check_ping1,check_ping2,check_https_local')
        result = self.app.post(pv.SUITE, data=params)
        self.assertEqual(result.status_code, 200)

    def test5022(self):
        # post_create_suite with plugins and hosts
        params = dict(name='defaultSuite',
                      plugin='check_ping1,check_ping2')
        result = self.app.put(pv.SUITE, data=params)
        self.assertEqual(result.status_code, 200)

    def test5024(self):
        # get_fetch_suite
        params = dict(name='defaultSuite')
        result = self.app.get(pv.SUITE, data=params)
        self.assertEqual(result.status_code, 200)
        assert 'check_https_local' not in result.data

    # apiListCallHandler tests
    def test6100(self):
        # check_hosts
        result = self.app.get(pv.HOSTS)
        self.assertEqual(result.status_code, 200)

    def test6102(self):
        # check_plugins
        result = self.app.get(pv.PLUGINS)
        self.assertEqual(result.status_code, 200)

    def test6104(self):
        # check_suites
        result = self.app.get(pv.SUITES)
        self.assertEqual(result.status_code, 200)

    def test6106(self):
        # check_subnets should fail as of now, no subnets where added
        result = self.app.get(pv.SUBNETS)
        self.assertEqual(result.status_code, 400)

    def test6108(self):
        # check_status
        result = self.app.get(pv.STATUS)
        self.assertEqual(result.status_code, 200)

    # test subnets and discovery
    def test7000(self):
        # check adding new subnet
        params = dict(name='poneyTelecomSubnet',
                      subnet='62.210.18.0',
                      netmask='255.255.255.192',
                      suite='defaultSuite')
        result = self.app.post(pv.SUBNET, data=params)
        self.assertEqual(result.status_code, 200)

    def test7010(self):
        # trigger discovery for added subnet - requests are sent to rabbitMQ
        params = dict(subnet='poneyTelecomSubnet')
        result = self.app.get(pv.DISCOVERY, data=params)
        self.assertEqual(result.status_code, 200)

    def test7020(self):
        # check get for added subnet
        params = dict(name='poneyTelecomSubnet')
        result = self.app.get(pv.SUBNET, data=params)
        self.assertEqual(result.status_code, 200)

    def test7022(self):
        # check list of subnets
        result = self.app.get(pv.SUBNETS)
        self.assertEqual(result.status_code, 200)

if __name__ == '__main__':
    unittest.main()
