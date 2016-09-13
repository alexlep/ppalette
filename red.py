"""
This example demonstrates the use of the SQLAlchemy job store.
On each run, it adds a new alarm that fires after ten seconds.
You can exit the program, restart it and observe that any previous alarms that have not fired yet
are still active. You can also give it the database URL as an argument.
See the SQLAlchemy documentation on how to construct those.
"""
from flask import Flask, abort
from datetime import datetime, timedelta
from core import database
from core.models import Schedule as ScheduleModel
import sys, os, pika
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import json

logger = logging.getLogger('')
hdlr = logging.FileHandler('myapp.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

hrmqHst = 'localhost'

class Scheduler(object):
    def __init__(self, ScheduleModel, refreshInterval):
        self.scheduler = BackgroundScheduler()
        #print dir (self.scheduler)
        self.ScheduleModel = ScheduleModel
        self.refreshInterval = refreshInterval
        self.fillSchedule()
        self.startScheduler()

    def getAllActiveTasksFromDB(self):
        return self.ScheduleModel.query.filter_by(enabled=True).all()

    def fillSchedule(self):
        self.removeAllJobs()
        print "reloaded"
        tasks = self.getAllActiveTasksFromDB()
        for task in tasks:
            # (task.host_id, task.plugin_id, task.interval)s
            self.scheduler.add_job(self.event, trigger = 'interval', id = str(task.id), seconds = task.interval,
                                    args=[task.plugins.name, task.host.hostname, task.host.ipaddress, task.interval]) #
        #self.scheduler.add_job(self.fillSchedule, id = 'internal1', trigger = 'interval', seconds = self.refreshInterval)

    def addJob(self, id):
        task = ScheduleModel.query.filter_by(enabled=True, id=id).all()
        self.scheduler.add_job(self.event, trigger = 'interval', id = str(task.id), seconds = task.interval,
                                args=[task.plugins.name, task.host.hostname, task.interval])# ,
    def removeJob(self, id):
        self.scheduler.remove_job(id)

    def removeAllJobs(self):
        self.scheduler.remove_all_jobs()

    def pauseJob(self, id):
        self.scheduler.pause_job(id)

    def resumeAllJobs(self):
        self.scheduler.resume()

    def resumeJob(self, id):
        self.scheduler.resume_job(id)

    def pauseAllJobs(self):
        self.scheduler.pause()

    def getJob(self, id):
        print self.scheduler.get_job(id)

    def getAllJobs(self):
        print self.scheduler.get_jobs()

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

    def startScheduler(self):
        self.scheduler.start()

def run_scheduler():
    try:
        print "1"
    except (KeyboardInterrupt, SystemExit):
        pass

ss = Scheduler(ScheduleModel, 20)
redapp = Flask('red')

#if __name__ == '__main__':

@redapp.route('/job/add/<id_>', methods=['GET','POST'])
def add_job(id_):
    #try:
    ss.addJob(id_)
    #except:
    #    abort(500)
    return 'Hello, World!'

@redapp.route('/job/remove/<id_>', methods=['GET','POST'])
def remove_job(id_):
    if id_ == 'all':
        ss.removeAllJobs()
    return 'removed'

@redapp.route('/job/get/<id_>', methods=['GET','POST'])
def get_job(id_):
    if id_ == 'all':
        ss.getAllJobs()
    else:
        try:
            ss.getJob(int(id_))
        except:
            abort(500)
    return '200'

@redapp.route('/job/pause/<id_>', methods=['GET','POST'])
def pause_job(id_):
    if id_ == 'all':
        ss.pauseAllJobs()
    else:
        try:
            ss.pauseJob(id_)
        except:
            abort(500)
    return '200'

@redapp.route('/job/resume/<id_>', methods=['GET','POST'])
def resume_job(id_):
    if id_ == 'all':
        ss.resumeAllJobs()
    else:
        try:
            ss.resumeJob(id_)
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
