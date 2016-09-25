# -*- coding: utf-8 -*-
import pika, json
from core.database import init_db, db_session
from core.models import Schedule, History
from datetime import datetime
from sqlalchemy import update, insert
from core import tools

init_db(False)


connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='violetqueue')

def callback(ch, method, properties, body):
    msg = (" [x] Received %r" % body)
    print msg
    msg = tools.createClass(json.loads(body))
    check_time = datetime.strptime(msg.time, "%H:%M:%S:%d:%m:%Y")
    """
    updateQ = update(Schedule).where(Schedule.taskid==jmsg['taskid']).values(last_status=jmsg['output'], last_exitcode = jmsg['exitcode'], last_check_run = check_time)
    db_session.execute(updateQ)
    insertQ = insert(History).values(last_status=jmsg['output'], last_exitcode = jmsg['exitcode'], last_check_run = check_time)
    db_session.execute(insertQ)
    """
    Sched = Schedule.query.filter_by(taskid=msg.taskid).first()
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
    db_session.add(h)
    db_session.commit()


channel.basic_consume(callback, queue='violetqueue', no_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
