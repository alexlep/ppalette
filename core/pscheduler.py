import sys
from datetime import datetime, timedelta
#from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler

from tools import Message, prepareDictFromSQLA, getUniqueID, dateToStr
from mq import MQ
from models import Plugin, Host, Suite, Subnet
from database import db_session
from configs import rConfig, rLogger

class Scheduler(BackgroundScheduler):
    def __init__(self):
        super(BackgroundScheduler, self).__init__(\
            {
                'apscheduler.executors.default':
                {
                    'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
                    'max_workers': '1'
                }
            })
        self.MQ = MQ(rConfig.queue) # init MQ
        self.mqCommonJobsOutChannel = self.MQ.initOutRabbitPyChannel()
        schStartTime = self.fillSchedule()
        rLogger.info("Scheduler was successfully initialized. Start planned "\
                     "at {}".format(dateToStr(schStartTime)))

    def _prepareStartTime(self, delta):
        startDelay = timedelta(0, delta)
        initTime = datetime.now()
        return initTime + startDelay

    def fillSchedule(self):
        """
        """
        self.remove_all_jobs()
        startTime = self._prepareStartTime(10)
        for plug in db_session.query(Plugin):
            self.registerJob(plugin=plug, jobStartTime=startTime)
        return startTime

    def registerJob(self, plugin, jobStartTime=False):
        """
        """
        job_params = dict(args=[plugin.pluginUUID], trigger='interval',
                          id=plugin.pluginUUID, seconds=plugin.interval,
                          misfire_grace_time=10,
                          name="{0};{1};{2}".format(plugin.script,
                                                    plugin.customname,
                                                    plugin.interval))
        if jobStartTime:
            job_params.update(next_run_time=jobStartTime)
        self.add_job(self.sendPluginJobsToMQ, **job_params)

    def sendPluginJobsToMQ(self, pluginUUID):
        counter = 0
        plugin = Plugin.query.filter(Plugin.pluginUUID == pluginUUID).first()
        for suite in plugin.suites:
            for host in suite.hosts:
                if not host.maintenance:
                    checkJob = Message(plugin=plugin, host=host,
                                       suite=suite)
                    checkJob.type = 'check'
                    checkJob.scheduled_time = dateToStr(datetime.now())
                    checkJob.message_id = getUniqueID()
                    self.sendCommonJobToMQ(checkJob)
                    counter += 1
        rLogger.info("Plugin {0}, interval {1}, sent {2} check to RMQ".\
                     format(plugin.customname, plugin.interval, str(counter)))

    ### --------------------------------------
    def sendCommonJobToMQ(self, jobMessage):
        msg = jobMessage.tojson()
        self.MQ.sendM(self.mqCommonJobsOutChannel, msg)

    def getApiHostPortConfig(self):
        return (rConfig.webapi.host, rConfig.webapi.port)
