import sys, os, pika, logging, json
from flask import Flask, abort
from datetime import datetime, timedelta
from core import database, tools
from core.mq import MQ
from core.models import Schedule as ScheduleModel
from apscheduler.schedulers.background import BackgroundScheduler

redConfig = './config/red_config.json'

class Scheduler(BackgroundScheduler):
    def __init__(self, configFile):
        super(BackgroundScheduler, self).__init__()
        self.configFile = tools.parseConfig(configFile)
        self.conf = self.configFile['configuration']
        self.log = tools.initLogging(self.conf['log']) # init logging
        self.MQ = MQ('m', self.conf['queue']) # init MQ
        self.MQ.inChannel.basic_consume(self.taskChange, queue=self.MQ.inQueue, no_ack=True)
        self.fillSchedule()
        self.start()

    def taskChange(self, ch, method, properties, body):
        message = tools.fromJSON(body)
        if message:
            msg = tools.createMessage(message)
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

    def addJobFromDB(self, id):
        task = ScheduleModel.query.filter_by(id=id).first()
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
        print('{0} was sent to queue for {1} at (interval is {2})'.format(task.plugin.name,
                                                                    task.host.hostname,
                                                                    task.interval))
database.init_db()
ss = Scheduler(redConfig)
try:
    ss.startListener()
except KeyboardInterrupt:
    print "aborted once again..."
