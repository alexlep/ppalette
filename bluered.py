# -*- coding: utf-8 -*-
import sys
from flask import Flask, abort, flash
from core.tools import parseConfig, draftClass, initLogging, getUniqueID
from core.red_scheduler import Scheduler
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib import sqla
from flask_admin.babel import ngettext
from core.models import Host, Subnet, Plugin, History, Suite, Status #bcrypt, Schedule
from core.database import url, init_db, db_session
from sqlalchemy.sql.functions import now
from wtforms import Form, BooleanField, TextField, PasswordField, validators
from flask_admin.actions import action


blueConfigFile = './config/blue_config.json'
redConfigFile = './config/red_config.json'

if not init_db(create_tables=False):
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)

blueConfig = parseConfig(blueConfigFile)
blueConfLog = draftClass(blueConfig.log)

#log = initLogging(blueConfLog) # init logging

class SuiteView(sqla.ModelView):
    column_labels = dict(name='Suite Name', plugins='Attached Plugins', subnet="Default Plugin for Subnets", host = 'Attached to Hosts')
    column_list = ('name', 'plugins', 'subnet')
    form_columns = ('name', 'description', 'plugins', 'host', 'subnet')

class HostView(sqla.ModelView):
    column_list = ('hostname', 'ipaddress',  'maintenance', 'suite', 'subnet')
    form_excluded_columns = ('hostid', 'date_created', 'date_modified', 'status', 'stats', 'hostUUID', 'history')
    column_labels = dict(suite='Suite Name', subnet='Subnet of the Host', login='Account for SSH')

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.hostUUID = getUniqueID()
        else:
            model.date_modified = now()
        return model

    def after_model_change(self, form, model, is_created):
        RedApp.fillSchedule()
        return model

    @action('enable maintenance', 'Enable Maintenance', 'Are you sure you want to enable maintenance for selected hosts?')
    def enable_maintenance(self, ids):
        try:
            hosts = Host.query.filter(Host.id.in_(ids)).all()
            count = 0
            for host in hosts:
                if host.maintenanceON():
                    db_session.add(host)
                    db_session.commit()
                    count += 1
            RedApp.fillSchedule()
            flash(ngettext('Host was putted to maintenance.',
                           '%(count)s hosts were putted to maintenance.',
                           count,
                           count=count))
        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash(gettext('Failed to put hosts to maintenance. %(error)s', error=str(ex)), 'error')

    @action('disable maintenance', 'Disable Maintenance', 'Are you sure you want to disable maintenance for selected hosts?')
    def disable_maintenance(self, ids):
        try:
            hosts = Host.query.filter(Host.id.in_(ids)).all()
            count = 0
            for host in hosts:
                if host.maintenanceOFF():
                    db_session.add(host)
                    db_session.commit()
                    count += 1
            RedApp.fillSchedule()
            flash(ngettext('Host was putted out of maintenance.',
                           '%(count)s hosts were putted out of maintenance.',
                           count,
                           count=count))
        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash(gettext('Failed to put hosts out of maintenance. %(error)s', error=str(ex)), 'error')

class PluginView(sqla.ModelView):
    column_list = ('customname', 'interval', 'date_created', 'date_modified', 'id')
    form_excluded_columns = ('pluginUUID', 'date_created','date_modified', 'suitos', 'status', 'history')
    form_args = dict(
        script = dict(label='Name of the Script file', validators=[validators.required(), validators.Length(min=3, max=100)]),
        customname = dict(label='Custom script name for Suite', validators=[validators.required(), validators.Length(min=3, max=100)]),
        interval = dict(label='Execution interval, in seconds', validators=[validators.required(), validators.NumberRange(10,3600)]),
    )

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.pluginUUID = getUniqueID()
        else:
            model.date_modified = now()
        return model

    def after_model_change(self, form, model, is_created):
        RedApp.fillSchedule()
        return model

    def on_model_delete(self, model):
        model.suites.clear()
        db_session.delete(Status).where(Status.plugin_id == model.id)
        db_session.commit()
        return model

class DashBoardView(sqla.ModelView):
    page_size = 10
    list_template = 'status_list.html'
    can_create = False
    can_delete = False
    can_edit = False
    column_display_pk = False
    can_export = True
    column_list = ('hostname', 'ipaddress', 'stats') #, 'interval', 'last_check_run', 'last_status', 'last_exitcode')
    column_searchable_list = ('hostname', 'ipaddress')

class SubnetView(sqla.ModelView):
    page_size = 50
    list_template = 'subnet_list.html'
    column_list = ('name', 'subnet', 'netmask', 'suite')
    column_labels = dict(name='Name', suite='Default Discovery Suite')
    form_args = dict(
        name = dict(label='Subnet Name', validators=[validators.required(), validators.Length(min=3, max=100)]),
        subnet = dict(label='Subnet', validators=[validators.required(), validators.IPAddress()]),
        netmask = dict(label='Netmask', validators=[validators.required(), validators.IPAddress()]),
    )

class HistoryView(sqla.ModelView):
    page_size = 200
    can_edit = False
    can_create = False
    can_export = True
    column_list = ('host', 'plugin', 'check_run_time', 'interval', 'check_exitcode', 'details', 'plugin.description')
    column_searchable_list = ('host.hostname', 'plugin.script')

webif = Admin (name='blue', template_mode='bootstrap3',
               index_view=DashBoardView(Host, db_session, url='/',
                                        endpoint='admin', name='Dashboard',
                                        menu_icon_type='glyph', menu_icon_value='glyphicon-home'))
webif.add_view(PluginView(Plugin, db_session, name="Plugins")) #, category="Checks"))
webif.add_view(SuiteView(Suite, db_session, name="Suites")) #, category="Checks"))
webif.add_view(HostView(Host, db_session, name="Hosts")) #, category="Targets"))
webif.add_view(SubnetView(Subnet, db_session, name="Subnet")) #, category="Targets"))
webif.add_view(HistoryView(History, db_session, name="History")) #, category="Targets"))


RedApp = Scheduler(redConfigFile)
RedApp.startRedService()

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
