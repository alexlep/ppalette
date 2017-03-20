# -*- coding: utf-8 -*-
import os
import sys
from flask import Flask

from core.redapi import initRedApiBP
from core.pscheduler import Scheduler
from core.database import init_db
from core.env import redConfigFile

if not init_db(False):
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)

RedScheduler = Scheduler(redConfigFile)
RedScheduler.start()

host = RedScheduler.config.webapi.host
port = RedScheduler.config.webapi.port

RedApi = Flask (__name__)
RedApi.secret_key="my_favourite_secret_key_here"
RedApi.register_blueprint(initRedApiBP(RedScheduler))
if __name__ == '__main__':
    RedApi.run(debug=False, host=host, port=port, threaded=True)
