# -*- coding: utf-8 -*-
import sys, os, pika, logging, json
from datetime import datetime, timedelta
import tools
from database import init_db, db_session
from mq import MQ
from models import Plugin, Host, Suite, Subnet
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from netaddr import IPSet

class Scheduler(BackgroundScheduler):
    def __init__(self, configFile):
        super(BackgroundScheduler, self).__init__()
        self.config = tools.parseConfig(configFile)
        self.logConfig = tools.draftClass(self.config.log)
        self.queueConfig = tools.draftClass(self.config.queue)
        self.log = tools.initLogging(self.logConfig) # init logging
        self.MQ = MQ(self.queueConfig) # init MQ
        self.mqCheckOutChannel = self.MQ.initOutChannel() # to violet
        self.mqCommonJobsOutChannel = self.MQ.initOutChannel() # to violet
        if (not self.mqCheckOutChannel) or (not self.mqCommonJobsOutChannel):
            print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
            sys.exit(1)
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

    def fillSchedule(self):
        self.remove_all_jobs()
        jobs = self.getAllActiveTasksFromDB()
        for job in jobs:
            jobdDict = tools.prepareDictFromSQLA(job)
            jobClass = tools.draftClass(jobdDict)
            self.registerJob(jobClass)
        print "reloaded"

    def getAllActiveTasksFromDB(self):
        return db_session.query(Plugin.id.label('pluginid'),
                                Plugin.pluginUUID, Plugin.script, Plugin.interval, Plugin.params,
                                Host.id.label('hostid'), Host.hostUUID, Host.ipaddress, Host.hostname).\
                join((Suite, Plugin.suites)).\
                join((Host, Suite.host))

    def registerJob(self, job):
        self.add_job(self.sendCheckToMQ, trigger = 'interval', id = job.hostUUID + job.pluginUUID,
                        seconds = job.interval,
                        args=[job])

    def addJobFromDB(self, jobid):
        task = ScheduleModel.query.filter_by(taskid=jobid).first()
        try:
            self.registerJob(task)
        except ConflictingIdError: # task already running, re-enabling, TODO: calculations with old task
            print "removing"
            self.remove_job(jobid)
            print "adding"
            self.registerJob(task)

    ###--------------------------
    def sendCheckToMQ(self, job):
        message = self.prepareCheckJobMessage(job)
        self.mqCheckOutChannel.basic_publish(exchange='', routing_key=self.queueConfig.outqueue, body=message)
        print('{0} was sent to queue) ').format(message)
        return

    def prepareCheckJobMessage(self, job):
        job.type = 'check'
        return json.dumps(job.__dict__)
    ###--------------------------
    def sendCommonJobToMQ(self, job):
        message = self.prepareCommonJobMessage(job)
        self.mqCommonJobsOutChannel.basic_publish(exchange='', routing_key=self.queueConfig.outqueue, body=message)
        print('{0} was sent to queue) ').format(message)
        return

    def prepareCommonJobMessage(self, job):
        job.type = 'task'
        return json.dumps(job.__dict__)

    def sendDiscoveryRequest(self, subnetid):
        subnet = Subnet.query.filter_by(id=subnetid).first()
        try:
            ipaddresses = list(IPSet(['{0}/{1}'.format(subnet.subnet, subnet.netmask)]))
        except AttributeError:
            self.log.warning("Cannot find subnet with if {0}. DIscovery failed.".format(subnetid))
            return None
        for ipaddress in ipaddresses:
            discoveryJob = tools.draftClass({})
            discoveryJob.ipaddress = str(ipaddress)
            discoveryJob.subnet_id = subnet.id
            discoveryJob.suite_id = subnet.suite_id
            discoveryJob.action = 'discovery'
            self.sendCommonJobToMQ(discoveryJob)
        return
#if __name__ =='__main__':
#    if not init_db(False):
#        print "Service is unable to connect to DB. Check if DB service is running. Aborting."
#        sys.exit(1)
#RedApp = Scheduler(redConfig)
#    try:
#        RedApp.startConsumer()
#    except KeyboardInterrupt:
#        db_session.close()
#        print "aborted once again..."
