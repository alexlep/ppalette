# -*- coding: utf-8 -*-
import time
from datetime import datetime
from sqlalchemy import update, insert, and_
from database import init_db, db_session
from models import Status, History, Subnet, Host, Suite, Plugin
from mq import MQ
from tools import getUniqueID, Message
from processing import Consumer
from monitoring import RRD, Stats, CommonStats
from pvars import statRRDFile, rrdDataDir
from configs import gConfig, gLogger

class Grey(object):
    def __init__(self, configFile, testing=False):
        self.status = CommonStats(db_session)
        self.active = True
        if not testing:
            self.MQ = MQ(gConfig.queue)
            self.consumers = [ Consumer(self.MQ.PyConnection.channel(),
                                        gConfig.queue.inqueue,
                                        callback=self.callback)
                              for _ in range(gConfig.consumer_amount)]
            # statistics from violets, monitoring_inqueue
            self.mConsumer = Consumer(self.MQ.PyConnection.channel(),
                                      gConfig.queue.monitoring_inqueue,
                                      callback=self.updateVioletStats)

    def startConsumer(self):
        for c in self.consumers:
            c.start()
        self.mConsumer.start()
        while self.active:
            self.updateCommonStats()
            time.sleep(gConfig.stats_heartbeat)

    def destroy(self):
        for c in self.consumers:
            c.stop()
        self.mConsumer.stop()

    def callback(self, body):
        gLogger.debug("Received message {}".format(body))
        msg = Message(body, fromJSON=True)
        msg.convertStrToDate()
        if msg.type == 'check':
            self.updateStatusTable(msg)
            if gConfig.collect_history:
                self.updateHistory(msg)
        elif msg.type == 'task':
            if msg.action == 'discovery':
                gLogger.debug(self.tryAddingNewHost(msg))

    def updateVioletStats(self, data):
        """
        executed on every heartbeat message received from violet(s)
        """
        stats = Stats(data, fromJSON=True)
        myrrd = RRD("{0}/{1}.rrd".format(rrdDataDir, stats.identifier))
        myrrd.insertValues(stats)
        gLogger.info("Updated {} stats".format(stats.identifier))

    def updateCommonStats(self):
        """
        executed every N seconds in start functions, to gather common
        statistics, mostly from DB
        """
        self.status.update()
        RRD(statRRDFile).insertValues(self.status)
        gLogger.info("Updated common stats. Overall checks {0}"\
                     " , OK state {1}".format(self.status.checks_all,
                                              self.status.checks_ok))

    def updateStatusTable(self, msg):
        statusRecord = db_session.query(Status).\
                       filter(and_(Status.plugin_id == msg.plugin_id,\
                                   Status.host_id == msg.host_id)).first()
        if not statusRecord:
            statusRecord = Status(msg)
        else:
            statusRecord.update(msg)
        try:
            db_session.add(statusRecord)
            db_session.commit()
            gLogger.debug('Message {} was inserted into status table.'.\
                          format(msg.message_id))
        except Exception as e:
            gLogger.warning('Failed to insert {0} to status table. Reason:{1}'.\
                            format(msg.message_id, e))
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
                result = "AutoDiscovery: host with ip {0} is already in db."\
                         " Skipping.".format(msg.ipaddress)
        else:
            result = "AutoDiscovery: ip {0} is not reachable. Skipping.".\
                     format(msg.ipaddress)
        return result
