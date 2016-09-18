import pika, json
from core import database
from core.models import Schedule as TaskModel
from datetime import datetime

database.init_db()


connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='violetqueue')

def callback(ch, method, properties, body):
    msg = (" [x] Received %r" % body)
    print msg
    jmsg = json.loads(body)
    check_time = datetime.strptime(jmsg['time'], "%H:%M:%d:%m:%Y")
    #print dir(TaskModel)
    TaskModel.__table__.update().where(TaskModel.id==int(jmsg['taskid'])).values(last_status=jmsg['output'], last_exitcode = jmsg['exitcode'], last_check_run = check_time)
    #rmgChannel.basic_publish(exchange='direct', routing_key='violetqueue', body=msg)


channel.basic_consume(callback, queue='violetqueue', no_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
