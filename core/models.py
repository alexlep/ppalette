import tools
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

    def __unicode__(self):
            return "{0} ({1})".format(self.hostname, self.ipaddress)

class Subnet(Base):
    __tablename__ = 'subnet'
    id = Column(Integer, primary_key=True)
    subnet = Column(String(100))
    netmask = Column(String(100))
    subnetdesc = Column(String(100))

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
    taskid = Column(String(36), default=tools.getUniqueID())
    desc = Column(String(100))
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now())
    enabled = Column(Boolean(True))
    interval = Column(Integer)
    host_id = Column(Integer(), ForeignKey(Host.id))
    host = relationship(Host, backref='schedule')
    plugin_id = Column(Integer(), ForeignKey(Plugin.id))
    plugin = relationship(Plugin, backref='schedule')
    last_check_run = Column(DateTime, default=datetime.fromtimestamp(0))
    last_status = Column(String(1000))
    last_exitcode = Column(Integer)

    def __unicode__(self):
        return self.plugin.customname
