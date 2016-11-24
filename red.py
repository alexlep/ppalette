# -*- coding: utf-8 -*-
import sys, os
from datetime import datetime, timedelta
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from ipaddress import IPv4Network
from flask import Flask
from core.redapi import initRedApiBP

from core.tools import parseConfig, initLogging, Message, prepareDictFromSQLA
from core.mq import MQ
from core.models import Plugin, Host, Suite, Subnet
from core.database import init_db, db_session

workingDir = os.path.dirname(os.path.abspath(__file__))
redConfigFile = workingDir + '/config/red_config.json'

class Scheduler(BackgroundScheduler):
    def __init__(self, configFile):
        super(BackgroundScheduler, self).__init__( {'apscheduler.executors.default': {
        'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
        'max_workers': '2'
        }})
        self.config = parseConfig(configFile)
        self.log = initLogging(self.config.log, __name__)
        self.MQ = MQ(self.config.queue, self.log) # init MQ
        self.mqCommonJobsOutChannel = self.MQ.initOutRabbitPyChannel() # to violet
        self.fillSchedule()
        self.Violets = dict()

    def updateMonitoring(self):
        pass

    def startRedService(self):
        self.start()

    def _prepareStartTime(self, delta):
        startDelay = timedelta(0, delta)
        initTime = datetime.now()
        return initTime + startDelay

    def fillSchedule(self):
        """ Fill Execution Scheduler
        Fetches all tasks (hosts and their plugins) and generates
        schedule from them. Distibutes the load for each plugin type.
        If plugin is executed every 5 seconds for 10 hosts, they will be
        distributed in such way:
        seconds:    1   2   3   4   5
        ------------|---|---|---|---|-
        hosts:      1   2   3   4   5
                    6   7   8   9   10
        """
        self.remove_all_jobs()
        taskdict = dict()
        for job in self._getAllActiveTasksFromDB():
            if job.interval not in taskdict.keys():
                taskdict[job.interval] = list()
            taskdict[job.interval].append(job)
        startTime = self._prepareStartTime(15)
        for key in taskdict.keys():
            counter = 0
            for item in taskdict[key]:
                if counter == key: counter = 0
                self._registerJob(job = item,
                                  jobStartTime = startTime + timedelta(0, counter))
                counter += 1

    def _getAllActiveTasksFromDB(self):
        """
        Gets all the tasks(hosts and assigned plugins) from DB
        """
        return db_session.query(Plugin.id.label('pluginid'),
                                Plugin.pluginUUID, Plugin.script, Plugin.interval, Plugin.params, Plugin.ssh_wrapper,
                                Host.id.label('hostid'), Host.hostUUID, Host.ipaddress, Host.hostname, Host.login, Host.maintenance).\
                                join((Suite, Plugin.suites)).\
                                join((Host, Suite.host))

    def _getSingleActiveTaskFromDB(self, hostUUID, pluginUUID):
        """
        Gets single task from DB
        """
        return db_session.query(Plugin.id.label('pluginid'),
                                Plugin.pluginUUID, Plugin.script, Plugin.interval, Plugin.params, Plugin.ssh_wrapper,
                                Host.id.label('hostid'), Host.hostUUID, Host.ipaddress, Host.hostname, Host.login, Host.maintenance).\
                                join((Suite, Plugin.suites)).\
                                join((Host, Suite.host)).\
                                filter(Host.hostUUID == hostUUID, Plugin.pluginUUID == pluginUUID).first()

    def _registerJob(self, job, jobStartTime = False):
        """
        Adds task to shedule. If host is iuner maintenance - job is in paused
        state.
        """
        jobDict = prepareDictFromSQLA(job)
        message = Message(jobDict)
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

    def resumeHostFromMaintenance(self, host):
        """
        Activates all the tasks of the host, which was in maintenance mode.
        If the host was added while sheduler was already running, by default
        host is in maintenance mode without tasks in shcedule, so tasks will be
        automatically added here once maintenance mode will be deactivated.
        As of now - distribution algorithm from fillSchedule is ignored for
        newly added hosts, but full service restart will take care of new
        hosts.
        """
        for plugin in host.suite.plugins:
            try:
                self.resume_job("{0}{1}".format(host.hostUUID, plugin.pluginUUID))
            except JobLookupError:
                newjob = self._getSingleActiveTaskFromDB(host.hostUUID, plugin.pluginUUID)
                self._registerJob(newjob)

    ### --------------------------------------
    def sendCommonJobToMQ(self, jobMessage):
        msg = jobMessage.tojson(refreshTime = True)
        message = self.MQ.prepareMsg(self.mqCommonJobsOutChannel, msg)
        message.publish('', self.config.queue.outqueue)
        return

    def sendDiscoveryRequest(self, subnetid):
        subnet = Subnet.query.filter_by(id=subnetid).first()
        try:
            ipaddresses = list(IPv4Network(u'{0}/{1}'.format(subnet.subnet, subnet.netmask)))
        except AttributeError:
            self.log.warning("Cannot find subnet with id {0}. Discovery failed.".format(subnetid))
            return None
        for ipaddress in ipaddresses:
            discoveryJob = Message()
            discoveryJob.ipaddress = str(ipaddress)
            discoveryJob.subnet_id = subnet.id
            discoveryJob.suite_id = subnet.suite_id
            discoveryJob.action = 'discovery'
            discoveryJob.type = 'task'
            self.sendCommonJobToMQ(discoveryJob)
        return
#if __name__ =='__main__':
if not init_db(False):
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)

RedApp = Scheduler(redConfigFile)
#RedApp.startRedService()
    #if RedApp.config.webapi:

RedApi = Flask (__name__)
RedApi.secret_key="a92547e3847063649d9d732a183418bf"
RedApi.register_blueprint(initRedApiBP(RedApp, db_session))
#RedApi.run(debug=False, host='0.0.0.0', port=5001, threaded=True)
    #else:
    #    import time
    #    while True:
    #        time.sleep(1)
