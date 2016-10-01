# -*- coding: utf-8 -*-
import sys
from flask import Flask
from core.mq import MQ
from core.tools import parseConfig, draftClass, initLogging
from core.blueif import webif, db_session, init_db

blueConfig = './config/blue_config.json'

config = parseConfig(blueConfig)
confQueue = draftClass(config.queue)
confLog = draftClass(config.log)
isMQ = confQueue.isMQ

if isMQ:
    MQ = MQ('s', confQueue) # init MQ
    mqOutChannel = MQ.initOutChannel()
    if (not mqOutChannel):
        print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
        sys.exit(1)

#log = initLogging(confLog) # init logging

arg = ''.join(sys.argv[1:]) or True
if arg == 'i':
    dbc = init_db(create_tables=True)
else:
    dbc = init_db(create_tables=False)

if not dbc:
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)

app = Flask (__name__)
app.secret_key="a92547e3847063649d9d732a183418bf"
app.config['DEBUG'] = True

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

#bcrypt.init_app(app)
webif.init_app(app)

app.run(debug=True, host='0.0.0.0', threaded=True)
