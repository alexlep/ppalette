# -*- coding: utf-8 -*-
from flask import Flask
from core.blueif import webif, db_session
from core.red_scheduler import Scheduler
from core.tools import parseConfig, draftClass, initLogging

blueConfigFile = './config/blue_config.json'
redConfigFile = './config/red_config.json'

blueConfig = parseConfig(blueConfigFile)

#sblueConfLog = draftClass(blueConfig.log)
#log = initLogging(blueConfLog) # init logging

RedApp = Scheduler(redConfigFile)
RedApp.startRedService()

BlueApp = Flask (__name__)
BlueApp.secret_key="a92547e3847063649d9d732a183418bf"
#BlueApp.config['DEBUG'] = True

@BlueApp.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

if blueConfig.webif_enabled:
    webif.init_app(BlueApp)
    webif.Scheduler = RedApp

#bcrypt.init_app(app)
#BlueApp.run(debug=True, host='0.0.0.0', threaded=True)
