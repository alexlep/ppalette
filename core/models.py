# -*- coding: utf-8 -*-
import tools
import architect
#from flask_bcrypt import Bcrypt
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql.functions import now
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

#bcrypt = Bcrypt()

class Host(Base):
    __tablename__ = 'hosts'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(100))
    ipaddress = Column(String(100))
    login = Column(String(80), unique=True)
    maintenance = Column(Boolean(False), default = False)

    def __unicode__(self):
        return self.hostname

class Subnet(Base):
    __tablename__ = 'subnet'
    id = Column(Integer, primary_key=True)
    subnet = Column(String(100))
    netmask = Column(String(100))
    subnetdesc = Column(String(100))

    def __unicode__(self):
        return self.subnet

class Plugin(Base):
    __tablename__ = 'plugins'
    id = Column(Integer, primary_key=True)
    check = Column(String(100))
    customname = Column(String(100))
    description = Column(String(100))
    params = Column(String(200))

    def __unicode__(self):
        return self.customname

class Schedule(Base):
    __tablename__ = 'schedule'
    id = Column(Integer, primary_key=True)
    taskid = Column(String(36), unique=True)
    desc = Column(String(100))
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now())
    enabled = Column(Boolean(True), default = True)
    interval = Column(Integer, default=10)
    host_id = Column(Integer(), ForeignKey(Host.id))
    host = relationship(Host, backref='schedule')
    plugin_id = Column(Integer(), ForeignKey(Plugin.id))
    plugin = relationship(Plugin, backref='schedule')
    last_check_run = Column(DateTime, default=datetime.fromtimestamp(0))
    last_status = Column(String(1000))
    last_exitcode = Column(Integer)

    def __unicode__(self):
        return self.plugin.customname

@architect.install('partition', type='range', subtype='date', constraint='day', column='check_run_time', db='mysql://test:test@localhost/palette?charset=utf8')
class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True)
    desc = Column(String(100))
    interval = Column(Integer)
    host_id = Column(Integer()) #, ForeignKey(Host.id))
    #host = relationship(Host, backref='history')
    plugin_id = Column(Integer()) # ForeignKey(Plugin.id))
    #plugin = relationship(Plugin, backref='history')
    check_run_time = Column(DateTime, default=datetime.fromtimestamp(0))
    check_status = Column(String(1000))
    check_exicode = Column(Integer)

    def __unicode__(self):
        return self.plugin.last_status
