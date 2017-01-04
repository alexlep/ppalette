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
    def test10(self):
        # check_hosts
        result = self.app.get('/redapi/hosts')
        self.assertEqual(result.status_code, 200)

    def test20(self):
        # check_status
        result = self.app.get('/redapi/status')
        self.assertEqual(result.status_code, 200)

    def test30(self):
        # post_create_localhost
        result = self.app.post('/redapi/host?ip=127.0.0.1')
        self.assertEqual(result.status_code, 200)

    def test40(self):
        # post_create_googledns
        result = self.app.post('/redapi/host?ip=8.8.8.8&hostname=googledns&login=googleuser')
        self.assertEqual(result.status_code, 200)

    def test50(self):
        # post_create_googlesite_with_resolve
        result = self.app.post('/redapi/host?ip=216.58.214.206')
        self.assertEqual(result.status_code, 200)

    def test60(self):
        # put_edit_googledns
        result = self.app.put('/redapi/host?ip=8.8.8.8&hostname=googlednsnew&login=googleusernew')
        self.assertEqual(result.status_code, 200)

    def test70(self):
        # delete_remove_googledns
        result = self.app.delete('/redapi/host?ip=8.8.8.8')
        self.assertEqual(result.status_code, 200)

    def test80(self):
        # get_fetch_localhost
        result = self.app.get('/redapi/host?ip=127.0.0.1')
        self.assertEqual(result.status_code, 200)

    def test90(self):
        # check_hosts_else
        result = self.app.get('/redapi/hosts')
        self.assertEqual(result.status_code, 200)

    # Plugin API tests
    def test1000(self):
        # post_create_plugin
        result = self.app.post('/redapi/plugin?customname=check_mysql_linux_test&script=check_mysql')
        self.assertEqual(result.status_code, 200)

    def test1010(self):
        # post_create_plugin
        result = self.app.put('/redapi/plugin?customname=check_mysql_linux_test&params=-w10 -c20')
        self.assertEqual(result.status_code, 200)

    def test1020(self):
        # check_hosts_else
        result = self.app.get('/redapi/plugin?customname=check_mysql_linux_test')
        self.assertEqual(result.status_code, 200)

    def test1030(self):
        # post_create_plugin - should fail as suite with such name does not exist
        result = self.app.post('/redapi/plugin?customname=check_load_linux_test&script=check_load&suite=defLinuxRemoteSuite')
        self.assertEqual(result.status_code, 400)
if __name__ == '__main__':
    unittest.main()
