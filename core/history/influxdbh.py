# -*- coding: utf-8 -*-
from influxdb import InfluxDBClient
from influxdb import SeriesHelper

from core.tools import Message

host = 'localhost'
port = 8086
user = 'ppalette'
password = 'ppalette'
dbname = 'ppalette'

def prepareCli():
    return InfluxDBClient(host, port, user, password, dbname)

class HistorySeries(SeriesHelper):
    class Meta:
        client = prepareCli()
        # separate measurement for each violet instance
        series_name = 'ppalette.history.{plugin_id}'
        fields = Message.history_keys
        tags = ['plugin_id', 'host_id']
        autocommit = True

class BaseHistory(object):
    def insertValues(self, statdata, **kwargs):
        pass

    def getLatestUpdate(self):
        pass

    def getValues(self, host, customname, hours=6):
        pass


class History(BaseHistory):
    def __init__(self):
        super(History, self).__init__()

    def insertValues(self, msg):
        HistorySeries(plugin_id=msg.plugin_id,
                      host_id=msg.host_id,
                      **msg.getHistoryDict())

    def getValues(self, hostID, pluginID):
        client = prepareCli()
        req = "SELECT {0} FROM \"{1}\" WHERE time > now() - {2}h".\
              format(','.join(Message.history_keys),
                     'ppalette.history.' + str(pluginID),
                     hostID)
        rs = client.query(req)
        client._session.close()
        return dict(res=list(rs.get_points()))
