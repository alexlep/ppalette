#from flask.ext.sqlalchemy import SQLAlchemy
#from wtforms.fields import PasswordField
from flask.ext.bcrypt import Bcrypt
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql.functions import now
from sqlalchemy.orm import relationship
from database import Base

bcrypt = Bcrypt()
#db = SQLAlchemy()

#class Host(Model):
class Host(Base):
    __tablename__ = 'hosts'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(100))
    ipaddress = Column(String(100))
    login = Column(String(80), unique=True)
    #email = Column(String(120))
    #password = Column(String(120))
    #is_admin = Column(Boolean(False))
    #is_locked = Column(Boolean(False))

    """def set_password(self, password):
            self.password = bcrypt.generate_password_hash(password)
            return True

    def check_password(self, password_entered):
            try:
                    result = bcrypt.check_password_hash(self.password, password_entered)
            except ValueError:
                    result = False
            return result

    def is_authenticated(self):
            return True
    def is_active(self):
            return True
    def is_anonymous(self):
            return False
    def get_id(self):
            return self.id"""
    def __unicode__(self):
            return self.hostname

#class Subnet(Model):
class Subnet(Base):
    __tablename__ = 'subnet'
    id = Column(Integer, primary_key=True)
    subnet = Column(String(100))
    netmask = Column(String(100))
    subnetdesc = Column(String(100))

#class Plugin(Model):
class Plugin(Base):
    __tablename__ = 'plugins'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(String(100))

    def __unicode__(self):
        return self.name
        #subnetdesc = Column(String(100))

#class Schedule(Model):
class Schedule(Base):
    __tablename__ = 'schedule'
    id = Column(Integer, primary_key=True)
    desc = Column(String(100))
    date_created = Column(DateTime, default=now())
    date_modified = Column(DateTime, default=now())
    date_last_started = Column(DateTime, default=now())
    enabled = Column(Boolean(True))
    interval = Column(Integer)
    #user_id = Column(Integer(), ForeignKey(User.id))
    #user = relationship(User, backref='posts')
    host_id = Column(Integer(), ForeignKey(Host.id))
    host = relationship(Host, backref='schedule')
    plugin_id = Column(Integer(), ForeignKey(Plugin.id))
    plugins = relationship(Plugin, backref='schedule')

    def __unicode__(self):
        return '{0}_{1}s'.format(self.plugins.name, self.interval)
'''
art_arch_table = Table('arch_art_ids', Model.metadata,
        Column('arch_id', Integer, ForeignKey('archive_.id')),
        Column('art_id', Integer, ForeignKey('articles_.id'))
)
'''
