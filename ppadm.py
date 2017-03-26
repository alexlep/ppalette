"""ppadm - administrative interface for ppalette. Works through RedAPI.

Usage:
  ppadm.py (get|delete) host --ipaddress=<ip>
  ppadm.py add host --ipaddress=<ip> [--hostname=<hostname>] [--suite=<suitename>] [--subnet=<subnetname>]
  ppadm.py edit host --ipaddress=<ip> [--hostname=<hostname>] [--suite=<suitename>] [--subnet=<subnetname>] [--maintenance=(on|off)]
  ppadm.py (get|delete) subnet --name=<name>
  ppadm.py add subnet --name=<name> --subnet=<subnet> --netmask=<netmask> [--suite=<suite>]
  ppadm.py edit subnet --name=<name> [--suite=<suitename>] [--subnet=<subnetname>] [--netmask=<netmask>]
  ppadm.py list (hosts|subnets|plugins|suites)
  ppadm.py ops discovery --subnet=<subnet>
  ppadm.py show (status|scheduler|workers)
  ppadm.py show monitoring --type=<type> [--period=<period>]
  ppadm.py show monitoring --type=violet --violet_id=<violet_id> [--period=<period>]
  ppadm.py (get|delete) plugin --customname=<customname>
  ppadm.py add plugin --customname=<customname> --script=<script> --interval=<interval> [--ssh_wrapper=(on|off)] [--params='<params>'] [--suite=<suite>...]
  ppadm.py edit plugin --customname=<customname> [--interval=<interval>] [--ssh_wrapper=(on|off)] [--params='<params>'] [--suite=<suite>...]
  ppadm.py (get|delete) suite --name=<name>
  ppadm.py add suite --name=<name> [--ipaddress=<IPs>...] [--subnetname=<subnets>...] [--plugin=<plugins>...]
  ppadm.py edit suite --name=<name> [--ipaddress=<IPs>...] [--subnetname=<subnets>...] [--plugin=<plugins>...]

Options:
  -h --help     Show this screen
"""
import os
import sys
import requests
from docopt import docopt

from core.tools import parseConfig
import logging
from core.pvars import redConfigFile

LOGLEVEL = "DEBUG"
logging.basicConfig(stream=sys.stderr, level=getattr(logging, LOGLEVEL))

config = parseConfig(redConfigFile)

host = config.webapi.host
port = config.webapi.port
redApiUrl = 'http://{0}:{1}/redapi'.format(host, port)

request_types= {
    'show' : 'get',
    'list' : 'get',
    'get' : 'get',
    'edit' : 'put',
    'delete' : 'delete',
    'add' : 'post',
    'ops' : 'get'
}

single_item = ['subnet', 'host', 'plugin', 'suite']
list_items = ['subnets', 'plugins', 'suites', 'hosts']
special = ['discovery']
dynamic = ['status', 'monitoring', 'scheduler', 'workers']

object_types = {
    'show' : dynamic,
    'list' : list_items,
    'get' : single_item,
    'edit' : single_item,
    'delete' : single_item,
    'add' : single_item,
    'ops' : special
}

def getOperation(arguments):
    for key in request_types.keys():
        if (key in arguments.keys()) and (arguments[key]):
            return key

def getObj(arguments):
    for key in arguments.keys():
        if (key in object_types[operation]) and (arguments[key]):
            return key

def getOptions(arguments):
    opargs = dict()
    for key in arguments.keys():
        if key.startswith('--') and (arguments[key] is not None):
            opargs[key[2:]] = arguments[key]
    return opargs

def runApiCall(method, obj, params):
    try:
        r = getattr(requests, method)('{0}/{1}'.format(redApiUrl, obj),
                                      data=params)
    except requests.exceptions.ConnectionError as ce:
        print "Unable to connect to {}. Is red running?".format(redApiUrl)
        sys.exit(1)
    logging.debug(r.url)
    return (r.text, r.status_code)

if __name__ == '__main__':
    arguments = docopt(__doc__, version='ppadm 0.0.1')
    logging.debug(arguments)

    operation = getOperation(arguments)
    obj = getObj(arguments)
    method = request_types[operation]
    logging.debug('operation={0},obj={1},method={2}'.format(operation,
                                                            obj,
                                                            method))
    print runApiCall(method, obj, getOptions(arguments))[0]
    sys.exit(0)
