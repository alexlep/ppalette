# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# SQLite, for tests

from sqlalchemy.pool import StaticPool
url = 'sqlite:///ppalette.sqlite'
engine = create_engine(url,
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool)
# MySQL
'''
from sqlalchemy.pool import QueuePool

mysql_host = '127.0.0.1'
mysql_port = 3306
url = 'mysql://test:test@{}/palette?use_unicode=1&charset=utf8'.\
      format(mysql_host)
engine = create_engine(url, poolclass=QueuePool,
                       connect_args=dict(host=mysql_host, port=mysql_port),
                       pool_recycle=3600, pool_size=20, max_overflow=0,
                       isolation_level="READ UNCOMMITTED")
'''
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=True,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db(create_tables=False):
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import models
    if create_tables:
        Base.metadata.drop_all(bind=engine)
    try:
        Base.metadata.create_all(bind=engine)
        connected = True
    except Exception as e:
        print e
        connected = None
    return connected
