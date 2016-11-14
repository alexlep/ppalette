# -*- coding: utf-8 -*-
import sys, os
from core.database import init_db, db_session
from core.models import Status, History, Subnet, Host, Suite, Plugin
from datetime import datetime
from sqlalchemy import update, insert, and_
from core.mq import MQ
from core.tools import parseConfig, initLogging, getUniqueID, Message
from core.processing import Consumer
import time
from core.monitoring import RRD, Stats, CommonStats
from glob import glob

init_db(False)
workingDir = os.path.dirname(os.path.abspath(__file__))
greyConfig = workingDir + '/config/grey_config.json'

class Grey(object):
    def __init__(self, configFile):
        self.collectHistory = False
        self.config = parseConfig(configFile)
        self.log = initLogging(self.config.log, __name__) # init logging
        self.MQ = MQ(self.config.queue, self.log)
        self.consumers = [Consumer(self.MQ.initInRabbitPyQueue(self.config.queue.inqueue), funct = self.callback) for _ in range(self.config.consumer_amount)]
        self.monitoringConsumer = Consumer(self.MQ.initInRabbitPyQueue(self.config.queue.monitoring_inqueue), funct = self.updateVioletStats) # statistics from violets, monitoring_inqueue
        self.rrdCommon = 'common_statistics.rrd'

    def startConsumer(self):
        for c in self.consumers:
            c.start()
        self.monitoringConsumer.start()
        while True:
            self.updateCommonStats()
            time.sleep(3)

    def destroy(self):
        for c in self.consumers:
            c.join()

    def callback(self, body):
        msg = Message(body, fromJSON = True)
        #print msg.scheduled_time
        if msg.type == 'check':
            msg.time = datetime.strptime(msg.time, "%H:%M:%S:%d:%m:%Y")
            msg.scheduled_time = datetime.strptime(msg.scheduled_time, "%H:%M:%S:%d:%m:%Y")
            self.updateStatusTable(msg)
            if self.collectHistory:
                self.updateHistory(msg)
        elif 'task':
            if msg.action == 'discovery':
                self.log.info(self.tryAddingNewHost(msg))

    def updateVioletStats(self, data):
        """
        executed on every heartbeat message received from violet(s)
        """
        stats = Stats(data, fromJSON = True)
        myrrd = RRD("{}.rrd".format(stats.identifier))
        myrrd.insertValues(stats)

    def updateCommonStats(self):
        """
        executed every N seconds in start functions, to gather common statistics, mostly from DB
        """
        status = CommonStats()
        status.hosts_active = db_session.query(Host.id).filter(Host.maintenance == False).count()
        status.hosts_all = db_session.query(Host.id).count()
        status.hosts_active_up = db_session.query(Host.id).join((Status, Host.stats)).\
                                join((Plugin, Status.plugin)).\
                                filter(Host.maintenance == False, Status.last_exitcode == 0, Plugin.script == 'check_ping').\
                                count()
        start1 = time.time()
        status.checks_active = db_session.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Host.maintenance == False).\
                                count()
        status.checks_all = db_session.query(Plugin.id).\
                                join((Suite, Plugin.suites)).\
                                join((Host, Suite.host)).\
                                count()
        status.checks_ok = db_session.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 0, Host.maintenance == False).\
                                count()
        status.checks_warn = db_session.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 1, Host.maintenance == False).\
                                count()
        status.checks_error = db_session.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 2, Host.maintenance == False).\
                                count()
        print 'First Method: ', time.time() - start1
        print status.__dict__
        status.updateDataSources()
        RRD(self.rrdCommon).insertValues(status)
        '''
        if stats.identifier not in self.Violets.keys():
            stats.setConnectionTime()
            self.Violets[stats.identifier] = stats.__dict__
        else:
            self.Violets[stats.identifier].update(stats.__dict__)
        for v in self.Violets.values():
            try: # PYTHON bug here, strptime in threads
                v.performChecks()
            except:
                pass
        '''
    def updateStatusTable(self, msg):
        updateQ = Status.__table__.update().where(and_(Status.plugin_id==msg.pluginid, Status.host_id==msg.hostid)).\
            values(last_status=msg.output, last_exitcode = msg.exitcode,
                   last_check_run = msg.time, scheduled_check_time = msg.scheduled_time,
                   interval = msg.interval)
        try:
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
        except Exception as e:
            print e
            pass
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
    #GreyApp.destroy()
    db_session.close()
