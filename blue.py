import sys
from flask import Flask
from flask_admin import Admin
from core.models import Host, Subnet, Plugin, Schedule #bcrypt,
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

if not init_db():
    print "Service is unable to connect to DB. Check if DB service is running. Aborting."
    sys.exit(1)

if isMQ:
    MQ = MQ('s', confQueue) # init MQ
    if (not MQ.outChannel):
        print "Unable to connect to RabbitMQ. Check configuration and if RabbitMQ is running. Aborting."
        sys.exit(1)

#log = tools.initLogging(confLog) # init logging

class ScheduleView(sqla.ModelView):
    column_list = ('enabled', 'plugin', 'host', 'interval', 'date_created', 'date_modified', 'desc', 'id')
    form_excluded_columns = ('date_created','date_modified', 'last_check_run', 'last_status', 'last_exitcode')

    def on_model_change(self, form, model, is_created):
        model.date_modified = now()
        if isMQ:
            message = tools.prepareDict(converted = True,
                                    type='taskChange',
                                    option='active',
                                    taskid = model.id,
                                    value = model.enabled)
            MQ.sendMessage(message)
        return model

class DashBoardView(sqla.ModelView):
    can_create = False
    can_delete = False
    can_edit = False
    column_display_pk = False
    can_export = True
    column_list = ('host', 'plugin', 'last_check_run', 'last_status', 'last_exitcode')


arg = ''.join(sys.argv[1:]) or True
if arg == 'i':

    with main.app.app_context():
    #drop_all_tables_and_sequences(db.engine)
        #print dir(models.Base)
        models.Base.metadata.drop_all()
        models.Base.metadata.create_all()

app = Flask (__name__)
app.secret_key="a92547e3847063649d9d732a183418bf"

admin = Admin (app, name='blue', template_mode='bootstrap3', url='/', index_view=DashBoardView(Schedule, db_session, url='/', endpoint='admin', name='Dashboard'))
admin.add_view(sqla.ModelView(Host, db_session, name="Hosts"))
admin.add_view(sqla.ModelView(Plugin, db_session, name="Plugins"))
admin.add_view(ScheduleView(Schedule, db_session, name="Scheduler"))
admin.add_view(sqla.ModelView(Subnet, db_session, name="Subnets"))

#db.init_app(app)
#bcrypt.init_app(app)

app.run(debug=True, host='0.0.0.0', threaded=True)
