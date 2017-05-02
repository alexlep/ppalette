# -*- coding: utf-8 -*-
from influxdb import InfluxDBClient
from influxdb import SeriesHelper

from core.pvars import defTimeFormat, workingDir
from base import BaseMonitoring, CommonStats, Stats

host = 'localhost'
port = 8086
user = 'ppalette'
password = 'ppalette'
dbname = 'ppalette'

VIOLET = 'violet'
COMMON = 'common'

SN_TEMPLATE = "ppalette.stats."
VIOLET_SN = SN_TEMPLATE + VIOLET
COMMON_SN = SN_TEMPLATE + COMMON

def prepareCli():
    return InfluxDBClient(host, port, user, password, dbname)

class VioletSeries(SeriesHelper):
    class Meta:
        client = prepareCli()
        # separate measurement for each violet instance
        #series_name = 'ppalette.stats.{violet_instance}'
        series_name = VIOLET_SN
        fields = Stats.data_sources
        tags = ['violetID']
        autocommit = True

class CommonSeries(SeriesHelper):
    class Meta:
        client = prepareCli()
        series_name = COMMON_SN
        fields = CommonStats.data_sources
        tags = ['ctype']
        autocommit = True

class Monitor(BaseMonitoring):
    def __init__(self, violetID=None):
        super(Monitor, self).__init__()
        self.violetID = violetID
        if violetID:
            self.paramsToFetch = ['input_queue_size', 'throughput']
        else:
            self.paramsToFetch = ['checks_ok', 'checks_warn', 'checks_error',
                                    'checks_active']

    def insertValues(self, statdata):
        if self.violetID:
            VioletSeries(violetID=self.violetID,
                         **statdata.getStatDict())
        else:
            CommonSeries(ctype=COMMON,
                         **statdata.getStatDict())

    def getChartData(self, hours=6, grades=10):
        client = prepareCli()
        if self.violetID:
            req = "SELECT {0} FROM \"{1}\" WHERE time > now() - {2}h "\
                  "AND violetID='{3}'".format(','.join(self.paramsToFetch),
                                               VIOLET_SN,
                                               hours,
                                               self.violetID)
            rs = client.query(req)
            res = dict(res=list(rs.get_points()))
        else:
            req = "SELECT {0} FROM \"{1}\" WHERE time > now() - {2}h".\
                  format(','.join(self.paramsToFetch),
                         COMMON_SN,
                         hours)
            rs = client.query(req)
            res = dict(res=list(rs.get_points()))
        return res

    def getLatestUpdate(self):
        client = prepareCli()
        if self.violetID:
            req = "SELECT {0} FROM \"{1}\" WHERE violetID='{2}' LIMIT 1".\
                  format(','.join(self.paramsToFetch),
                         VIOLET_SN,
                         self.violetID)
            rs = client.query(req)
            res = dict(res=list(rs.get_points()))
        else:
            req = "SELECT {0} FROM \"{1}\" LIMIT 1".\
                  format(','.join(self.paramsToFetch),
                         COMMON_SN)
            rs = client.query(req)
            res = dict(res=list(rs.get_points()))
        return res
