# -*- coding: utf-8 -*-
import sys, os
from core.database import init_db, db_session
from core.models import Status, History, Subnet, Host
from datetime import datetime
from sqlalchemy import update, insert, and_
from core.mq import MQ
from core.tools import parseConfig, initLogging, getUniqueID, Message

init_db(False)
workingDir = os.path.dirname(os.path.abspath(__file__))
greyConfig = workingDir + '/config/grey_config.json'

class Grey(object):
    def __init__(self, configFile):
        self.collectHistory = False
        self.config = parseConfig(configFile)
        self.log = initLogging(self.config.log, __name__) # init logging
        self.MQ = MQ(self.config.queue, self.log)
        self.inQueue = self.MQ.initInRabbitPyQueue()

    def startConsumer(self):
        while True:
            if len(self.inQueue) > 0:
                message = self.inQueue.get(acknowledge=False)
                self.callback(message.body)

    def callback(self, body):
        msg = Message(body, fromJSON = True)
        print msg.scheduled_time
        if msg.type == 'check':
            msg.time = datetime.strptime(msg.time, "%H:%M:%S:%d:%m:%Y")
            msg.scheduled_time = datetime.strptime(msg.scheduled_time, "%H:%M:%S:%d:%m:%Y")
            self.updateStatusTable(msg)
            if self.collectHistory:
                self.updateHistory(msg)
        elif 'task':
            if msg.action == 'discovery':
                self.log.info(self.tryAddingNewHost(msg))

    def updateStatusTable(self, msg):
        updateQ = Status.__table__.update().where(and_(Status.plugin_id==msg.pluginid, Status.host_id==msg.hostid)).\
            values(last_status=msg.output, last_exitcode = msg.exitcode,
                   last_check_run = msg.time, scheduled_check_time = msg.scheduled_time,
                   interval = msg.interval)
        if not db_session.execute(updateQ).rowcount:
            insertQ = insert(Status).values(statusid = getUniqueID(),
                                        plugin_id = msg.pluginid,
                                        host_id = msg.hostid,
                                        last_status = msg.output,
                                        last_exitcode = msg.exitcode,
                                        scheduled_check_time = msg.scheduled_time,
                                        last_check_run = msg.time,
                                        interval = msg.interval)
            db_session.execute(insertQ)
        print msg.details
        db_session.commit()
        return

    def updateHistory(self, msg):
        h = History(msg)
        #h.insertValues(msg)
        db_session.add(h)
        db_session.commit()
        return

    def tryAddingNewHost(self, msg):
        if msg.exitcode == 0:
            existingHost = db_session.query(Host).filter(Host.ipaddress == msg.ipaddress).first()
            if (not existingHost):
                newHost = Host()
                newHost.hostUUID = getUniqueID()
                newHost.hostname = msg.hostname
                newHost.ipaddress = msg.ipaddress
                newHost.subnet_id = msg.subnet_id
                newHost.suite_id = msg.suite_id
                newHost.maintenance = True
                db_session.add(newHost)
                db_session.commit()
                result = "AutoDiscovery: ip {0} was successfully added".format(msg.ipaddress)
            else:
                result = "AutoDiscovery: host with ip {0} is already in db. Skipping.".format(msg.ipaddress)
        else:
            result = "AutoDiscovery: ip {0} is not reachable. Skipping.".format(msg.ipaddress)
        print result
        return result

GreyApp = Grey(greyConfig)

print(' [*] Waiting for messages. To exit press CTRL+C')
try:
    GreyApp.startConsumer()
except KeyboardInterrupt:
    print ("ABORTING GREY LISTENER")
    db_session.close()
