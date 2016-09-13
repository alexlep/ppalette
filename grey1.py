import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='violetqueue')

def callback(ch, method, properties, body):
    msg = (" [x] Received %r" % body)
    print msg
    #rmgChannel.basic_publish(exchange='direct', routing_key='violetqueue', body=msg)


channel.basic_consume(callback, queue='violetqueue', no_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
