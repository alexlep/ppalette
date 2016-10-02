# -*- coding: utf-8 -*-
import pika, json
from core.database import init_db, db_session
from core.models import Status, History, Subnet, Host
from datetime import datetime
from sqlalchemy import update, insert, and_
from core.mq import MQ
from core import tools
from sqlalchemy.dialects import mysql

init_db(False)

greyConfig = './config/grey_config.json'

class Grey(object):
    def __init__(self, configFile):
        self.config = tools.parseConfig(configFile)
        self.logConfig = tools.draftClass(self.config.log)
        self.queueConfig = tools.draftClass(self.config.queue)
        self.log = tools.initLogging(self.logConfig) # init logging
        self.MQ = MQ(self.queueConfig)
        self.inChannel = self.MQ.initInChannel(self.callback)
        if not self.inChannel:
            self.log.error('Unable to connect to RabbitMQ. Please check config and RMQ service.')
            print "Unable to connect to RabbitMQ. Please check config and RMQ service."
            sys.exit(1)

    def startConsumer(self):
        self.inChannel.start_consuming()

    def callback(self, ch, method, properties, body):
        msg = tools.draftClass(json.loads(body))
        exec_time = datetime.strptime(msg.time, "%H:%M:%S:%d:%m:%Y")
        if msg.type == 'check':
            updateQ = Status.__table__.update().where(and_(Status.plugin_id==msg.pluginid, Status.host_id==msg.hostid)).\
                values(last_status=msg.output, last_exitcode = msg.exitcode, last_check_run = exec_time, interval = msg.interval)
            if not db_session.execute(updateQ).rowcount:
                insertQ = insert(Status).values(statusid = tools.getUniqueID(),
                                            plugin_id = msg.pluginid,
                                            host_id = msg.hostid,
                                            last_status=msg.output,
                                            last_exitcode = msg.exitcode,
                                            last_check_run = exec_time,
                                            interval = msg.interval)
                db_session.execute(insertQ)
        elif 'task':
            if msg.action == 'discovery':
                if (msg.exitcode == 0): # or ('filtered' in msg.output):
                    print body
                    newHost = Host()
                    newHost.hostUUID = tools.getUniqueID()
                    newHost.hostname = msg.hostname
                    newHost.ipaddress = msg.ipaddress
                    newHost.subnet_id = msg.subnet_id
                    newHost.suite_id = msg.suite_id
                    db_session.add(newHost)
                    self.log.info("AutoDiscovery: ip {0} was successfully added".format(msg.ipaddress))
                else:
                    self.log.info("AutoDiscovery: ip {0} is not reachable. Skipping.".format(msg.ipaddress))
        """Sched = Schedule.query.filter_by(taskid=msg.taskid).first()
        Sched.last_status = msg.output
        Sched.last_exitcode = msg.exitcode
        Sched.last_check_run = check_time
        h = History()
        h.host_id = Sched.host_id
        h.plugin_id = Sched.plugin_id
        h.check_run_time = check_time
        h.check_status = msg.output
        h.check_exicode = msg.exitcode
        h.interval = Sched.interval
        h.desc = Sched.desc
        db_session.add(h)"""
        db_session.commit()

GreyApp = Grey(greyConfig)

print(' [*] Waiting for messages. To exit press CTRL+C')
try:
    GreyApp.startConsumer()
except KeyboardInterrupt:
    print ("ABORTING GREY LISTENER")
    db_session.close()
