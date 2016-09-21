import sys, os, pika, logging, json
from flask import Flask, abort
from datetime import datetime, timedelta
from core import tools
from core.database import init_db, db_session
from core.mq import MQ
from core.models import Schedule as ScheduleModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import ConflictingIdError

redConfig = './config/red_config.json'

class Scheduler(BackgroundScheduler):
    def __init__(self, configFile):
        super(BackgroundScheduler, self).__init__()
        self.config = tools.parseConfig(configFile)
        self.logConfig = tools.createClass(self.config.log)
        self.queueConfig = tools.createClass(self.config.queue)
        #self.log = tools.initLogging(self.logConfig) # init logging
        self.MQ = MQ('m', self.queueConfig) # init MQ
        if (not self.MQ.inChannel) or (not self.MQ.outChannel):
            print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
            sys.exit(1)
        self.MQ.inChannel.basic_consume(self.taskChange, queue=self.queueConfig.inqueue, no_ack=True)
        self.fillSchedule()
        self.start()

    def taskChange(self, ch, method, properties, body):
        message = tools.fromJSON(body)
        if message:
            msg = tools.createClass(message)
            if msg.value:
                self.addJobFromDB(msg.taskid)
            else:
                self.remove_job(str(msg.taskid))
        else:
            self.log.WARN("An error while decoding json through API interface")

    def startListener(self):
        self.MQ.inChannel.start_consuming()

    def getAllActiveTasksFromDB(self):
        return ScheduleModel.query.filter_by(enabled=True).all()

    def fillSchedule(self):
        self.remove_all_jobs()
        tasks = self.getAllActiveTasksFromDB()
        for task in tasks:
            self.registerJob(task)
        print "reloaded"

    def addJobFromDB(self, jobid):
        task = ScheduleModel.query.filter_by(id=jobid).first()
        try:
            self.registerJob(task)
        except ConflictingIdError: # task already running, re-enabling, TODO: calculations with old task
            print "removing"
            self.remove_job(str(jobid))
            print "adding"
            self.registerJob(task)

    def registerJob(self, task):
        self.add_job(self.event, trigger = 'interval', id = str(task.id), seconds = task.interval,
                                args=[task])


    def event(self, task):
        message = tools.prepareDict(converted = True,
                                    plugin = task.plugin.name,
                                    host = task.host.hostname,
                                    ip = task.host.ipaddress,
                                    type = "check",
                                    params = task.plugin.params,
                                    taskid = task.id)
        self.MQ.sendMessage(message)
        print('{0} was sent to queue for {1} at (interval is {2}, task is {3})'.format(task.plugin.name,
                                                                    task.host.hostname,
                                                                task.interval, task.id))

if __name__ =='__main__':
    if not init_db():
        print "Service is unable to connect to DB. Check if DB service is running. Aborting."
        sys.exit(1)
    ss = Scheduler(redConfig)
    try:
        ss.startListener()
    except KeyboardInterrupt:
        print "aborted once again..."
