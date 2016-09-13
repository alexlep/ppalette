from flask import Flask, abort
from datetime import datetime, timedelta
from core import database
from core.models import Schedule as ScheduleModel
import sys, os, pika
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import json

logFileName = 'red.log'
hrmqHst = 'localhost'

logger = logging.getLogger('')
hdlr = logging.FileHandler(logFileName)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)


class Scheduler(BackgroundScheduler):
    def __init__(self, ScheduleModel, refreshInterval):
        super(BackgroundScheduler, self).__init__()
        self.scheduleModel = ScheduleModel
        self.refreshInterval = refreshInterval
        self.fillSchedule()
        self.start()

    def getAllActiveTasksFromDB(self):
        return self.scheduleModel.query.filter_by(enabled=True).all()

    def fillSchedule(self):
        self.remove_all_jobs()
        tasks = self.getAllActiveTasksFromDB()
        for task in tasks:
            self.registerJob(task)
        print "reloaded"

    def addJobFromDB(self, id):
        task = self.scheduleModel.query.filter_by(enabled=True, id=id).first()
        self.registerJob(task)

    def registerJob(self, task):
        self.add_job(self.event, trigger = 'interval', id = str(task.id), seconds = task.interval,
                                args=[task.plugins.name, task.host.hostname, task.host.ipaddress, task.interval])

    def event(self, job, host, ip, interval):
        message = {}
        message['plugin'] = job
        message['host'] = host
        message['ip'] = ip
        msg = json.dumps(message)
        rmqConnection = pika.BlockingConnection(pika.ConnectionParameters(host=hrmqHst))
        rmgChannel = rmqConnection.channel()
        rmgChannel.queue_declare(queue='redqueue')
        rmgChannel.basic_publish(exchange='', routing_key='hello', body=msg)

        print('{0} was sent to queue for {1} at (interval is {2})'.format(job,
                                                                    host,
                                                                    interval))

ss = Scheduler(ScheduleModel, 20)
redapp = Flask('red')

#if __name__ == '__main__':

@redapp.route('/job/add/<id_>', methods=['GET','POST'])
def add_job(id_):
    try:
        ss.addJobFromDB(int(id_))
    except:
        abort(500)
    return 'Hello, World!'

@redapp.route('/job/remove/<id_>', methods=['GET','POST'])
def remove_job(id_):
    if id_ == 'all':
        ss.remove_all_jobs()
    return 'removed'

@redapp.route('/job/get/<id_>', methods=['GET','POST'])
def get_job(id_):
    if id_ == 'all':
        ss.get_jobs()
    else:
        try:
            ss.get_job(int(id_))
        except:
            abort(500)
    return '200'

@redapp.route('/job/pause/<id_>', methods=['GET','POST'])
def pause_job(id_):
    if id_ == 'all':
        ss.pause()
    else:
        try:
            ss.pause_job(id_)
        except:
            abort(500)
    return '200'

@redapp.route('/job/resume/<id_>', methods=['GET','POST'])
def resume_job(id_):
    if id_ == 'all':
        ss.resume()
    else:
        try:
            ss.resume_job(id_)
        except:
            abort(500)
    return '200'

@redapp.route('/schedule/reload', methods=['GET','POST'])
def reloadJobs():
    try:
        ss.fillSchedule()
    except:
        abort(500)
    return '200'

redapp.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False, threaded=True)
