# -*- coding: utf-8 -*-
import datetime as dt
import time
import os.path
import rrdtool
import json
from tools import draftClass
import inspect
from models import Host, Status, Plugin, Suite

VIOLET = 'violet'
COMMON = 'common'

class CommonStats(object):
    interval = 60
    checks_ok = None
    checks_warn = None
    checks_error = None
    checks_all = None
    checks_active = None
    hosts_all = None
    hosts_active_up = None
    data_sources = ['checks_ok', 'checks_warn',
                    'checks_error', 'checks_all',
                    'checks_active', 'hosts_all',
                    'hosts_active_up'
                    ]
    unmonitored_items = ['interval', 'data_sources']

    def __init__(self, db_session):
        self.dbs = db_session

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
                                join((Host, Suite.host)).\
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

class Stats(object):
    interval = None
    status = None
    identifier = None
    worker_count = None
    worker_alive = None
    consumers_count = None
    consumers_alive = None
    senders_count = None
    senders_alive = None
    input_queue_size = None
    throughput = None
    max_throughput = None
    connection_time = None
    last_update_time = None
    ram_used = None
    raw_amount = None
    data_sources = ['worker_count', 'worker_alive',
                    'consumers_count', 'consumers_alive',
                    'senders_count','senders_alive',
                    'input_queue_size', 'throughput',
                    ]

    def __init__ (self, data = dict(), fromJSON = False):
        if fromJSON:
            data = json.loads(data)
        self.__dict__.update(data)

    def tojson(self):
        return json.dumps(self.__dict__)

    def setConnectionTime(self):
        self.connection_time = dt.datetime.now().strftime("%H:%M:%S:%d:%m:%Y")

class RRD(object):
    def __init__(self, filename, statType = COMMON):
        self.rrd = filename
        if statType == COMMON:
            self.paramsToMonitor = ['checks_ok', 'checks_warn', 'checks_error',
                                    'checks_active']
        elif VIOLET:
            self.paramsToMonitor = ['input_queue_size', 'throughput']

    def createFile(self, statdata):
        """
        Initial timestamp of creation is message time minus message interval,
        so the first value(update after creating table) could be successful.
        Otherwise we will get rrd error, because creation timestamp will be
        equal to first update timestamp.
        """
        try:
            start_timestamp = int(time.mktime(
                                    dt.datetime.strptime(
                                        statdata.last_update_time,
                                        "%H:%M:%S:%d:%m:%Y").\
                                            timetuple())) - statdata.interval
        except Exception as e:
            start_timestamp = int(time.mktime(
                                    dt.datetime.now().\
                                        timetuple())) - statdata.interval
        args = [self.rrd,
                "--start", str(start_timestamp),
                '--step', str(statdata.interval),
                "RRA:AVERAGE:0.5:1:1440", "RRA:AVERAGE:0.5:60:744"]
        args.extend(self._getDataSourcesRRDList(statdata.data_sources,
                                                statdata.interval))
        rrdtool.create(*args)

    def insertValues(self, statdata):
        if not os.path.isfile(self.rrd):
            self.createFile(statdata)
        rrdtool.update(self.rrd, '-t', \
                       self._getDataSourcesString(statdata.data_sources), \
                       self._getDataValuesString(statdata, useStatDate = True))

    def fetch(self):
        return rrdtool.fetch(self.rrd,'-r','60', "AVERAGE")

    def getLatestUpdate(self):
        return rrdtool.lastupdate(self.rrd)

    def getChartData(self, hours=6, grades=10):
        stats = dict()
        stats['ds'] = dict()
        stats['meta'] = dict()
        stepToGet = 3600 * hours / grades
        raw_stats = [ rrdtool.xport('--maxrows', str(grades),
                                    '--start', 'now-{}h'.format(hours),
                                    '--end', 'now',
                                    '--step', str(stepToGet),
                                    "DEF:a={0}:{1}:AVERAGE".format(self.rrd, param),
                                    'XPORT:a:{}'.format(param)) \
                                    for param in self.paramsToMonitor]
        for elem in raw_stats:
            legend = elem['meta']['legend'][0]
            #{meta: 'description', value: 1 },
            tmp = map(self.prepareValue, elem['data'][1:-1]) # excluding first and last ones
            stats['ds'][legend] = map(lambda x: {'meta':legend,'value':x}, tmp)
        rows = raw_stats[0]['meta']['rows']
        start = raw_stats[0]['meta']['start']
        step = raw_stats[0]['meta']['step']
        stats['meta']['labels'] = [ (dt.datetime.fromtimestamp(start)\
                                            + dt.timedelta(seconds=step*val))\
                                            .strftime("%H:%M")\
                                            for val in range(1, rows-1) ] # first and last ones
        return stats

    def prepareValue(self, value):
        """
        int float values fron rrd, and correctly convert None values
        """
        try:
            nvalue = int(value[0])
        except:
            nvalue = None
        return nvalue

    def _getDataSourcesRRDList(self, dataSources, interval):
        return [ 'DS:{0}:GAUGE:{1}:0:100000'.format(ds, interval) \
                for ds in dataSources ]

    def _getDataSourcesString(self, dataSources):
        return str(":".join(dataSources))

    def _getDataValuesString(self, params, useStatDate=False):
        try:
            stime = str(int(time.mktime(
                                dt.datetime.strptime(params.last_update_time,
                                                     "%H:%M:%S:%d:%m:%Y").\
                                                    timetuple())))
        except:
            stime = 'N' # now
        values = [str(int(params.__dict__[ds])) for ds in params.data_sources]
        return "{0}:{1}".format(stime, ":".join(values))
