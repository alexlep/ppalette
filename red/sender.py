#!/usr/bin/env python
import pika, sys


message = ' '.join(sys.argv[1:]) or "Yopt!"

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='hosttask')

channel.basic_publish(exchange='',
                      routing_key='hello',
                      body=message)
print(" [x] Sent 'Hello World!'")
connection.close()
