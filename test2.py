# -*- coding: utf-8 -*-
import pika, json
from core.database import init_db, db_session
from core.models import Suite, Plugin, Host
from datetime import datetime
from sqlalchemy import update
import time

#init_db(False)


from apscheduler.schedulers.background import BackgroundScheduler

#import logging
#from apscheduler.scheduler import Scheduler


"""
Demonstrates how to use the blocking scheduler to schedule a job that executes on 3 second
intervals.
"""

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
