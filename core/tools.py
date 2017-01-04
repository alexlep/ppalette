# -*- coding: utf-8 -*-
import os, sys
import subprocess
import logging
import json
import uuid
import socket
import datetime as dt
import time
from sshexecutor import SSHConnection

class Message(object):
    type = None
    action = None
    suite_id = None
    scheduled_time = None
    script = None
    plugin_id = None
    pluginUUID = None
    params = None
    host_id = None
    hostUUID = None
    hostname = None
    ipaddress = None
    interval = None
    ssh_wrapper = None
    login = None
    output = None
    exitcode = None
    time = None
    executor = None
    def __init__ (self, data=False, fromJSON=False, plugin=False,
                  suite=False, host=False, subnet=False):
        if fromJSON:
            data = json.loads(data)
        if data:
            self.__dict__.update(data)
        if plugin:
            self.pluginUUID = plugin.pluginUUID
            self.plugin_id = plugin.id
            self.interval = plugin.interval
            self.ssh_wrapper = plugin.ssh_wrapper
            self.script = plugin.script
            self.params = plugin.params
        if host:
            self.hostUUID = host.hostUUID
            self.host_id = host.id
            self.ipaddress = host.ipaddress
            self.hostname = host.hostname
            self.login = host.login
        if suite:
            self.suite_id = suite.id
        if subnet:
            self.subnet_id = subnet.id
            self.suite_id = subnet.suite_id
        scheduled_time = dt.datetime.now()

    def getScheduleJobID(self):
        return self.hostUUID + self.pluginUUID

    def tojson(self, refreshTime = False):
        if refreshTime:
            self.scheduled_time = dt.datetime.now().\
                                    strftime("%H:%M:%S:%d:%m:%Y")
        return json.dumps(self.__dict__)

    def prepareSSHCommand(self):
        return "{0} {1}".format(self.executor, self.params)

    def prepareLocalCommand(self):
        return "{0} {1} {2}".format(self.executor, self.params, self.ipaddress)

    def prepareDiscoveryCommand(self):
        return "ping -c3 -W1 {0}".format(self.ipaddress)

    def removeWrongASCIISymbols(self):
        self.output = self.output.decode('utf-8','ignore').encode("utf-8")

class draftClass:
    def __init__(self, dictdata = dict()):
        self.__dict__.update(dictdata)

    def updateWithDict(self, dictdata):
        self.__dict__.update(dictdata)

    def tojson(self):
        return json.dumps(self.__dict__)

def time_wrap(func):
    def func_wrapper(*args, **kwargs):
        data = func(*args, **kwargs)
        data.time = dt.datetime.now().strftime("%H:%M:%S:%d:%m:%Y")
        return data
    return func_wrapper

def parseConfig(config):
    try:
        with open(config) as config_file:
            config_data = json.load(config_file)
            config_file.close()
    except ValueError as ve:
        print "Error in configuration file {0}: {1}".format(config, ve)
        config_file.close()
        sys.exit(1)
    except IOError as ie:
        print "Error in opening configuration file {0}: {1}".format(config, ie)
        sys.exit(1)
    config = draftClass(config_data)
    config.log = draftClass(config.log)
    try: # ome service don't use MQ, so there is no config for them (blue, for example)
        config.queue = draftClass(config.queue)
    except AttributeError:
        pass
    try: # same with ssh, for violet
        config.ssh = draftClass(config.ssh)
        config.ssh.host_key_file = os.path.expanduser(config.ssh.host_key_file)
        config.ssh.rsa_key_file = os.path.expanduser(config.ssh.rsa_key_file)
    except AttributeError:
        pass
    return config

@time_wrap
def executeDiscovery(job):
    process = subprocess.Popen(job.prepareDiscoveryCommand(),
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    job.output = process.communicate()[0].rstrip() # here subprocess is killed
    job.exitcode = process.returncode
    job.hostname = resolveIP(job.ipaddress)
    return job

@time_wrap
def executeProcess(job):
    process = subprocess.Popen(job.prepareLocalCommand(),
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    out = process.communicate()[0].rstrip() # here subprocess is killed
    try:
        job.output, job.details = out.split("|")
    except ValueError:
        job.output, job.details = out, None
    job.exitcode = process.returncode
    return job

@time_wrap
def executeProcessViaSSH(job, ssh_config):
    if not (os.path.isfile(ssh_config.host_key_file)) or not (os.path.isfile(ssh_config.host_key_file)):
        raise IOError
    conn = SSHConnection(ipaddress = job.ipaddress,
                         user = job.login,
                         ssh_config = ssh_config)
    job.output, job.details, job.exitcode = conn.executeCommand(job.prepareSSHCommand()) # here remote connection is killed
    return job

def initLogging(logconfig, serviceName = str()):
    logger = logging.getLogger(serviceName)
    hdlr = logging.FileHandler(logconfig.log_file)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(getattr(logging, logconfig.log_level))
    return logger
"""
def prepareDict(converted,**kwargs):
    data = {}
    for name, value in kwargs.items():
        data[name] = value
    if converted:
        return json.dumps(data)
    else:
        return data"""

def prepareDictFromSQLA(item):
    return dict(zip(item.keys(), item))

def fromJSONtoDict(data):
    try:
        msg = json.loads(data)
    except:
        msg = None
    return msg

def fromDictToJson(data):
    msg = json.dumps(data)
    return msg

def getUniqueID(short = False):
    if short:
        identifier = str(uuid.uuid4().fields[-1])[:8]
    else:
        identifier = str(uuid.uuid4())
    return identifier

def resolveIP(ipaddress):
    try:
        res = socket.gethostbyaddr(ipaddress)[0]
    except:
        res = ipaddress
    return res

def validateIP(ipaddress):
    try:
        socket.inet_aton(ipaddress)
        res = True
    except socket.error:
        res = False
    return res
