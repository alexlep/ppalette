from flask import Flask
from flask_admin import Admin
from models import bcrypt, Host, Subnet, Plugin, Schedule
from database import db_session
from flask.ext.admin.contrib import sqla, fileadmin

app = Flask (__name__)
app.secret_key="a92547e3847063649d9d732a183418bf"

#app.config['DATABASE_FILE'] = 'sample_db.sqlite'
#app.config['SQLALCHEMY_ECHO'] = True
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']

class ScheduleView(sqla.ModelView):
	#can_create = False
	#can_delete = False
    column_list = ('plugin', 'host', 'interval', 'date_created', 'date_modified', 'desc', 'id')
    form_excluded_columns = ('date_created','date_modified', 'last_check_run', 'last_status', 'last_exitcode')

class DashBoardView(sqla.ModelView):
    can_create = False
    can_delete = False
    can_edit = False
    can_export = True
    column_list = ('host', 'plugin', 'last_check_run', 'last_status', 'last_exitcode')
    #form_excluded_columns = ('date_created','date_modified', 'last_check_run', 'last_status', 'last_exitcode')

admin = Admin (app, name='blue', template_mode='bootstrap3', url='/', index_view=DashBoardView(Schedule, db_session, url='/', endpoint='admin', name='Dashboard'))
admin.add_view(sqla.ModelView(Host, db_session, name="Hosts"))
admin.add_view(sqla.ModelView(Plugin, db_session, name="Plugins"))
admin.add_view(ScheduleView(Schedule, db_session, name="Scheduler"))
admin.add_view(sqla.ModelView(Subnet, db_session, name="Subnets"))


#db.init_app(app)
bcrypt.init_app(app)
