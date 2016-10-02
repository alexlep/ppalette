# -*- coding: utf-8 -*-
import sys
from flask import Flask, abort
from core.tools import parseConfig, draftClass, initLogging
from core.scheduler import Scheduler
from flask_admin import Admin
from flask_admin.contrib import sqla, fileadmin
from core.models import Host, Subnet, Plugin, History, Suite, Status #bcrypt, Schedule
from core.database import init_db, db_session
from sqlalchemy.sql.functions import now

blueConfigFile = './config/blue_config.json'

if not init_db(create_tables=False):
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)

blueConfig = parseConfig(blueConfigFile)
#if blueConfig.webif_enabled:
#    from core.blueapi import BlueApp, db_session, init_db
#else:
#    from core.database import db_session, init_db
blueConfLog = draftClass(blueConfig.log)

#log = initLogging(blueConfLog) # init logging
redConfigFile = './config/red_config.json'
RedApp = Scheduler(redConfigFile)

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
        print "ololo"
        if is_created:
            model.pluginUUID = tools.getUniqueID()
        else:
            model.date_modified = now()
        return model

    def after_model_change(self, form, model, is_created):
        RedApp.fillSchedule()
        return model

class DashBoardView(sqla.ModelView):
    page_size = 50
    list_template = 'status_list.html'
    can_create = False
    can_delete = False
    can_edit = False
    column_display_pk = False
    can_export = True
    column_list = ('host', 'host.ipaddress', 'plugin', 'interval', 'last_check_run', 'last_status', 'last_exitcode')
    column_searchable_list = ('host.hostname',)
    column_default_sort = ('host.hostname')
    #column_sortable_list = ('host.hostname',)

webif = Admin (name='blue', template_mode='bootstrap3', url='/', index_view=DashBoardView(Status, db_session, url='/', endpoint='admin', name='Dashboard'))
webif.add_view(PluginView(Plugin, db_session, name="Plugins")) #, category="Checks"))
webif.add_view(SuiteView(Suite, db_session, name="Suites")) #, category="Checks"))
webif.add_view(HostView(Host, db_session, name="Hosts")) #, category="Targets"))
webif.add_view(sqla.ModelView(Subnet, db_session, name="Subnet")) #, category="Targets"))


BlueApp = Flask (__name__)
BlueApp.secret_key="a92547e3847063649d9d732a183418bf"
#BlueApp.config['DEBUG'] = True

@BlueApp.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

if blueConfig.webif_enabled:
    webif.init_app(BlueApp)

@BlueApp.route('/api/job/discovery/<subnetid>', methods=['GET'])
def discoveryInitiator(subnetid):
    #try:
    RedApp.sendDiscoveryRequest(int(subnetid))
    #except:
    #    abort(500)
    return '200'

"""
@blueapp.route('/api/job/add/<id_>', methods=['GET','POST'])
def add_job(id_):
    try:
        ss.addJobFromDB(int(id_))
    except:
        abort(500)
    return 'Hello, World!'

@blueapp.route('/api/job/remove/<id_>', methods=['GET','POST'])
def remove_job(id_):
    if id_ == 'all':
        ss.remove_all_jobs()
    return 'removed'

@blueapp.route('/api/job/get/<id_>', methods=['GET','POST'])
def get_job(id_):
    if id_ == 'all':
        ss.get_jobs()
    else:
        try:
            ss.get_job(int(id_))
        except:
            abort(500)
    return '200'

@blueapp.route('/api/job/pause/<id_>', methods=['GET','POST'])
def pause_job(id_):
    if id_ == 'all':
        ss.pause()
    else:
        try:
            ss.pause_job(id_)
        except:
            abort(500)
    return '200'

@blueapp.route('/api/job/resume/<id_>', methods=['GET','POST'])
def resume_job(id_):
    if id_ == 'all':
        ss.resume()
    else:
        try:
            ss.resume_job(id_)
        except:
            abort(500)
    return '200'

@blueapp.route('/api/schedule/reload', methods=['GET','POST'])
def reloadJobs():
    try:
        ss.fillSchedule()
    except:
        abort(500)
    return '200'
"""









#bcrypt.init_app(app)


#BlueApp.run(debug=True, host='0.0.0.0', threaded=True)
