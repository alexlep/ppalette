# -*- coding: utf-8 -*-
from datetime import datetime
import time
import os.path
import rrdtool
'''
violet_id = 34512
file_name = 'violet_stats_id{}.rrd'.format(violet_id)
step = 60
start_time = int(time.time()) - step*1440
var = 'incoming_messages'

rrdtool.create(
    file_name,
    "--start", "{}".format(start_time),
     "--step", "{}".format(step),
    "RRA:AVERAGE:0.5:1:1440",
    "RRA:AVERAGE:0.5:60:744",
    "DS:incoming_messages:GAUGE:60:0:100000")
#     "--step", "{}".format(step),

# feed updates to the database
for i in range(1, 1441):
    aa = "{0}:{1}".format(start_time + step*i, random.randint(600,12000))
    print aa
    rrdtool.update(file_name, '-t', 'incoming_messages', aa)
result = rrdtool.fetch(file_name, "AVERAGE")
print result[2]
print start_time
aa = rrdtool.info(file_name)
for key in aa.keys():
    print key, aa[key]


oo = rrdtool.xport('--maxrows', '1440', '--step', '60', "DEF:a={0}:{1}:AVERAGE".format(file_name, var), '--json', 'XPORT:a:Amount of Incoming Messages, per 60s' )
print oo'''
#print help(rrdtool.update)
#def createRRDArchive(filename, step_seconds, ):


class RRD(object):
    def __init__(self, filename):
        self.rrd = filename

    def createFile(self, statdata):
        start_time = int(time.mktime(datetime.strptime(statdata.last_update_time, "%H:%M:%S:%d:%m:%Y").timetuple())) - statdata.interval
        args = [self.rrd,
                "--start", str(start_time),
                '--step', str(statdata.interval),
                "RRA:AVERAGE:0.5:1:1440", "RRA:AVERAGE:0.5:60:744"]
        args.extend(statdata.getRRDDataSourcesList())
        rrdtool.create(*args)

    def insertValues(self, statdata):
        if not os.path.isfile(self.rrd):
            self.createFile(statdata)
        rrdtool.update(self.rrd, '-t', statdata.getDataSourcesString(), statdata.getDataValuesString())

    def fetch(self):
        return rrdtool.fetch(self.rrd,'-r','60', "AVERAGE")

    def getLatestUpdate(self):
        return rrdtool.lastupdate(self.rrd)

    def getChartData(self):
        data = dict()
        monitoring_params = ['input_queue_size', 'throughput']
        #    input_queue_size = int() , throughput = int()
        data['input_queue_size'] = rrdtool.xport('--maxrows', '60',
                                                 '--start', 'now-1h', '--end', 'now',
                                                 '--step', '60', "DEF:a={0}:{1}:AVERAGE".format(self.rrd, 'input_queue_size'),
                                                 '--json',
                                                 'XPORT:a:Amount of messages in input queue (backlog)' )
        data['throughput'] = rrdtool.xport('--maxrows', '60',
                                           '--start', 'now-1h', '--end', 'now',
                                           '--step', '60',
                                           "DEF:a={0}:{1}:AVERAGE".format(self.rrd, 'throughput'),
                                           '--json',
                                           'XPORT:a:Throughput of processing messages, per 1 minute' )
        return data
