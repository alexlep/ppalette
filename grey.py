# -*- coding: utf-8 -*-
import pika, json
from core.database import init_db, db_session
from core.models import Status, History
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
        self.MQ = MQ('c', self.queueConfig)
        self.inChannel = self.MQ.initInChannel() # from red
        if (not self.inChannel):
            print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
            sys.exit(1)
        self.inChannel.basic_consume(self.callback, queue=self.queueConfig.inqueue, no_ack=True)

    def startConsumer(self):
        self.inChannel.start_consuming()

    def callback(self, ch, method, properties, body):
        #print (" [x] Received %r" % body)
        msg = tools.draftClass(json.loads(body))
        check_time = datetime.strptime(msg.time, "%H:%M:%S:%d:%m:%Y")
        #print type(check_time)
        #Status.update().
        #try:
        updateQ = Status.__table__.update().where(and_(Status.plugin_id==msg.pluginid, Status.host_id==msg.hostid)).\
                values(last_status=msg.output, last_exitcode = msg.exitcode, last_check_run = check_time, interval = msg.interval)
        if not db_session.execute(updateQ).rowcount:
            insertQ = insert(Status).values(statusid = tools.getUniqueID(),
                                            plugin_id = msg.pluginid,
                                            host_id = msg.hostid,
                                            last_status=msg.output,
                                            last_exitcode = msg.exitcode,
                                            last_check_run = check_time,
                                            interval = msg.interval)
            db_session.execute(insertQ)

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
    print dir(db_session)
    GreyApp.startConsumer()
except KeyboardInterrupt:
    print "ABORTING GREY LISTENER"
    db_session.close()
