from flask_admin import Admin

from flask_admin.contrib import sqla, fileadmin
from core.models import Host, Subnet, Plugin, History, Suite, Status #bcrypt, Schedule
from core.database import init_db, db_session
from sqlalchemy.sql.functions import now

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
    list_template = 'status_list.html'
    can_create = False
    can_delete = False
    can_edit = False
    column_display_pk = False
    can_export = True
    column_list = ('host', 'host.ipaddress', 'plugin', 'last_check_run', 'last_status', 'last_exitcode')
    column_searchable_list = ('host.hostname',)
    column_default_sort = ('host.hostname')
    #column_sortable_list = ('host.hostname',)

webif = Admin (name='blue', template_mode='bootstrap3', url='/', index_view=DashBoardView(Status, db_session, url='/', endpoint='admin', name='Dashboard'))
webif.add_view(PluginView(Plugin, db_session, name="Plugins", category="Checks"))
webif.add_view(SuiteView(Suite, db_session, name="Suites", category="Checks"))
webif.add_view(HostView(Host, db_session, name="Hosts", category="Targets"))
webif.add_view(sqla.ModelView(Subnet, db_session, name="Subnet", category="Targets"))
