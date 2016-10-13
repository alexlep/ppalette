# -*- coding: utf-8 -*-
import tools
import architect
#from flask_bcrypt import Bcrypt
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy import Column, Table, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql.functions import now
from sqlalchemy.orm import relationship, backref
from database import Base
from datetime import datetime

#bcrypt = Bcrypt()
pluginsToSuites = Table('pluginsToSuites',
    Base.metadata,
    Column('suites_id', Integer, ForeignKey('suite.id')),
    Column('plugin_id', Integer, ForeignKey('plugin.id'))
)

"""hosts = Table('hosts',
    Base.metadata,
    Column('hosts_id', Integer, ForeignKey('host.id')),
    Column('suites_id', Integer, ForeignKey('suite.id'))
)"""

class Suite(Base):
    __tablename__ = 'suite'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(String(100))
    host = relationship("Host", back_populates="suite")
    subnet = relationship("Subnet", back_populates="suite")
    plugins = relationship('Plugin', secondary=pluginsToSuites, backref=backref('suitos', lazy='dynamic'))

    def __unicode__(self):
        return self.name

class Plugin(Base):
    __tablename__ = 'plugin'
    id = Column(Integer, primary_key=True)
    pluginUUID = Column(String(36), unique=True)
    script = Column(String(100))
    customname = Column(String(100), unique=True)
    description = Column(String(100))
    params = Column(String(200))
    interval = Column(Integer, default=10)
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now())
    suites = relationship('Suite', secondary=pluginsToSuites, backref=backref('pluginos', lazy='dynamic'))

    def __unicode__(self):
        return self.customname

class Host(Base):
    __tablename__ = 'host'
    id = Column(Integer, primary_key=True)
    hostUUID = Column(String(36), unique=True)
    hostname = Column(String(100))
    ipaddress = Column(String(100))
    login = Column(String(80), unique=True)
    maintenance = Column(Boolean(False), default = False)
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now())
    suite_id = Column(Integer, ForeignKey('suite.id'))
    suite = relationship("Suite")
    subnet_id = Column(Integer, ForeignKey('subnet.id'))
    subnet = relationship("Subnet")
    stats = relationship("Status")

    def __unicode__(self):
        return self.hostname


class Status(Base):
    __tablename__ = 'status'
    id = Column(Integer, primary_key=True)
    statusid = Column(String(36), unique=True)
    interval = Column(Integer, default=10)
    host_id = Column(Integer(), ForeignKey(Host.id))
    host = relationship(Host, backref='status')
    plugin_id = Column(Integer(), ForeignKey(Plugin.id))
    plugin = relationship(Plugin, backref='status')
    last_check_run = Column(DateTime, default=datetime.fromtimestamp(0))
    last_status = Column(String(1000))
    last_exitcode = Column(Integer)

    def __unicode__(self):
        return self.plugin.customname

"""
class Schedule(Base):
    __tablename__ = 'schedule'
    id = Column(Integer, primary_key=True)
    taskid = Column(String(36), unique=True)
    desc = Column(String(100))
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now())
    enabled = Column(Boolean(True), default = True)
    interval = Column(Integer, default=10)
    #host_id = Column(Integer(), ForeignKey(Host.id))
    #host = relationship(Host, backref='schedule')
    #plugin_id = Column(Integer(), ForeignKey(Plugin.id))
    #plugin = relationship(Plugin, backref='schedule')
    last_check_run = Column(DateTime, default=datetime.fromtimestamp(0))
    last_status = Column(String(1000))
    last_exitcode = Column(Integer)

    def __unicode__(self):
        return self.plugin.customname
"""
#@architect.install('partition', type='range', subtype='date', constraint='day', column='check_run_time', db='mysql://test:test@localhost/palette?charset=utf8')
class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True)
    desc = Column(String(100))
    interval = Column(Integer)
    host_id = Column(Integer(), ForeignKey(Host.id)) #, ForeignKey(Host.id))
    host = relationship(Host, backref='history')
    plugin_id = Column(Integer(), ForeignKey(Plugin.id)) # ForeignKey(Plugin.id))
    plugin = relationship(Plugin, backref='history')
    check_run_time = Column(DateTime, default=datetime.fromtimestamp(0))
    check_status = Column(String(1000))
    check_exicode = Column(Integer)

    def __unicode__(self):
        return self.plugin.last_status

class Subnet(Base):
    __tablename__ = 'subnet'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    subnet = Column(String(100))
    netmask = Column(String(100))
    description = Column(String(100))
    host = relationship("Host", back_populates="subnet")
    #suite = relationship("Suite", back_populates="subnet")
    suite_id = Column(Integer, ForeignKey('suite.id'))
    suite = relationship("Suite")

    def __unicode__(self):
        return self.name
