# -*- coding: utf-8 -*-
import sys
import datetime as dt

from flask import flash
from flask_admin import Admin, BaseView, AdminIndexView, expose
from flask_admin.actions import action
from flask_admin.babel import ngettext
from flask_admin.contrib import sqla
from wtforms import BooleanField, TextField, PasswordField, validators
from sqlalchemy.sql.functions import now

from core.models import Host, Subnet, Plugin, History, Suite, Status #bcrypt, Schedule
from core.database import init_db, db_session
from core.monitoring import RRD
from core.tools import getUniqueID, draftClass, fromDictToJson

if not init_db(create_tables=False):
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)

class SuiteView(sqla.ModelView):
    column_labels = dict(name='Suite Name', plugins='Attached Plugins', subnet="Default Plugin for Subnets", host = 'Attached to Hosts')
    column_list = ('name', 'plugins', 'subnet')
    form_columns = ('name', 'description', 'plugins', 'host', 'subnet')

class HostView(sqla.ModelView):
    page_size = 100
    column_list = ('hostname', 'ipaddress',  'maintenance', 'suite', 'subnet')
    form_excluded_columns = ('hostid', 'date_created', 'date_modified', 'status', 'stats', 'hostUUID', 'history')
    column_labels = dict(suite='Suite Name', subnet='Subnet of the Host', login='Account for SSH')
    form_args = dict(
        ipaddress = dict(label='IP address', validators=[validators.required(), validators.IPAddress()]),
    )
    column_searchable_list = ('hostname', 'ipaddress')

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.hostUUID = getUniqueID()
        else:
            model.date_modified = now()
        print model.maintenance

        return model

    def after_model_change(self, form, model, is_created):
        if model.maintenance:
            for item in model.listScheduleItems():
                print item, "On, pause"
                webif.Scheduler.pause_job(item)
        else:
            if model.suite:
                webif.Scheduler.resumeHostFromMaintenance(model)
        return model

    @action('enable maintenance', 'Enable Maintenance', 'Are you sure you want to enable maintenance for selected hosts?')
    def enable_maintenance(self, ids):
        try:
            hosts = Host.query.filter(Host.id.in_(ids)).all()
            count = 0
            for host in hosts:
                if host.maintenanceON():
                    for item in host.listScheduleItems():
                        webif.Scheduler.pause_job(item)
                    db_session.add(host)
                    db_session.commit()
                    count += 1
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
                    webif.Scheduler.resumeHostFromMaintenance(host)
                    db_session.add(host)
                    db_session.commit()
                    count += 1
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
        webif.Scheduler.fillSchedule()
        return model

    def on_model_delete(self, model):
        model.suites.clear()
        db_session.delete(Status).where(Status.plugin_id == model.id)
        db_session.commit()
        return model

class StatusView(sqla.ModelView):
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
    column_list = ('name', 'subnet', 'netmask', 'suite')
    column_labels = dict(name='Name', suite='Default Discovery Suite')
    form_args = dict(
        name = dict(label='Subnet Name', validators=[validators.required(), validators.Length(min=3, max=100)]),
        subnet = dict(label='Subnet', validators=[validators.required(), validators.IPAddress()]),
        netmask = dict(label='Netmask', validators=[validators.required(), validators.IPAddress()]),
    )

    @action('trigger discovery', 'Trigger Discovery', 'Are you sure you want to trigger discvery for selected subnets?')
    def trigger_discovery(self, ids):
        try:
            count = 0
            for subnetid in ids:
                webif.Scheduler.sendDiscoveryRequest(subnetid)
                count += 1
            flash(ngettext('Discovery task for subnet was triggered.',
                           'Discovery tasks for %(count)s subnets were triggered.',
                           count,
                           count=count))
        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash(gettext('Failed to trigger discovery task. %(error)s', error=str(ex)), 'error')

class HistoryView(sqla.ModelView):
    page_size = 200
    can_edit = False
    can_create = False
    can_export = True
    column_list = ('host', 'plugin', 'check_run_time', 'interval', 'check_exitcode', 'details', 'plugin.description')
    column_searchable_list = ('host.hostname', 'plugin.script')

class DashBoardView(AdminIndexView):
    @expose('/')
    def index(self):
        return self.render('dashboard.html')

webif = Admin(name='blue', template_mode='bootstrap3', index_view=DashBoardView(name='Dashboard', url='/'))
#webif = Admin(name='blue', template_mode='bootstrap3', index_view=DashBoardView(name='Dashboard', url='/', menu_icon_type='glyph', menu_icon_value='glyphicon-home'))
webif.add_view(StatusView(Host, db_session, name="Status", endpoint="status")) #, category="Checks"))
webif.add_view(HistoryView(History, db_session, name="History")) #, category="Targets"))
webif.add_view(PluginView(Plugin, db_session, name="Plugins")) #, category="Configuration"))
webif.add_view(SuiteView(Suite, db_session, name="Suites")) #, category="Configuration"))
webif.add_view(HostView(Host, db_session, name="Hosts", endpoint="hosts")) #, category="Configuration"))
webif.add_view(SubnetView(Subnet, db_session, name="Subnets")) #, category="Configuration"))
