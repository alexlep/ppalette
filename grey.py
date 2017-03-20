# -*- coding: utf-8 -*-
import sys
import os
import time
from core.database import init_db, db_session
from core.models import Status, History, Subnet, Host, Suite, Plugin
from datetime import datetime
from sqlalchemy import update, insert, and_
from core.mq import MQ
from core.tools import parseConfig, initLogging, getUniqueID, Message
from core.processing import Consumer
from core.monitoring import RRD, Stats, CommonStats
from core.pvars import greyConfigFile, statRRDFile, rrdDataDir

class Grey(object):
    def __init__(self, configFile, testing=False):
        self.config = parseConfig(configFile)
        self.log = initLogging(self.config.log, __name__) # init logging
        self.status = CommonStats(db_session)
        if not testing:
            self.MQ = MQ(self.config.queue)
            self.consumers = [ Consumer(self.MQ.initInRabbitPyQueue(
                                            self.config.queue.inqueue),
                                        funct=self.callback)
                              for _ in range(self.config.consumer_amount)]
            # statistics from violets, monitoring_inqueue
            self.mConsumer = Consumer(self.MQ.initInRabbitPyQueue(
                                        self.config.queue.monitoring_inqueue),
                                        funct = self.updateVioletStats)

    def startConsumer(self):
        for c in self.consumers:
            c.start()
        self.mConsumer.start()
        while True:
            self.updateCommonStats()
            time.sleep(3)

    def destroy(self):
        for c in self.consumers:
            c.join()

    def callback(self, body):
        msg = Message(body, fromJSON=True)
        if msg.type == 'check':
            self.updateStatusTable(msg)
            if self.config.collect_history:
                self.updateHistory(msg)
        elif msg.type == 'task':
            if msg.action == 'discovery':
                self.log.info(self.tryAddingNewHost(msg))

    def updateVioletStats(self, data):
        """
        executed on every heartbeat message received from violet(s)
        """
        stats = Stats(data, fromJSON = True)
        myrrd = RRD("{0}/{1}.rrd".format(rrdDataDir, stats.identifier))
        myrrd.insertValues(stats)

    def updateCommonStats(self):
        """
        executed every N seconds in start functions, to gather common
        statistics, mostly from DB
        """
        self.status.update()
        RRD(statRRDFile).insertValues(self.status)

    def updateStatusTable(self, msg):
        statusRecord = db_session.query(Status).\
                       filter(and_(Status.plugin_id == msg.plugin_id,\
                                   Status.host_id == msg.host_id)).first()
        if not statusRecord:
            statusRecord = Status(msg)
        else:
            statusRecord.update(msg)
            print 'hit'
        try:
            db_session.add(statusRecord)
            db_session.commit()
        except Exception as e:
            self.log.warning('{0}:{1} {2}'.format(statusRecord.host,
                                                  statusRecord.plugin,
                                                  e))
            print e
            pass

    def updateHistory(self, msg):
        h = History(msg)
        db_session.add(h)
        db_session.commit()

    def tryAddingNewHost(self, msg):
        if msg.exitcode == 0:
            existingHost = db_session.query(Host).\
                           filter(Host.ipaddress == msg.ipaddress).\
                           first()
            if (not existingHost):
                newHost = Host(ip=msg.ipaddress, suiteID=msg.suite_id,
                               subnetID=msg.subnet_id, hostname=msg.hostname)
                db_session.add(newHost)
                db_session.commit()
                result = "AutoDiscovery: ip {0} was successfully added".\
                         format(msg.ipaddress)
            else:
                result = "AutoDiscovery: host with ip {0} is already in db. Skipping.".format(msg.ipaddress)
        else:
            result = "AutoDiscovery: ip {0} is not reachable. Skipping.".\
                     format(msg.ipaddress)
        return result

if __name__ == "__main__":
    #init_db(False)
    GreyApp = Grey(greyConfigFile)
    print(' [*] Waiting for messages. To exit press CTRL+C')
    try:
        GreyApp.startConsumer()
    except KeyboardInterrupt:
        print ("ABORTING GREY LISTENER")
    #GreyApp.destroy()
        db_session.close()
