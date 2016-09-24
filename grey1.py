import pika, json
from core.database import init_db, db_session
from core.models import Schedule as TaskModel
from datetime import datetime
from sqlalchemy import update

init_db()


connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='violetqueue')

def callback(ch, method, properties, body):
    msg = (" [x] Received %r" % body)
    print msg
    jmsg = json.loads(body)
    check_time = datetime.strptime(jmsg['time'], "%H:%M:%S:%d:%m:%Y")
    updateQ = update(TaskModel).where(TaskModel.taskid==jmsg['taskid']).values(last_status=jmsg['output'], last_exitcode = jmsg['exitcode'], last_check_run = check_time)
    db_session.execute(updateQ)
    db_session.commit()

channel.basic_consume(callback, queue='violetqueue', no_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
