from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
#from flask.ext.sqlalchemy import SQLAlchemy

engine = create_engine('mysql://test:test@localhost/palette', convert_unicode=True) #, echo=True) #('sqlite:///sample_db.sqlite')
#
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import models
    #Base.metadata.drop_all(bind=engine)
    try:
        Base.metadata.create_all(bind=engine)
        connected = True
    except OperationalError:
        connected = None
    return connected
