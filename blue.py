import sys
from flask import Flask
from flask_admin import Admin
from core.models import bcrypt, Host, Subnet, Plugin, Schedule
from core.database import init_db, db_session
from core.mq import MQ
from core import tools
from flask_admin.contrib import sqla, fileadmin
from sqlalchemy.sql.functions import now
#from blueif.views import DashBoardView, ScheduleView

blueConfig = './config/blue_config.json'


init_db()



configFile = tools.parseConfig(blueConfig)
conf = configFile['configuration']
#log = tools.initLogging(conf['log']) # init logging
MQ = MQ('s', conf['queue']) # init MQ

class ScheduleView(sqla.ModelView):
    column_list = ('enabled', 'plugin', 'host', 'interval', 'date_created', 'date_modified', 'desc', 'id')
    form_excluded_columns = ('date_created','date_modified', 'last_check_run', 'last_status', 'last_exitcode')

    def on_model_change(self, form, model, is_created):
        model.date_modified = now()
        message = tools.prepareDict(converted = True,
                                    type='taskChange',
                                    option='active',
                                    taskid = model.id,
                                    value = model.enabled)
        MQ.sendMessage(message)
        return model

        """if model.typeof == 1:
        if is_created:
        curTime = dt.now().replace(day=1, minute=0, hour=0, second=0, microsecond=0)
        else:
        curTime = model.date_created.replace(day=1, minute=0, hour=0, second=0, microsecond=0)
        archive = Archive.query.filter_by(date=curTime).all()
        try:
        record = archive[0]
        record.articles.append(model)
        except IndexError:
        newArch = Archive(curTime,  model)
        db.session.add(newArch)
        db.session.commit()"""


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
bcrypt.init_app(app)

app.run(debug=True, host='0.0.0.0', threaded=True)
