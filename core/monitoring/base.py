# -*- coding: utf-8 -*-
VIOLET = 'violet'
COMMON = 'common'

class BaseMonitoring(object):
    def insertValues(self, statdata, **kwargs):
        pass

    def fetch(self):
        pass

    def getLatestUpdate(self):
        pass

    def getChartData(self, hours=6, grades=10):
        pass
