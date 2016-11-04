# -*- coding: utf-8 -*-
import sys, os, pika, json
from datetime import datetime, timedelta
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from ipaddress import IPv4Network
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.ext.serializer import loads, dumps

import tools
from mq import MQ
from models import Plugin, Host, Suite, Subnet
from database import init_db, db_session
from core.threaded import Factory

class Scheduler(BackgroundScheduler):
    def __init__(self, configFile):
        super(BackgroundScheduler, self).__init__( {'apscheduler.executors.default': {
        'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
        'max_workers': '1'
        }})
        self.config = tools.parseConfig(configFile)
        self.logConfig = tools.draftClass(self.config.log)
        self.log = tools.initLogging(self.logConfig)
        self.queueConfig = tools.draftClass(self.config.queue)
        self.MQ = MQ(self.queueConfig) # init MQ
        self.mqCommonJobsOutChannel = self.MQ.initOutRabbitPyChannel() # to violet
        #if (not self.mqCheckOutChannel) or (not self.mqCommonJobsOutChannel):
        #    print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
        #    sys.exit(1)
        #self.outChannel = self.MQ.initOutChannel()
        """self.factory = Factory(serviceType = 'red',
                               workers_count = self.config.process_count,
                               mq_out_queue = self.queueConfig.outqueue,
                               mq_handler = self.MQ,
                               logger = self.log)"""
        self.fillSchedule()

    def startRedService(self):
        #self.factory.startWork()
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

    def prepareStartTime(self, delta):
        startDelay = timedelta(0, delta)
        initTime = datetime.now()
        return initTime + startDelay

    def fillSchedule(self):
        self.remove_all_jobs()
        schedule = self.getAllActiveTasksFromDB()
        taskdict = dict()
        for job in schedule:
            if job.interval not in taskdict.keys():
                taskdict[job.interval] = list()
            taskdict[job.interval].append(job)
            #self.registerJob(job)
        startTime = self.prepareStartTime(15)
        for key in taskdict.keys():
            print key, len(taskdict[key]), len(taskdict[key]) % key, len(taskdict[key]) / key #35 192 17 5
            counter = 0
            for item in taskdict[key]:
                if counter == key: counter = 0
                self.registerJob(job = item, jobStartTime = startTime + timedelta(0, counter))
                counter += 1

    def getAllActiveTasksFromDB(self):
        return db_session.query(Plugin.id.label('pluginid'),
                                Plugin.pluginUUID, Plugin.script, Plugin.interval, Plugin.params, Plugin.ssh_wrapper,
                                Host.id.label('hostid'), Host.hostUUID, Host.ipaddress, Host.hostname, Host.login, Host.maintenance).\
                join((Suite, Plugin.suites)).\
                join((Host, Suite.host))

    def getSingleActiveTaskFromDB(self, hostUUID, pluginUUID):
        return db_session.query(Plugin.id.label('pluginid'),
                                Plugin.pluginUUID, Plugin.script, Plugin.interval, Plugin.params, Plugin.ssh_wrapper,
                                Host.id.label('hostid'), Host.hostUUID, Host.ipaddress, Host.hostname, Host.login, Host.maintenance).\
                join((Suite, Plugin.suites)).\
                join((Host, Suite.host)).\
                filter(Host.hostUUID == hostUUID, Plugin.pluginUUID == pluginUUID).first()

    def registerJob(self, job, jobStartTime = False):
        jobDict = tools.prepareDictFromSQLA(job)
        message = tools.Message(jobDict)
        message.type = 'check'
        jobid = message.getScheduleJobID()
        if jobStartTime:
            self.add_job(self.sendCommonJobToMQ, args=[message], trigger = 'interval', id = jobid, seconds = message.interval,
                     misfire_grace_time=10, next_run_time = jobStartTime)
        else:
            self.add_job(self.sendCommonJobToMQ, args=[message], trigger = 'interval', id = jobid, seconds = message.interval,
                     misfire_grace_time=10)
        if job.maintenance:
            self.pause_job(jobid)

    def addJobFromDB(self, jobid):
        task = Host.query.filter_by(taskid=jobid).first()
        try:
            self.registerJob(task)
        except ConflictingIdError: # task already running, re-enabling, TODO: calculations with old task
            print "removing"
            self.remove_job(jobid)
            print "adding"
            self.registerJob(task)
        return

    def resumeHostFromMaintenance(self, host):
        for plugin in host.suite.plugins:
            try:
                self.resume_job("{0}{1}".format(host.hostUUID, plugin.pluginUUID))
            except JobLookupError:
                newjob = self.getSingleActiveTaskFromDB(host.hostUUID, plugin.pluginUUID)
                self.registerJob(newjob)

    ### --------------------------------------

    def sendCommonJobToMQ(self, jobMessage):
        msg = jobMessage.tojson(refreshTime = True)
        message = self.MQ.prepareMsg(self.mqCommonJobsOutChannel, msg)
        message.publish('', self.queueConfig.outqueue)
        #self.mqCommonJobsOutChannel.basic_publish(exchange='', routing_key=self.queueConfig.outqueue, body=msg)
        return

    def sendDiscoveryRequest(self, subnetid):
        subnet = Subnet.query.filter_by(id=subnetid).first()
        try:
            ipaddresses = list(IPv4Network(u'{0}/{1}'.format(subnet.subnet, subnet.netmask)))
        except AttributeError:
            self.log.warning("Cannot find subnet with id {0}. Discovery failed.".format(subnetid))
            return None
        for ipaddress in ipaddresses:
            discoveryJob = tools.Message({})
            discoveryJob.ipaddress = str(ipaddress)
            discoveryJob.subnet_id = subnet.id
            discoveryJob.suite_id = subnet.suite_id
            discoveryJob.action = 'discovery'
            discoveryJob.type = 'task'
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
