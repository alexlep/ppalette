from flask_admin import Admin
from flask_admin.contrib import sqla, fileadmin
from core.models import Host, Subnet, Plugin, History, Suite, Status #bcrypt, Schedule
from core.database import init_db, db_session

from scheduler import Scheduler


arg = ''.join(sys.argv[1:]) or True
if arg == 'i':
    dbc = init_db(create_tables=True)
else:
    dbc = init_db(create_tables=False)

if not dbc:
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)
