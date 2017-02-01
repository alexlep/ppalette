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
    paramsFull = paramsShort + ['host', 'subnet', 'plugins']
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(String(100))
    host = relationship('Host', back_populates='suite')
    subnet = relationship('Subnet', back_populates='suite')
    plugins = relationship('Plugin',
                           secondary=pluginsToSuites,
                           backref=backref('suitos', lazy='select'))
    def __init__(self, name, ipsDB=None, pluginsDB=None, subnetsDB=None):
        self.name = name
        if ipsDB:
            self.host = ipsDB
        if subnetsDB:
            self.subnet = subnetsDB
        if pluginsDB:
            self.plugins = pluginsDB

    def updateParams(self, ipsDB=None, pluginsDB=None, subnetsDB=None):
        if ipsDB:
            self.host = ipsDB
        if subnetsDB:
            self.subnet = subnetsDB
        if pluginsDB:
            self.plugins = pluginsDB

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

    def __init__(self, script=None, customname=None,
                 interval=None, params=None,
                 ssh_wrapper=None, suitesDB=None):
        self.script = script
        self.customname = customname
        self.params = params
        if ssh_wrapper:
            self.ssh_wrapper = ssh_wrapper
        if interval:
            self.interval = interval
        if suitesDB:
            self.suites = suitesDB

    def updateParams(self, script=None, interval=None, params=None,
                     ssh_wrapper=None, suitesDB=None):
        if script:
            self.script = script
        if interval:
            self.interval = interval
        if params:
            self.params = params
        if suitesDB:
            self.suites = suitesDB
        if ssh_wrapper:
            self.ssh_wrapper = ssh_wrapper

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

    def __init__(self, ip=None, suiteID=None, subnetID=None, hostname=None,
                 login=None):
        self.ipaddress = ip
        self.hostname = hostname
        self.suite_id = suiteID
        self.subnet_id = subnetID
        if login:
            self.login = login

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

    def updateParams(self, suiteID, subnetID, hostname, login, maintenance):
        if hostname:
            self.hostname = hostname
        if login:
            self.login = login
        if subnetID:
            self.subnet_id = subnetID
        if suiteID:
            if self.suite_id:
                self.stats[:] = list()
            self.suite_id = suiteID
        if maintenance:
            self.maintenanceON()
        else:
            self.maintenanceOFF()

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
        self.host_id = msg.hostid
        self.plugin_id = msg.pluginid
        self.check_run_time = msg.time
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

    def __init__(self, name=None, subnet=None, netmask=None, suiteID=None):
        self.name = name
        self.subnet = subnet
        self.netmask = netmask
        if suiteID:
            self.suite_id = suiteID

    def updateParams(self, name=None, subnet=None, netmask=None, suiteID=None):
        if name:
            self.name = name
        if subnet:
            self.subnet = subnet
        if netmask:
            self.netmask = netmask
        if suiteID:
            self.suite_id = suiteID

    def __unicode__(self):
        return self.name

    def APIGetDict(self, short=True):
        return self.SQLA2Dict(self.paramsShort if short else self.paramsFull)
