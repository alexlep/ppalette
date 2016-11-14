# -*- coding: utf-8 -*-
import datetime as dt
import time
import os.path
import rrdtool
import json
from copy import deepcopy
from tools import draftClass

class CommonStats(object):
    interval = 60
    checks_ok = int()
    checks_warn = int()
    checks_error = int()
    checks_all = int()
    checks_active = int()
    hosts_all = int()
    hosts_maintenance = int()
    hosts_active_up = int()

    def updateDataSources(self):
        unmonitored_items = ['interval', 'data_sources']
        self.data_sources = self.__dict__.keys()
        for item in unmonitored_items:
            try:
                self.data_sources.remove(item)
            except:
                pass

class Stats(object):
    interval = int()
    status = int()
    identifier = str()
    worker_count = int()
    worker_alive = int()
    consumers_count = int()
    consumers_alive = int()
    senders_count = int()
    senders_alive = int()
    input_queue_size = int()
    throughput = int()
    max_throughput = int()
    connection_time = str()
    last_update_time = str()
    ram_used = int()
    raw_amount = int()

    def __init__ (self, data = dict(), fromJSON = False):
        if fromJSON:
            data = json.loads(data)
        self.__dict__.update(data)
        self.data_sources = self.getDataSources()

    def getDataSources(self):
        unmonitored_items = ['interval', 'identifier','last_update_time', 'connection_time', 'data_sources']
        keys = deepcopy(self.__dict__.keys())
        for item in unmonitored_items:
            try:
                keys.remove(item)
            except:
                pass
        return keys

    def tojson(self):
        return json.dumps(self.__dict__)

    def setConnectionTime(self):
        self.connection_time = dt.datetime.now().strftime("%H:%M:%S:%d:%m:%Y")

    def performChecks(self):
        """
        Check when heartbeat was last time updated.
        if interval * 3 = warning (status 1)
        if interval * 10 = error (status 2)
        """
        current_date = dt.datetime.now()
        last_hb_sent = dt.datetime.strptime(self.last_update_time, "%H:%M:%S:%d:%m:%Y")
        diff = (current_date - last_hb_sent).seconds
        if diff > (self.interval * 10):
            self.status = 2
        elif diff > (self.interval * 3):
            self.status = 1
        else:
            self.status = 0

class RRD(object):
    def __init__(self, filename):
        self.rrd = filename
        self.commonParamsToMonitor = ['checks_ok', 'checks_warn', 'checks_error', 'checks_active']
        self.violetParamsToMonitor = ['input_queue_size', 'throughput']

    def createFile(self, statdata):
        """
        Initial timestamp of creation is message time minus message interval, so the first value(update after creating table) could be successful.
        Otherwise we will get rrd error, because creation timestamp will be equal to first update timestamp.
        """
        try:
            start_timestamp = int(time.mktime(dt.datetime.strptime(statdata.last_update_time, "%H:%M:%S:%d:%m:%Y"))) - statdata.interval
        except:
            start_timestamp = int(time.mktime(dt.datetime.now().timetuple())) - statdata.interval
        args = [self.rrd,
                "--start", str(start_timestamp),
                '--step', str(statdata.interval),
                "RRA:AVERAGE:0.5:1:1440", "RRA:AVERAGE:0.5:60:744"]
        print statdata.data_sources, statdata.interval
        args.extend(self._getDataSourcesRRDList(statdata.data_sources, statdata.interval))
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

    def getVioletChartData(self):
        return (rrdtool.xport('--maxrows', '40',
                                                 '--start', 'now-1h', '--end', 'now',
                                                 '--step', 'now-1h', "DEF:a={0}:{1}:AVERAGE".format(self.rrd, 'input_queue_size'),
                                                 '--json',
                                                 'XPORT:a:Amount of messages in input queue (backlog)' ),
                rrdtool.xport('--maxrows', '40',
                                           '--start', 'now-1h', '--end', 'now',
                                           '--step', '900',
                                           "DEF:a={0}:{1}:AVERAGE".format(self.rrd, 'throughput'),
                                           '--json',
                                           'XPORT:a:Throughput of processing messages, per 1 minute' ))
    def getCommonChartData(self, hours = 6, grades = 10):
        common_stats = dict()
        common_stats['ds'] = dict()
        common_stats['meta'] = dict()
        stepToGet = 3600 * hours / grades
        #print "get {0}/{1}".format(rowsToGet, stepToGet)
        raw_stats = [ rrdtool.xport('--maxrows', str(grades),
                                    '--start', 'now-{}h'.format(hours),
                                    '--end', 'now',
                                    '--step', str(stepToGet),
                                    "DEF:a={0}:{1}:AVERAGE".format(self.rrd, param),
                                    'XPORT:a:{}'.format(param)) \
                                    for param in self.commonParamsToMonitor]
        for elem in raw_stats:
            legend = elem['meta']['legend'][0]
            #{meta: 'description', value: 1 },
            tmp = map(self.prepareValue, elem['data'][1:-1]) # excluding first and last ones
            common_stats['ds'][legend] = map(lambda x: {'meta':legend,'value':x}, tmp)
        rows = raw_stats[0]['meta']['rows']
        start = raw_stats[0]['meta']['start']
        step = raw_stats[0]['meta']['step']
        #print "got {0}/{1}".format(rows, step)
        common_stats['meta']['labels'] = [(dt.datetime.fromtimestamp(start)\
                                     + dt.timedelta(seconds = step * val))\
                                     .strftime("%H:%M")\
                                     for val in range(1, rows-1) ] # first and last ones
        return common_stats

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
        return [ 'DS:{0}:GAUGE:{1}:0:100000'.format(ds, interval) for ds in dataSources ]

    def _getDataSourcesString(self, dataSources):
        return str(":".join(dataSources))

    def _getDataValuesString(self, params, useStatDate = False):
        try:
            stime = str(int(time.mktime(dt.datetime.strptime(params.last_update_time, "%H:%M:%S:%d:%m:%Y").timetuple())))
        except:
            stime = 'N' # now
        values = [ str(int(params.__dict__[ds]))
                  for ds in params.data_sources ]
        return "{0}:{1}".format(stime, ":".join(values))
