# -*- coding: utf-8 -*-
import datetime as dt
import time
import os.path
import rrdtool
from core.pvars import defTimeFormat, workingDir
from base import BaseMonitoring

rrdDataDir = workingDir + '/rrd_data'
statRRDFile = rrdDataDir + '/common_statistics.rrd'
VIOLET = 'violet'
COMMON = 'common'

class Monitor(BaseMonitoring):
    def __init__(self, violetID=None):
        super(Monitor, self).__init__()
        if violetID:
            self.rrd = "{0}/{1}.rrd".format(rrdDataDir, violetID)
            self.paramsToFetch = ['input_queue_size', 'throughput']
        else:
            self.rrd = statRRDFile
            self.paramsToFetch = ['checks_ok', 'checks_warn', 'checks_error',
                                    'checks_active']

    def insertValues(self, statdata):
        if not os.path.isfile(self.rrd):
            self._createFile(statdata)
        rrdtool.update(self.rrd, '-t', \
                       self._getDataSourcesString(statdata.data_sources), \
                       self._getDataValuesString(statdata, useStatDate = True))

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
                                    for param in self.paramsToFetch]
        for elem in raw_stats:
            legend = elem['meta']['legend'][0]
            #{meta: 'description', value: 1 },
            tmp = map(self._prepareValue, elem['data'][1:-1]) # excluding first and last ones
            stats['ds'][legend] = map(lambda x: {'meta':legend,'value':x}, tmp)
        rows = raw_stats[0]['meta']['rows']
        start = raw_stats[0]['meta']['start']
        step = raw_stats[0]['meta']['step']
        stats['meta']['labels'] = [ (dt.datetime.fromtimestamp(start)\
                                            + dt.timedelta(seconds=step*val))\
                                            .strftime("%H:%M")\
                                            for val in range(1, rows-1) ] # first and last ones
        return stats

    def getLatestUpdate(self):
        return rrdtool.lastupdate(self.rrd)

    def _createFile(self, statdata):
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
                                        defTimeFormat).\
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

    def _prepareValue(self, value):
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
