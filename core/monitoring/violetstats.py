# -*- coding: utf-8 -*-
import json
from core.tools import dateToStr

VIOLET = 'violet'

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
