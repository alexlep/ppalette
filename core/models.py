# -*- coding: utf-8 -*-
import tools
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy import Column, Table, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql.functions import now
from sqlalchemy.orm import collections
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import DeclarativeMeta
from database import Base
from datetime import datetime

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
    paramsShort = ['id', 'name']
    paramsFull = paramsShort + ['hosts', 'subnets', 'plugins']
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(String(100))
    hosts = relationship('Host', back_populates='suite')
    subnets = relationship('Subnet', back_populates='suite')
    plugins = relationship('Plugin',
                           secondary=pluginsToSuites,
                           backref=backref('suitos', lazy='select'))
    def __init__(self, name, **kwargs):
        self.name = name
        for argsItem, argsValue in kwargs.items():
            if argsValue is not None:
                setattr(self, argsItem, argsValue)

    def updateParams(self, **kwargs):
        for argsItem, argsValue in kwargs.items():
            if argsValue is not None:
                setattr(self, argsItem, argsValue)

    def __unicode__(self):
        return self.name

    def APIGetDict(self, short=True):
        return self.SQLA2Dict(self.paramsShort if short else self.paramsFull)

class Plugin(RedBase):
    __tablename__ = 'plugin'
    paramsShort = ['id', 'script','customname', 'interval']
    paramsFull = paramsShort + ['suites', 'description', 'ssh_wrapper',
                                'params']
    id = Column(Integer, primary_key=True)
    pluginUUID = Column(String(36), unique=True, default=tools.getUniqueID)
    script = Column(String(100))
    customname = Column(String(100), unique=True)
    description = Column(String(100))
    params = Column(String(200))
    interval = Column(Integer, default=30)
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now(), onupdate=now())
    ssh_wrapper = Column(Boolean(), default = False)
    suites = relationship('Suite',
                          secondary=pluginsToSuites,
                          backref=backref('pluginos', lazy='select'))
    stats = relationship('Status', cascade='all, delete-orphan')

    def __init__(self, script, customname, **kwargs):
        self.script = script
        self.customname = customname
        for argsItem, argsValue in kwargs.items():
            if argsValue is not None:
                setattr(self, argsItem, argsValue)

    def updateParams(self, **kwargs):
        for argsItem, argsValue in kwargs.items():
            if argsValue is not None:
                setattr(self, argsItem, argsValue)

    def __unicode__(self):
        return self.customname

    def APIGetDict(self, short=True):
        return self.SQLA2Dict(self.paramsShort if short else self.paramsFull)

class Host(RedBase):
    __tablename__ = 'host'
    paramsShort = ['id', 'hostname','ipaddress','maintenance']
    paramsFull = paramsShort + ['stats', 'subnet', 'suite', 'login']
    id = Column(Integer, primary_key=True)
    hostUUID = Column(String(36), unique=True, default=tools.getUniqueID)
    hostname = Column(String(100))
    ipaddress = Column(String(100), unique=True)
    login = Column(String(80), default='violet')
    maintenance = Column(Boolean(), default=True)
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now(), onupdate=now())
    suite_id = Column(Integer, ForeignKey('suite.id'))
    suite = relationship('Suite', lazy='select')
    subnet_id = Column(Integer, ForeignKey('subnet.id'))
    subnet = relationship('Subnet', lazy='select')
    stats = relationship('Status', cascade='all, delete-orphan')
    enablehistory = Column(Boolean, default=False)

    def __init__(self, ip, **kwargs):
        self.ipaddress = ip
        for argsItem, argsValue in kwargs.items():
            if argsValue is not None:
                setattr(self, argsItem, argsValue)

    def updateParams(self, **kwargs):
        for argsItem, argsValue in kwargs.items():
            if argsValue is not None:
                setattr(self, argsItem, argsValue)

    def __unicode__(self):
        return self.hostname

    def APIGetDict(self, short=True):
        return self.SQLA2Dict(self.paramsShort if short else self.paramsFull)

class Status(RedBase):
    __tablename__ = 'status'
    paramsShort = ['plugin','interval', 'last_check_run','last_status',
              'last_exitcode']
    paramsFull = paramsShort
    id = Column(Integer, primary_key=True)
    statusid = Column(String(36), unique=True, default=tools.getUniqueID)
    interval = Column(Integer, default=30)
    host_id = Column(Integer(), ForeignKey(Host.id))
    host = relationship(Host, backref='status')
    plugin_id = Column(Integer(), ForeignKey(Plugin.id))
    plugin = relationship(Plugin, backref='status')
    scheduled_check_time = Column(DateTime, default=datetime.fromtimestamp(0))
    last_check_run = Column(DateTime, default=datetime.fromtimestamp(0))
    last_status = Column(String(1000))
    last_exitcode = Column(Integer)

    def __init__(self, msg):
        self.plugin_id = msg.plugin_id
        self.host_id = msg.host_id
        self.last_status = msg.output
        self.last_exitcode = msg.exitcode
        self.scheduled_check_time = msg.scheduled_time
        self.last_check_run = msg.exec_time
        self.interval = msg.interval

    def update(self, msg):
        self.last_status = msg.output
        self.last_exitcode = msg.exitcode
        self.scheduled_check_time = msg.scheduled_time
        self.last_check_run = msg.exec_time
        self.interval = msg.interval

    def __unicode__(self):
        return self.plugin.customname

    def APIGetDict(self):
        return self.SQLA2Dict(self.paramsShort)

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
        self.host_id = msg.host_id
        self.plugin_id = msg.plugin_id
        self.check_run_time = msg.exec_time
        self.check_status = msg.output
        self.check_exitcode = msg.exitcode
        self.interval = msg.interval
        self.details = msg.details

class Subnet(RedBase):
    __tablename__ = 'subnet'
    paramsShort = ['id', 'name']
    paramsFull = paramsShort + ['subnet', 'netmask', 'description','host',
                                'suite']
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    subnet = Column(String(100))
    netmask = Column(String(100))
    description = Column(String(100))
    host = relationship('Host', back_populates='subnet')
    suite_id = Column(Integer, ForeignKey('suite.id'))
    suite = relationship('Suite')

    def __init__(self, name, subnet, netmask, **kwargs):
        self.name = name
        self.subnet = subnet
        self.netmask = netmask
        for argsItem, argsValue in kwargs.items():
            if argsValue is not None:
                setattr(self, argsItem, argsValue)

    def updateParams(self, **kwargs):
        for argsItem, argsValue in kwargs.items():
            if argsValue is not None:
                setattr(self, argsItem, argsValue)

    def __unicode__(self):
        return self.name

    def APIGetDict(self, short=True):
        return self.SQLA2Dict(self.paramsShort if short else self.paramsFull)
