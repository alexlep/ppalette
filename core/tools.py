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
from ipaddress import ip_address, ip_network, IPv4Network
from pvars import commonConfigFile, redConfigFile, defTimeFormat, workingDir

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
    message_id = None
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
        if subnet: # discovery job
            self.subnet_id = subnet.id
            self.suite_id = subnet.suite_id

    def convertStrToDate(self):
        self.exec_time = strToDate(self.exec_time)
        self.scheduled_time = strToDate(self.scheduled_time)

    def tojson(self):
        try:
            res = json.dumps(self.__dict__)
        except UnicodeDecodeError:
            self.removeWrongASCIISymbols()
            res = json.dumps(self.__dict__)
        return res

    def prepareSSHCommand(self):
        return "{0} {1}".format(self.executor, self.params)

    def prepareLocalCommand(self):
        if self.params is None:
            res = "{0} {1}".format(self.executor, self.ipaddress)
        else:
            res = "{0} {1} {2}".format(self.executor,
                                       self.params,
                                       self.ipaddress)
        return res

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

    def expandPaths(self):
        for key in self.__dict__.keys():
            try:
                self.__dict__[key] = os.path.expanduser(self.__dict__[key])
            except:
                pass

def time_wrap(func):
    def func_wrapper(*args, **kwargs):
        data = func(*args, **kwargs)
        data.exec_time = dateToStr(dt.datetime.now())
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
    for item in config.__dict__.keys():
        if type(getattr(config, item)) is dict:
            setattr(config, item, draftClass(getattr(config, item)))
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
    if not (os.path.isfile(ssh_config.host_key_file)) or \
       not (os.path.isfile(ssh_config.rsa_key_file)):
        raise IOError('Unable to reach ssh configuration files.')
    conn = SSHConnection(ipaddress=job.ipaddress,
                         user=job.login,
                         ssh_config=ssh_config)
    job.output, job.details, job.exitcode = conn.executeCommand(job.prepareSSHCommand()) # here remote connection is killed
    return job

def initLogging(logconfig, service = str()):
    logger = logging.getLogger(service)
    hdlr = logging.FileHandler(logconfig.log_file)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(getattr(logging, logconfig.log_level))
    return logger

def initStdoutLogger():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    return logging.getLogger(str())

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
        ip_address(ipaddress)
        res = True
    except:
        res = False
    return res

def validateNetwork(subnet, netmask):
    try:
        ip_network(u'{0}/{1}'.format(subnet, netmask))
        res = True
    except:
        res = False
    return res

def getListOfIPs(subnet, netmask):
    return list(IPv4Network(u'{0}/{1}'.format(subnet, netmask)))

def validateInt(value):
    try:
        int(value)
    except:
        raise ValueError("{} value is incorrect".format(value))
    return value

def validatePage(value):
    if validateInt(value) < 1:
        raise ValueError("{} value is below 1".format(value))
    return True

def checkDev():
    return parseConfig(commonConfigFile).development

def getPidPath():
    return workingDir + parseConfig(commonConfigFile).pid_path

def getApiServerType():
    return parseConfig(commonConfigFile).redapi_server

def strToDate(dateStr, now=False):
    if not now:
        res = dt.datetime.strptime(dateStr, defTimeFormat)
    else:
        res = dt.datetime.strptime(dt.datetime.now(), defTimeFormat)
    return res

def dateToStr(dateObj=None):
    if dateObj is not None:
        res = dateObj.strftime(defTimeFormat)
    else:
        res = dt.datetime.now().strftime(defTimeFormat)
    return res

def pluginDict(pluginPaths, logger=None):
    tPlugDict = dict()
    for path in pluginPaths.split(';'):
        if path:
            try:
                scripts = os.listdir(path)
            except OSError as (errno, strerror):
                if logger:
                    logger.warning("Unable to access directory {0} to get plugins. Reason: {1}.".format(path, strerror))
                continue
            if not len(scripts):
                if logger:
                    logger.warning("No plugins found in {0} directory is empty. Skipping it.".format(path))
            else:
                for script in scripts:
                    tPlugDict[script] = "{0}/{1}".format(path, script)
    return tPlugDict
