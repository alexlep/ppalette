# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool, StaticPool

# SQLite, for tests

url = 'sqlite:///ppalette.sqlite'
engine = create_engine(url,
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool)
# MySQL
'''
url = 'mysql://test:test@localhost/palette?use_unicode=1&charset=utf8'
engine = create_engine(url, pool_recycle=3600, pool_size=20, max_overflow=0,
                       poolclass=QueuePool,
                       isolation_level="READ UNCOMMITTED")
'''
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=True,
                                         bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db(create_tables = False):
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
