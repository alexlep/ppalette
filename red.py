# -*- coding: utf-8 -*-
import sys, os, pika, logging, json
from flask import Flask, abort
from datetime import datetime, timedelta
from core import tools
from core.database import init_db, db_session
from core.mq import MQ
from core.models import Plugin, Host, Suite
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError

redConfig = './config/red_config.json'

class Scheduler(BackgroundScheduler):
    def __init__(self, configFile):
        super(BackgroundScheduler, self).__init__()
        self.config = tools.parseConfig(configFile)
        self.logConfig = tools.draftClass(self.config.log)
        self.queueConfig = tools.draftClass(self.config.queue)
        self.log = tools.initLogging(self.logConfig) # init logging
        self.MQ = MQ('m', self.queueConfig) # init MQ
        self.mqInChannel = self.MQ.initInChannel() # from blue
        self.mqOutChannel = self.MQ.initOutChannel() # to violet
        if (not self.mqInChannel) or (not self.mqOutChannel):
            print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
            sys.exit(1)
        self.mqInChannel.basic_consume(self.taskChange, queue=self.queueConfig.inqueue, no_ack=True)
        self.fillSchedule()
        self.start()

    def taskChange(self, ch, method, properties, body):
        message = tools.fromJSON(body)
        if message:
            msg = tools.createClass(message)
            if msg.value:
                self.addJobFromDB(msg.taskid)
            else:
                try:
                    self.remove_job(msg.taskid)
                except JobLookupError: # remove alredy removed job
                    pass
        else:
            self.log.WARN("An error while decoding json through API interface")

    def startListener(self):
        self.mqInChannel.start_consuming()

    def fillSchedule(self):
        self.remove_all_jobs()
        tasks = self.getAllActiveTasksFromDB()
        for task in tasks:
            taskdict = tools.prepareDictFromSQLA(task)
            taskclass = tools.draftClass(taskdict)
            self.registerJob(taskclass)
        print "reloaded"

    def getAllActiveTasksFromDB(self):
        return db_session.query(Plugin.pluginid, Plugin.script, Plugin.interval, Plugin.params, Host.hostid, Host.ipaddress).\
                join((Suite, Plugin.suites)).\
                join((Host, Suite.host))

    def registerJob(self, task):
        self.add_job(self.event, trigger = 'interval', id = task.hostid + task.pluginid,
                        seconds = task.interval,
                        args=[task])


    def event(self, task):
        message = tools.prepareCheckMessage(converted = True, task = task)
        self.mqOutChannel.basic_publish(exchange='', routing_key=self.queueConfig.outqueue, body=message)
        print('{0} was sent to queue) ').format(message) #for {1} at (interval is {2}, task is {3})'.format(task.plugin.check,
                                                    #                task.host.hostname,
                                                    #            task.interval, task.taskid))

    def addJobFromDB(self, jobid):
        task = ScheduleModel.query.filter_by(taskid=jobid).first()
        try:
            self.registerJob(task)
        except ConflictingIdError: # task already running, re-enabling, TODO: calculations with old task
            print "removing"
            self.remove_job(jobid)
            print "adding"
            self.registerJob(task)

if __name__ =='__main__':
    if not init_db(False):
        print "Service is unable to connect to DB. Check if DB service is running. Aborting."
        sys.exit(1)
    ss = Scheduler(redConfig)
    try:
        ss.startListener()
    except KeyboardInterrupt:
        db_session.close()
        print "aborted once again..."
