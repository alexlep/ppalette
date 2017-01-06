# -*- coding: utf-8 -*-
import os
from flask import Flask

from core.redapi import initRedApiBP
from core.pscheduler import Scheduler
from core.database import init_db

workingDir = os.path.dirname(os.path.abspath(__file__))
redConfigFile = workingDir + '/config/red_config.json'

if not init_db(False):
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)

RedScheduler = Scheduler(redConfigFile)
RedScheduler.start()

RedApi = Flask (__name__)
RedApi.secret_key="my_favourite_secret_key_here"
RedApi.register_blueprint(initRedApiBP(RedScheduler))
if __name__ == '__main__':
    RedApi.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
