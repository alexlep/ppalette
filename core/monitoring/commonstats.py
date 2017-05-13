# -*- coding: utf-8 -*-
import json
from core.models import Host, Status, Plugin, Suite
from core.database import db_session

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

    def __init__(self):
        for ds in self.data_sources:
            setattr(self, ds, None)

    def update(self):
        self.hosts_active = db_session.query(Host.id).\
                                    filter(Host.maintenance == False).count()
        self.hosts_all = db_session.query(Host.id).count()
        self.hosts_active_up = db_session.query(Host.id).\
                                join((Status, Host.stats)).\
                                join((Plugin, Status.plugin)).\
                                filter(Host.maintenance == False,
                                       Status.last_exitcode == 0,
                                       Plugin.script == 'check_ping').\
                                count()
        self.checks_active = db_session.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Host.maintenance == False).\
                                count()
        self.checks_all = db_session.query(Plugin.id).\
                                join((Suite, Plugin.suites)).\
                                join((Host, Suite.hosts)).\
                                count()
        self.checks_ok = db_session.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 0,
                                       Host.maintenance == False).\
                                count()
        self.checks_warn = db_session.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 1,
                                       Host.maintenance == False).\
                                count()
        self.checks_error = db_session.query(Status.id).\
                                join((Host, Status.host)).\
                                filter(Status.last_exitcode == 2,
                                       Host.maintenance == False).\
                                count()
        self.checks_incorrect = db_session.query(Status.id).\
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
