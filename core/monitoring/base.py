# -*- coding: utf-8 -*-
import json
from core.models import Host, Status, Plugin, Suite
from core.tools import dateToStr

VIOLET = 'violet'
COMMON = 'common'

class CommonStats(object):
    mtype = COMMON
    interval = 60
    data_sources = ['checks_ok', 'checks_warn',
                    'checks_error', 'checks_all',
                    'checks_active', 'hosts_all',
                    'hosts_active_up', 'checks_incorrect',
                    'ram_used'
                    ]

    def __init__(self, db_session):
        self.dbs = db_session
        for ds in self.data_sources:
            setattr(self, ds, None)

    def update(self):
        self.hosts_active = self.dbs.query(Host.id).\
                                    filter(Host.maintenance == False).count()
        self.hosts_all = self.dbs.query(Host.id).count()
        self.hosts_active_up = self.dbs.query(Host.id).\
                                join((Status, Host.stats)).\
                                join((Plugin, Status.plugin)).\
                                filter(Host.maintenance == False,
                                       Status.last_exitcode == 0,
                                       Plugin.script == 'check_ping').\
                                count()
        self.checks_active = self.dbs.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Host.maintenance == False).\
                                count()
        self.checks_all = self.dbs.query(Plugin.id).\
                                join((Suite, Plugin.suites)).\
                                join((Host, Suite.hosts)).\
                                count()
        self.checks_ok = self.dbs.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 0,
                                       Host.maintenance == False).\
                                count()
        self.checks_warn = self.dbs.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 1,
                                       Host.maintenance == False).\
                                count()
        self.checks_error = self.dbs.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 2,
                                       Host.maintenance == False).\
                                count()
        self.checks_incorrect = self.dbs.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 3,
                                       Host.maintenance == False).\
                                count()

    def getStatDict(self):
        res = dict()
        for elem in self.data_sources:
            res[elem] = getattr(self, elem)
        return res

    def tojson(self):
        return json.dumps(self.getStatDict())

class Stats(object):
    mtype = VIOLET
    interval = None
    status = None
    identifier = None
    worker_count = None
    worker_alive = None
    consumers_count = None
    consumers_alive = None
    publishers_alive = None
    senders_alive = None
    input_queue_size = None
    throughput = None
    max_throughput = None
    connection_time = None
    last_update_time = None
    ram_used = None
    data_sources = ['worker_count', 'worker_alive',
                    'consumers_count', 'consumers_alive',
                    'publishers_count','publishers_alive',
                    'input_queue_size', 'throughput',
                    'ram_used'
                    ]

    def __init__ (self, data = dict(), fromJSON = False):
        if fromJSON:
            data = json.loads(data)
        self.__dict__.update(data)

    def getStatDict(self):
        res = dict()
        for elem in self.data_sources:
            res[elem] = getattr(self, elem)
        return res

    def tojson(self):
        return json.dumps(self.getStatDict())

    def tojsonAll(self):
        return json.dumps(self.__dict__)

    def setConnectionTime(self):
        self.connection_time = dateToStr()

class BaseMonitoring(object):
    def insertValues(self, statdata, **kwargs):
        pass

    def fetch(self):
        pass

    def getLatestUpdate(self):
        pass

    def getChartData(self, hours=6, grades=10):
        pass
