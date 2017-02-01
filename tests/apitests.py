import unittest
import os
import time

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
os.chdir(parentdir)

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
        result = self.app.post('/redapi/host?ipaddress=127.0.0.1')
        self.assertEqual(result.status_code, 200)

    def test0400(self):
        # post_create_googledns
        result = self.app.post('/redapi/host?ipaddress=8.8.8.8&hostname=googledns&login=googleuser')
        self.assertEqual(result.status_code, 200)

    def test0500(self):
        # post_create_googlesite_with_resolve
        result = self.app.post('/redapi/host?ipaddress=216.58.214.206')
        self.assertEqual(result.status_code, 200)

    def test0502(self):
        # post_create_bbc.com_with_resolve
        result = self.app.post('/redapi/host?ipaddress=212.58.246.90')
        self.assertEqual(result.status_code, 200)

    def test0504(self):
        # post_create_newyorker.com_with_resolve
        result = self.app.post('/redapi/host?ipaddress=151.101.0.239')
        self.assertEqual(result.status_code, 200)

    def test0600(self):
        # put_edit_googledns
        result = self.app.put('/redapi/host?ipaddress=8.8.8.8&hostname=googlednsnew&login=googleusernew')
        self.assertEqual(result.status_code, 200)

    def test0700(self):
        # delete_remove_googledns
        result = self.app.delete('/redapi/host?ipaddress=8.8.8.8')
        self.assertEqual(result.status_code, 200)

    def test0800(self):
        # get_fetch_localhost
        result = self.app.get('/redapi/host?ipaddress=127.0.0.1')
        self.assertEqual(result.status_code, 200)

    def test0900(self):
        # check_hosts_else
        result = self.app.get('/redapi/hosts')
        self.assertEqual(result.status_code, 200)

    def test0910(self):
        # put_edit_localhost maintenance off
        result = self.app.put('/redapi/host?ipaddress=127.0.0.1&maintenance=off')
        self.assertEqual(result.status_code, 200)

    def test0920(self):
        # put_edit_google maintenance off
        result = self.app.put('/redapi/host?ipaddress=216.58.214.206&maintenance=off')
        self.assertEqual(result.status_code, 200)

    def test0930(self):
        # put_edit_bbc maintenance off
        result = self.app.put('/redapi/host?ipaddress=212.58.246.90&maintenance=off')
        self.assertEqual(result.status_code, 200)

    def test0940(self):
        # put_edit_newyorker maintenance off
        result = self.app.put('/redapi/host?ipaddress=151.101.0.239&maintenance=off')
        self.assertEqual(result.status_code, 200)

    # Plugin API tests
    def test1000(self):
        # post_create_plugin
        result = self.app.post('/redapi/plugin?customname=check_mysql_linux_test&script=check_mysql')
        self.assertEqual(result.status_code, 200)

    def test1100(self):
        # post_create_plugin
        result = self.app.put('/redapi/plugin?customname=check_mysql_linux_test&params=-w10 -c20')
        self.assertEqual(result.status_code, 200)

    def test1200(self):
        # check_hosts_else
        result = self.app.get('/redapi/plugin?customname=check_mysql_linux_test')
        self.assertEqual(result.status_code, 200)

    def test1300(self):
        # post_create_plugin
        result = self.app.post('/redapi/plugin?customname=check_load_linux_test&script=check_load&suite=defLinuxRemoteSuite')
        self.assertEqual(result.status_code, 400)

    def test1300(self):
        # delete_remove_plugin check_mysql_linux_test
        result = self.app.delete('/redapi/plugin?customname=check_mysql_linux_test')
        self.assertEqual(result.status_code, 200)

    def test1305(self):
        # get_removed_plugin check_mysql_linux_test, should be 404
        result = self.app.get('/redapi/plugin?customname=check_mysql_linux_test')
        self.assertEqual(result.status_code, 404)

    def test1400(self):
        # post_create_plugin
        result = self.app.post('/redapi/plugin?customname=check_ping1&script=check_ping')
        self.assertEqual(result.status_code, 200)

    def test1410(self):
        # post_create_plugin
        result = self.app.post('/redapi/plugin?customname=check_ping2&script=check_ping')
        self.assertEqual(result.status_code, 200)

    def test1420(self):
        # post_create_plugin
        result = self.app.post('/redapi/plugin?customname=check_https_local&script=check_https')
        self.assertEqual(result.status_code, 200)

    def test1430(self):
        # post_create_plugin
        result = self.app.put('/redapi/plugin?customname=check_ping1&interval=10')
        self.assertEqual(result.status_code, 200)

    def test1440(self):
        # post_create_plugin
        result = self.app.put('/redapi/plugin?customname=check_ping2&interval=15')
        self.assertEqual(result.status_code, 200)

    def test1450(self):
        # post_create_plugin
        result = self.app.put('/redapi/plugin?customname=check_https_local&interval=13')
        self.assertEqual(result.status_code, 200)

    def test5000(self):
        # get_fetch_bbc
        result = self.app.get('/redapi/host?ipaddress=151.101.0.239')
        self.assertEqual(result.status_code, 200)

    def test5010(self):
        # post_create_suite with hosts
        result = self.app.post('/redapi/suite?name=defaultSuite&ipaddress=216.58.214.206&ipaddress=212.58.246.90&ipaddress=151.101.0.239')
        self.assertEqual(result.status_code, 200)

    def test5012(self):
        # get_fetch_suite
        result = self.app.get('/redapi/suite?name=defaultSuite')
        self.assertEqual(result.status_code, 200)

    def test5014(self):
        # delete_remove_suite
        result = self.app.delete('/redapi/suite?name=defaultSuite')
        self.assertEqual(result.status_code, 200)

    def test5016(self):
        # get_removed_suite_must_fail
        result = self.app.get('/redapi/suite?name=defaultSuite')
        self.assertEqual(result.status_code, 404)

    def test5018(self):
        # post_create_suite must fail due to unknown ip
        result = self.app.post('/redapi/suite?name=defaultSuite&ipaddress=216.58.214.206&ipaddress=212.58.246.90&ipaddress=151.101.0.239&ipaddress=127.0.0.200')
        self.assertEqual(result.status_code, 400)

    def test5020(self):
        # post_create_suite with plugins and hosts
        result = self.app.post('/redapi/suite?name=defaultSuite&ipaddress=216.58.214.206&ipaddress=212.58.246.90&ipaddress=151.101.0.239&plugin=check_ping1&plugin=check_ping2&plugin=check_https_local')
        self.assertEqual(result.status_code, 200)

    def test5022(self):
        # post_create_suite with plugins and hosts
        result = self.app.put('/redapi/suite?name=defaultSuite&plugin=check_ping1&plugin=check_ping2')
        self.assertEqual(result.status_code, 200)

    def test5024(self):
        # get_fetch_suite
        result = self.app.get('/redapi/suite?name=defaultSuite')
        self.assertEqual(result.status_code, 200)


    # apiListCallHandler tests
    def test6100(self):
        # check_hosts
        result = self.app.get('/redapi/hosts')
        self.assertEqual(result.status_code, 200)

    def test6102(self):
        # check_plugins
        result = self.app.get('/redapi/plugins')
        self.assertEqual(result.status_code, 200)

    def test6104(self):
        # check_suites
        result = self.app.get('/redapi/suites')
        self.assertEqual(result.status_code, 200)

    def test6106(self):
        # check_subnets should fail as of now, no subnets where added
        result = self.app.get('/redapi/subnets')
        self.assertEqual(result.status_code, 400)

    def test6108(self):
        # check_status
        result = self.app.get('/redapi/status')
        self.assertEqual(result.status_code, 200)

    # test subnets and discovery
    def test7000(self):
        # check adding new subnet
        result = self.app.post('/redapi/subnet?name=poneyTelecomSubnet&subnet=62.210.18.0&netmask=255.255.255.192&suite=defaultSuite')
        self.assertEqual(result.status_code, 200)
        
    def test7010(self):
        # check discovery for added subnet - requests are sent to rabbitMQ
        result = self.app.get('/redapi/ops?op=discovery&arg=poneyTelecomSubnet')
        self.assertEqual(result.status_code, 200)

    def test7020(self):
        # check get for added subnet
        result = self.app.get('/redapi/subnet?name=poneyTelecomSubnet')
        self.assertEqual(result.status_code, 200)

    def test7022(self):
        # check list of subnets
        result = self.app.get('/redapi/subnets')
        self.assertEqual(result.status_code, 200)
if __name__ == '__main__':
    unittest.main()
