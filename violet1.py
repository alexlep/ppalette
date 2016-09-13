import pika

inQueue = 'redqueue'
outQueue = 'violetqueue'
rabbitMQHost = 'localhost'

inConnection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitMQHost))
outConnection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitMQHost))
inChannel = inConnection.channel()
outChannel = outConnection.channel()

inChannel.queue_declare(queue=inQueue)
outChannel.queue_declare(queue=outQueue)

def callback(ch, method, properties, body):
    msg = (" [x] Received %r" % body)
    print msg
    outChannel.basic_publish(exchange='', routing_key=outQueue, body=msg)


inChannel.basic_consume(callback, queue=inQueue, no_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
inChannel.start_consuming()
