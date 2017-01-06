import sys
from datetime import datetime, timedelta
#from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from ipaddress import IPv4Network

from tools import parseConfig, initLogging, Message,\
                        prepareDictFromSQLA, getUniqueID
from mq import MQ
from models import Plugin, Host, Suite, Subnet
from database import db_session

class Scheduler(BackgroundScheduler):
    def __init__(self, configFile):
        super(BackgroundScheduler, self).__init__( {'apscheduler.executors.default': {
        'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
        'max_workers': '1'
        }})
        self.config = parseConfig(configFile)
        try:
            self.log = initLogging(self.config.log, __name__)
        except IOError as ioe:
            print "Unable to reach log file {}".format(ioe.filename)
            print "Error: {}".format(ioe.strerror)
            sys.exit(1)
        self.MQ = MQ(self.config.queue, self.log) # init MQ
        self.mqCommonJobsOutChannel = self.MQ.initOutRabbitPyChannel() # to violet
        self.fillSchedule()

    def _prepareStartTime(self, delta):
        startDelay = timedelta(0, delta)
        initTime = datetime.now()
        return initTime + startDelay

    def fillSchedule(self):
        """
        """
        self.remove_all_jobs()
        startTime = self._prepareStartTime(10)
        for plug in db_session.query(Plugin): #options(joinedload(Plugin.suites)).options(joinedload(Suite.host)):
            self.registerJob(plugin = plug, jobStartTime = startTime)

    def registerJob(self, plugin, jobStartTime = False):
        """
        """
        job_params = dict(args=[plugin], trigger='interval', id=plugin.pluginUUID,
                          seconds=plugin.interval, misfire_grace_time=10,
                          name="{0};{1};{2}".format(plugin.script,
                                                    plugin.customname,
                                                    plugin.interval))
        if jobStartTime:
            job_params.update(next_run_time=jobStartTime)
        self.add_job(self.sendPluginJobsToMQ, **job_params)

    def sendPluginJobsToMQ(self, plugin):
        for suite in plugin.suites:
            for host in suite.host:
                if not host.maintenance:
                    checkJob = Message(plugin=plugin, host=host,
                                       suite=suite)
                    checkJob.type = 'check'
                    self.sendCommonJobToMQ(checkJob)

    ### --------------------------------------
    def sendCommonJobToMQ(self, jobMessage):
        msg = jobMessage.tojson(refreshTime = True)
        message = self.MQ.prepareMsg(self.mqCommonJobsOutChannel, msg)
        message.publish(str(), self.config.queue.outqueue)

    def sendDiscoveryRequest(self, subnetid):
        subnet = Subnet.query.filter_by(id=subnetid).first()
        try:
            ipaddresses = list(IPv4Network(u'{0}/{1}'.format(subnet.subnet,
                                                             subnet.netmask)))
        except AttributeError:
            self.log.warning("Cannot find subnet with id {0}. Discovery failed.".format(subnetid))
            return None
        for ipaddress in ipaddresses:
            discoveryJob = Message(subnet=subnet)
            discoveryJob.ipaddress = str(ipaddress)
            discoveryJob.action = 'discovery'
            discoveryJob.type = 'task'
            self.sendCommonJobToMQ(discoveryJob)
        return
#if __name__ =='__main__':
