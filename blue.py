# -*- coding: utf-8 -*-
import sys
from flask import Flask
from flask_admin import Admin
from core.models import Host, Subnet, Plugin, History, Suite #bcrypt, Schedule
from core.database import init_db, db_session
from core.mq import MQ
from core import tools
from flask_admin.contrib import sqla, fileadmin
from sqlalchemy.sql.functions import now

blueConfig = './config/blue_config.json'

config = tools.parseConfig(blueConfig)
confQueue = tools.createClass(config.queue)
confLog = tools.createClass(config.log)
isMQ = confQueue.isMQ


if isMQ:
    MQ = MQ('s', confQueue) # init MQ
    mqOutChannel = MQ.initOutChannel()
    if (not mqOutChannel):
        print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
        sys.exit(1)

#log = tools.initLogging(confLog) # init logging

class SuiteView(sqla.ModelView):
    column_list = ('suite', 'description', 'hosts')
    #form_excluded_columns = ('taskid', 'date_created','date_modified', 'last_check_run', 'last_status', 'last_exitcode')
    """form_ajax_refs = {
        'hosts': {
            'fields': (Host.hostname,)
        }
    }"""

class HostView(sqla.ModelView):
    column_list = ('hostname', 'ipaddress',  'maintenance')
    form_excluded_columns = ('hostid', 'login', 'date_created', 'date_modified')
    #form_excluded_columns = ('taskid', 'date_created','date_modified', 'last_check_run', 'last_status', 'last_exitcode')
    def on_model_change(self, form, model, is_created):
        if is_created:
            model.hostid = tools.getUniqueID()
        else:
            model.date_modified = now()
        return model

class PluginView(sqla.ModelView):
    column_list = ('customname', 'suites', 'interval', 'date_created', 'date_modified', 'id')
    form_excluded_columns = ('pluginid', 'date_created','date_modified')
    """form_ajax_refs = {
        'suites': {
            'fields': (Suite.suite,)
        }
    }"""
    def on_model_change(self, form, model, is_created):
        if is_created:
            model.pluginid = tools.getUniqueID()
        else:
            model.date_modified = now()
        return model

    """def after_model_change(self, form, model, is_created):
        if isMQ:
            message = tools.prepareDict(converted = True,
                                    type='taskChange',
                                    option='active',
                                    taskid = model.taskid,
                                    value = model.enabled)
            print message
            try: # TODO: HANDLE!
                mqOutChannel.basic_publish(exchange='', routing_key=confQueue.outqueue, body=message)
            except:
                print "oops"
                pass
        #return model"""

class DashBoardView(sqla.ModelView):
    list_template = 'palist.html'
    can_create = False
    can_delete = False
    can_edit = False
    column_display_pk = False
    can_export = True
    column_list = ('host', 'host.ipaddress', 'plugin', 'last_check_run', 'last_status', 'last_exitcode')


arg = ''.join(sys.argv[1:]) or True
if arg == 'i':
    dbc = init_db(create_tables=True)
else:
    dbc = init_db(create_tables=False)

if not dbc:
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)

app = Flask (__name__)
app.secret_key="a92547e3847063649d9d732a183418bf"
app.config['DEBUG'] = True

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

#admin = Admin (app, name='blue', template_mode='bootstrap3', url='/', index_view=DashBoardView(Schedule, db_session, url='/', endpoint='admin', name='Dashboard'))
admin = Admin (app, name='blue', template_mode='bootstrap3') #, url='/', index_view=DashBoardView(Schedule, db_session, url='/', endpoint='admin', name='Dashboard'))
admin.add_view(PluginView(Plugin, db_session, name="Plugins", category="Checks"))
admin.add_view(SuiteView(Suite, db_session, name="Suites", category="Checks"))

admin.add_view(HostView(Host, db_session, name="Hosts", category="Targets"))
admin.add_view(sqla.ModelView(Subnet, db_session, name="Subnet", category="Targets"))
#admin.add_view(sqla.ModelView(subsets, db_session, name="Subsets"))
#admin.add_view(ScheduleView(Schedule, db_session, name="Scheduler"))
#admin.add_view(sqla.ModelView(Subnet, db_session, name="Subnets"))
#admin.add_view(sqla.ModelView(History, db_session, name="History"))

#db.init_app(app)
#bcrypt.init_app(app)

app.run(debug=True, host='0.0.0.0', threaded=True)
