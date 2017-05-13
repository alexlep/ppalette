# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# SQLite, for tests
'''
from sqlalchemy.pool import StaticPool
url = 'sqlite:///ppalette.sqlite'
engine = create_engine(url,
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool)
# MySQL
'''
from sqlalchemy.pool import QueuePool

MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
DBUSER = 'test'
DBPASSWORD = 'test'

URL = 'mysql://{0}:{1}@{2}/ppalette?use_unicode=1&charset=utf8'.\
      format(DBUSER, DBPASSWORD, MYSQL_HOST)

engine = create_engine(URL, poolclass=QueuePool,
                       connect_args=dict(host=MYSQL_HOST, port=MYSQL_PORT),
                       pool_recycle=3600, pool_size=20, max_overflow=0,
                       isolation_level="READ UNCOMMITTED")

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

def clearDBConnection(func):
    def func_wrapper(*args, **kwargs):
        data = func(*args, **kwargs)
        db_session.remove()
        return data
    return func_wrapper
