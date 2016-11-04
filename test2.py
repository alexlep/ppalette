# -*- coding: utf-8 -*-
import pika, json
from core.database import init_db, db_session
from core.models import Suite, Plugin, Host
from datetime import datetime
from sqlalchemy import update
import time
from core import tools
from core.mq import MQ


#init_db(False)


from apscheduler.schedulers.background import BackgroundScheduler

redConfigFile = './config/red_config.json'

config = tools.parseConfig(redConfigFile)
logConfig = tools.draftClass(config.log)
log = tools.initLogging(logConfig)
queueConfig = tools.draftClass(config.queue)
mqueue = MQ(queueConfig) # init MQ
mqueue.initPy()
mqCheckOutChannel = mqueue.initOutRabbitPyChannel()

#msg = mqueue.prepareMsg(mqCheckOutChannel, 'dwdwefwefwefwefwefwefwefwefweff#$#@')
msg2 = mqueue.prepareMsg(mqCheckOutChannel, '{"ssh_wrapper": false, "hostid": 715, "script": "check_ftp", "type": "check", "pluginUUID": "68d47916-a9f9-4755-a441-9053e0e5a3de", "interval": 90, "pluginid": 8, "params": "-t 4", "maintenance": false, "scheduled_time": "18:51:12:29:10:2016", "login": "violet", "hostUUID": "76c52251-4a77-4bdc-8e79-e47c6a53f636", "ipaddress": "195.154.103.235", "hostname": "195-154-103-235.rev.poneytelecom.eu"}')
for _ in range(1000000):
    #msg.publish('', queueConfig.outqueue)
    msg2.publish('', queueConfig.outqueue)
    print _

mqCheckOutChannel.close()

#import logging
#from apscheduler.scheduler import Scheduler

# FTP OK - 0,085 second response time on port 21 [220-J'ai l'impression que quand le nombre d'individus se multiplie,\r\n220-leurs intelligences se divisent proportionnellement.\r\n220-\t-+- Pierre Desproges -+-\r\n220 This is a private system - No anonymous login]
"""
Demonstrates how to use the blocking scheduler to schedule a job that executes on 3 second
intervals.
"""
'''
from datetime import datetime
import os

from apscheduler.schedulers.blocking import BlockingScheduler


def tick():
    print('Tick! The time is: %s' % datetime.now())


if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(tick, 'interval', seconds=3)
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

'''
#connection = pika.BlockingConnection(pika.ConnectionParameters(
        #host='localhost'))
#channel = connection.channel()

#channel.queue_declare(queue='violetqueue')
"""
def callback(ch, method, properties, body):
    msg = (" [x] Received %r" % body)
    print msg
    jmsg = json.loads(body)
    check_time = datetime.strptime(jmsg['time'], "%H:%M:%S:%d:%m:%Y")
    updateQ = update(TaskModel).where(TaskModel.taskid==jmsg['taskid']).values(last_status=jmsg['output'], last_exitcode = jmsg['exitcode'], last_check_run = check_time)
    db_session.execute(updateQ)
    db_session.commit()
"""
#channel.basic_consume(callback, queue='violetqueue', no_ack=True)

#print(' [*] Waiting for messages. To exit press CTRL+C')
#channel.start_consuming()
"""while True:
    #tasks = Schedule.query.all()
    #db_session.expire(Schedule())
    #db_session.refresh(Schedule())
    #tasks = db_session.query(Plugin).join((Subset, Plugin.subsets)).join(Host, Subset.host).all() #join((Department, Group.departments)).filter(Department.name == 'R&D')#Plugin.query.filter(Plugin.subsets.any()).all()
    #hosts = Host.query.all()
    #tasks = Plugin.query.filter(Subset.plugins.any(Host.query.all())).all()
    tasks =  db_session.query(Plugin.pluginid, Plugin.script, Plugin.interval, Plugin.params, Host.hostid, Host.ipaddress).\
                join((Suite, Plugin.suites)).\
                join((Host, Suite.host)).all()
    #print tasks
    for i in tasks:
        print dict(zip(i.keys(), i))
    #print dir(hosts[0])
    print '---'
    time.sleep(1)"""
