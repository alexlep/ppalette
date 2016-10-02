# -*- coding: utf-8 -*-
import sys
import json
import subprocess
import logging
import json
import uuid
from datetime import datetime
import socket

"""
def ping(host):

    Returns True if host responds to a ping request


    # Ping parameters as function of OS
    ping_str = "-n 1" if  platform.system().lower()=="windows" else "-c 1"

    # Ping
    return os.system("ping " + ping_str + " " + host) == 0
"""

class draftClass:
    def __init__(self, dict):
        self.__dict__.update(dict)

    def updateWithDict(self, dict):
        self.__dict__.update(dict)


def parseConfig(config):
    try:
        with open(config) as config_file:
            config_data =  json.load(config_file)
            config_file.close()
    except ValueError as ve:
        print "Error in configuration file {0}: {1}".format(config, ve)
        config_file.close()
        sys.exit(1)
    except IOError as ie:
        print "Error in opening configuration file {0}: {1}".format(config, ie)
        sys.exit(1)
    return draftClass(config_data)

def executeProcess(command):
    feedback = {}
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = process.communicate()[0].rstrip() # here subprocess is killed
    try:
        feedback['output'], feedback['details'] = out.split("|")
    except ValueError:
        feedback['output'], feedback['details'] = out, None
    feedback['exitcode'] = process.returncode
    feedback['time'] = datetime.now().strftime("%H:%M:%S:%d:%m:%Y")
    return feedback

def initLogging(logconfig):
    logger = logging.getLogger('')
    hdlr = logging.FileHandler(logconfig.log_file)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(getattr(logging, logconfig.log_level))
    return logger

def prepareDict(converted,**kwargs):
    data = {}
    for name, value in kwargs.items():
        data[name] = value
    if converted:
        return json.dumps(data)
    else:
        return data

def prepareDictFromSQLA(item):
    return dict(zip(item.keys(), item))

def fromJSON(data):
    try:
        msg = json.loads(data)
    except:
        msg = None
    return msg

def getUniqueID():
    return str(uuid.uuid4())

def resolveIP(ipaddress):
    try:
        result = socket.gethostbyaddr(ipaddress)[0]
    except:
        result = ipaddress
    return result
