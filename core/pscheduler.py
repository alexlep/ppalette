from apscheduler.jobstores.base import JobLookupError, ConflictingIdError
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import and_

from tools import Message, getUniqueID, dateToStr, prepareDiscoveryMessages,\
                  prepareStartTime
from mq import MQ
from models import Plugin, Host, Subnet, Suite
from database import db_session, clearDBConnection
from configs import rConfig, rLogger

class Scheduler(BackgroundScheduler):
    def __init__(self):
        super(BackgroundScheduler, self).__init__(\
            {
                'apscheduler.executors.default':
                {
                    'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
                    'max_workers': '2'
                }
            })
        self.jobMapper = {
            'Plugin' : self.sendPluginJobsToMQ,
            'Subnet' : self.sendDiscoveryRequest,
        }
        self.MQ = MQ(rConfig.queue) # init MQ
        self.mqJobsOutChannel = self.MQ.initOutRabbitPyChannel()
        self.mqDiscOutChannel = self.MQ.initOutRabbitPyChannel()
        schStartTime = self.fillSchedule()
        rLogger.info("Scheduler was successfully initialized. Start planned "\
                     "at {}".format(dateToStr(schStartTime)))

    def _dbCommitIfDirty(self):
        if db_session.dirty or db_session.deleted:
            db_session.commit()

    def _dbClearSession(self):
        db_session.remove()

    @clearDBConnection
    def fillSchedule(self):
        """
        """
        self.remove_all_jobs()
        startTime = prepareStartTime(10)
        self._registerChecks(startTime)
        self._registerDiscoveries(startTime)
        self._registerDBSync()
        return startTime

    def _registerChecks(self, startTime):
        """Fetches all plugins and adds jobs to scheduler.
        If plugin is marked for delete and wasn't delete due to some issues -
        we are not adding if to scheduler, and it should be deleted during
        next run of db_sync job
        """
        for plug in Plugin.query.filter(Plugin.sync_state!=2):
            self._registerJob(plug, jobStartTime=startTime)
            if not plug.isSynced():
                plug.markSynced()
                db_session.add(plug)
        self._dbCommitIfDirty()

    def _registerDiscoveries(self, startTime):
        """Same as _registerChecks, but for discoveries.
        """
        for sn in Subnet.query.filter(Subnet.auto_discovery==True,
                                      Subnet.sync_state!=2):
            self._registerJob(sn, startTime)
            if not sn.isSynced():
                sn.markSynced()
                db_session.add(sn)
        self._dbCommitIfDirty()

    def _registerDBSync(self):
        """Sync job. Executed Every 10 seconds.
        """
        job_params = dict(trigger='interval',
                          id='DB_SYNC_JOB', seconds=10,
                          misfire_grace_time=5)
        self.add_job(self._dbSync, **job_params)

    def _dbSync(self):
        """Checks sync_state column in DB tables
        """
        self._syncRecords(Plugin.query.filter(Plugin.sync_state!=0))
        self._syncRecords(Subnet.query.filter(Subnet.auto_discovery==True,
                                              Subnet.sync_state!=0))
        #self._dbCommitIfDirty()

    @clearDBConnection
    def _syncRecords(self, records):
        """If item is new (sync_state=1) - adding to scheduler.
        If it's marked for delete (sync_state=2), we are deleting job from
        scheduler and removing record from table in DB.
        If item is updated(sync_state=3) - modifying existing job in scheduler.
        If wasn't changed (sync_state=0) - passing by.
        """
        for item in records:
            if item.isNew():
                try:
                    self._registerJob(item,
                                      jobStartTime=prepareStartTime(10))
                except ConflictingIdError:
                    rLogger.warning("DB_sync job has tried to add already "\
                                    "existing job to scheduler (id {})".\
                                    format(item.UUID))
                item.markSynced()
                db_session.add(item)
            elif item.isForDelete():
                try:
                    self.remove_job(item.UUID)
                except JobLookupError:
                    rLogger.warning("DB_sync job has tried to delete "\
                                    "inexisting job from scheduler (id {})".\
                                    format(item.UUID))
                db_session.delete(item)
            elif item.isForUpdate():
                self.reschedule_job(item.UUID,
                                    trigger='interval',
                                    seconds=item.interval)
                item.markSynced()
                db_session.add(item)
        self._dbCommitIfDirty()

    def _registerJob(self, item, jobStartTime=False):
        """
        """
        job_params = dict(args=[item.UUID], trigger='interval',
                          id=item.UUID, seconds=item.interval,
                          misfire_grace_time=10,
                          name=item.generateJobName())
        if jobStartTime:
            job_params.update(next_run_time=jobStartTime)
        self.add_job(self.jobMapper.get(item.__class__.__name__),
                     **job_params)

    @clearDBConnection
    def sendPluginJobsToMQ(self, pluginUUID):
        counter = 0
        now = dateToStr()
        plugin = Plugin.query.filter(Plugin.UUID == pluginUUID).first()
        for suite in plugin.suites:
            for host in suite.hosts:
                if not host.maintenance:
                    checkJob = self._prepareSingleCheck(plugin=plugin,
                                                       host=host,
                                                       suite=suite,
                                                       schTime=now)
                    self.sendCommonJobToMQ(checkJob)
                    counter += 1
        rLogger.debug("Plugin {0}, interval {1}, sent {2} check to RMQ".\
                     format(plugin.customname, plugin.interval, str(counter)))

    def _prepareSingleCheck(self, plugin, suite, host, schTime=None):
        checkJob = Message(plugin=plugin,
                           host=host,
                           suite=suite)
        checkJob.type = 'check'
        checkJob.message_id = getUniqueID()
        if not schTime:
            checkJob.scheduled_time = dateToStr()
        else:
            checkJob.scheduled_time = schTime
        return checkJob

    def sendDiscoveryRequest(self, subnetUUID):
        subnet = Subnet.query.filter(Subnet.UUID == subnetUUID).first()
        self.pushDiscovery(subnet)

    def pushDiscovery(self, subnet):
        for discJob in prepareDiscoveryMessages(subnet):
            self.MQ.sendM(self.mqDiscOutChannel, discJob)

    ### --------------------------------------
    def sendCommonJobToMQ(self, jobMessage):
        msg = jobMessage.tojson()
        self.MQ.sendM(self.mqJobsOutChannel, msg)

    def getApiHostPortConfig(self):
        return (rConfig.webapi.host, rConfig.webapi.port)

    def getSinglePlugin(self, pluginName, hostIP):
        return db_session.query(Plugin, Suite, Host).\
                                join((Suite, Plugin.suites)).\
                                join((Host, Suite.hosts)).\
                                filter(and_(Plugin.customname == pluginName,
                                       Host.ipaddress == hostIP)).first()

    @clearDBConnection
    def pushSingleCheck(self, pluginName, hostIP):
        """
        Should be executed on API call
        """
        inst = self.getSinglePlugin(pluginName, hostIP)
        if inst:
            plug, suite, host = inst
            if host.maintenance:
                return dict(message='host is under maintenance. Rejected'), 401
            single = self._prepareSingleCheck(plugin=plug,
                                             suite=suite,
                                             host=host)
            self.sendCommonJobToMQ(single)
            res = dict(message="Single check for {}/{} was sent."\
                               .format(pluginName, hostIP))
            exitcode = 200
        else:
            res = dict(message="Plugin/host relation not found in DB")
            exitcode = 404
        return res, exitcode

    @clearDBConnection
    def sendDiscoveryFromAPI(self, subnetname):
        subnet = Subnet.query.filter(Subnet.name == subnetname).first()
        if subnet:
            self.pushDiscovery(subnet)
            res = dict(message='Discovery request for {} was sent to clients'.\
                       format(subnetname))
            exitcode = 200
        else:
            res = dict(message='Discovery cancelled - {} not found in db'.\
                       format(subnetname))
            exitcode = 404
        return res, exitcode
