# -*- coding: utf-8 -*-
import tools
import architect
#from flask_bcrypt import Bcrypt
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy import Column, Table, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql.functions import now
from sqlalchemy.orm import collections
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import DeclarativeMeta
from database import Base
from datetime import datetime

#bcrypt = Bcrypt()
pluginsToSuites = Table('pluginsToSuites',
    Base.metadata,
    Column('suites_id', Integer, ForeignKey('suite.id')),
    Column('plugin_id', Integer, ForeignKey('plugin.id'))
)
class RedBase(Base):
    __abstract__ = True
    def SQLA2Dict(self, params):
        res = dict()
        for param in params:
            value = getattr(self, param)
            if value.__class__.__name__ == 'InstrumentedList':
                res[param] = list()
                for elem in value:
                    res[param].append(elem.APIGetDict())
            elif isinstance(type(value), DeclarativeMeta):
                res[param] = value.APIGetDict()
            else:
                res[param] = value
        return res

class Suite(RedBase):
    __tablename__ = 'suite'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(String(100))
    host = relationship("Host", back_populates="suite")
    subnet = relationship("Subnet", back_populates="suite")
    plugins = relationship('Plugin',
                           secondary=pluginsToSuites,
                           backref=backref('suitos', lazy='dynamic'))

    def __unicode__(self):
        return self.name

    def APIGetDict(self, short = True):
        params = ['id', 'name']
        if not short:
            params.extend(['host', 'subnet', 'plugins'])
        return self.SQLA2Dict(params)

class Plugin(RedBase):
    __tablename__ = 'plugin'
    id = Column(Integer, primary_key=True)
    pluginUUID = Column(String(36), unique=True)
    script = Column(String(100))
    customname = Column(String(100), unique=True)
    description = Column(String(100))
    params = Column(String(200))
    interval = Column(Integer, default=30)
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now()) # onupdate=db.func.now()
    ssh_wrapper = Column(Boolean(), default = False)
    suites = relationship('Suite',
                          secondary=pluginsToSuites,
                          backref=backref('pluginos', lazy='dynamic'))

    def __unicode__(self):
        return self.customname

    def APIGetDict(self, short=True):
        params = ['id', 'script','customname', 'interval']
        if not short:
            params.extend(['suites', 'description', 'ssh_wrapper'])
        return self.SQLA2Dict(params)

class Host(RedBase):
    __tablename__ = 'host'
    id = Column(Integer, primary_key=True)
    hostUUID = Column(String(36), unique=True, default=tools.getUniqueID)
    hostname = Column(String(100))
    ipaddress = Column(String(100), unique=True)
    login = Column(String(80), default='violet')
    maintenance = Column(Boolean(), default=True)
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now())
    suite_id = Column(Integer, ForeignKey('suite.id'))
    suite = relationship("Suite")
    subnet_id = Column(Integer, ForeignKey('subnet.id'))
    subnet = relationship("Subnet")
    stats = relationship("Status")

    def __unicode__(self):
        return self.hostname

    def maintenanceON(self):
        if self.maintenance:
            res = False
        else:
            self.maintenance = res = True
        return res

    def maintenanceOFF(self):
        if self.maintenance:
            self.maintenance = False
            res = True
        else:
            res = False
        return res

    def listScheduleItems(self):
        return map(lambda plugUUID: self.hostUUID + plugUUID,
                   [plug.pluginUUID for plug in self.suite.plugins])

    def APIGetDict(self, short=True, exitcode = None):
        params = ['id', 'hostname','ipaddress','maintenance']
        if not short:
            params.extend(['stats', 'subnet', 'suite'])
        return self.SQLA2Dict(params)

class Status(RedBase):
    __tablename__ = 'status'
    id = Column(Integer, primary_key=True)
    statusid = Column(String(36), unique=True)
    interval = Column(Integer, default=10)
    host_id = Column(Integer(), ForeignKey(Host.id))
    host = relationship(Host, backref='status')
    plugin_id = Column(Integer(), ForeignKey(Plugin.id))
    plugin = relationship(Plugin, backref='status')
    scheduled_check_time = Column(DateTime, default=datetime.fromtimestamp(0))
    last_check_run = Column(DateTime, default=datetime.fromtimestamp(0))
    last_status = Column(String(1000))
    last_exitcode = Column(Integer)

    def __unicode__(self):
        return self.plugin.customname

    def APIGetDict(self):
        params = ['plugin','interval',
                  'last_check_run','last_status',
                  'last_exitcode']
        return self.SQLA2Dict(params)

class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True)
    desc = Column(String(100))
    details = Column(String(200))
    interval = Column(Integer)
    host_id = Column(Integer(), ForeignKey(Host.id))
    host = relationship(Host, backref='history')
    plugin_id = Column(Integer(), ForeignKey(Plugin.id))
    plugin = relationship(Plugin, backref='history')
    check_run_time = Column(DateTime, default=datetime.fromtimestamp(0))
    check_status = Column(String(1000))
    check_exitcode = Column(Integer)

    def __unicode__(self):
        return self.check_status

    def __init__(self, msg):
        self.host_id = msg.hostid
        self.plugin_id = msg.pluginid
        self.check_run_time = msg.time
        self.check_status = msg.output
        self.check_exitcode = msg.exitcode
        self.interval = msg.interval
        self.details = msg.details

class Subnet(RedBase):
    __tablename__ = 'subnet'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    subnet = Column(String(100))
    netmask = Column(String(100))
    description = Column(String(100))
    host = relationship("Host", back_populates="subnet")
    suite_id = Column(Integer, ForeignKey('suite.id'))
    suite = relationship("Suite")

    def __unicode__(self):
        return self.name

    def APIGetDict(self, short = True):
        params = ['id', 'name']
        if not short:
            params.extend(['subnet', 'netmask', 'description','host','suite'])
        return self.SQLA2Dict(params)
