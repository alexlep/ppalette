# -*- coding: utf-8 -*-
import time
from sqlalchemy import update, insert, and_
from database import db_session, clearDBConnection
from models import Status, Host, Plugin
from mq import MQ
from tools import Message, getPluginModule
from processing import Consumer
from configs import gConfig, gLogger, cConfig
from monitoring.violetstats import Stats
from monitoring.commonstats import CommonStats

monit = getPluginModule(cConfig.mon_engine,
                        cConfig.mon_plugin_path,
                        gLogger)

if gConfig.collect_history:
    hist = getPluginModule(cConfig.hist_engine,
                            cConfig.hist_plugin_path,
                            gLogger)

class Grey(object):
    def __init__(self, configFile, testing=False):
        self.status = CommonStats()
        self.active = True
        self.commonMonit = monit.Monitor()
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
        db_session.close()

    @clearDBConnection
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
        self.violetMonit = monit.Monitor(stats.identifier)
        self.violetMonit.insertValues(stats)
        gLogger.info("Updated {} stats".format(stats.identifier))

    def updateCommonStats(self):
        """
        executed every N seconds in start functions, to gather common
        statistics, mostly from DB
        """
        self.status.update()
        self.commonMonit.insertValues(self.status)
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
            db_session.rollback()
            gLogger.warning('Failed to insert {0} to status table. Reason:{1}'.\
                            format(msg.message_id, e))
            pass

    def updateHistory(self, msg):
        histInst = hist.History()
        histInst.insertValues(msg)
        #print histInst.getValues(hostID=1, pluginID=4)
        #h = History(msg)
        #db_session.add(h)
        #db_session.commit()

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
