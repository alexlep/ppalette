from flask import Blueprint, render_template, abort, jsonify
from jinja2 import TemplateNotFound
from monitoring import RRD
from core.models import Host, Subnet, Plugin, History, Suite, Status #bcrypt, Schedule
from tools import prepareDictFromSQLA

from glob import glob
import time
from flask import json

VIOLET = 'violet'
COMMON = 'common'
PER_PAGE = 10
STATUS_OK = 0
STATUS_WARNING = 1
STATUS_ERROR = 2

def initRedApiBP(scheduler, db_session):
    redapiBP = Blueprint('redapi_blueprint', __name__)
    statRRDFile = 'common_statistics.rrd'

    @redapiBP.route('/redapi/monitoring/common/<period>')
    def getCustomStats(period):
        if period == 'all':
            return jsonify(**RRD(statRRDFile).getChartData(hours = 1, grades = 60))
        elif period =='last':
            return jsonify(**RRD(statRRDFile).getLatestUpdate())
        else:
            abort(404)

    @redapiBP.route('/redapi/monitoring/violet/<violet_id>/<period>')
    def getSingleVioletStats(violet_id, period):
        if (violet_id.startswith('violet')) and (violet_id in getWorkersList().keys()):
            if period == "all":
                return jsonify(**RRD("{}.rrd".format(violet_id), statType=VIOLET).getChartData(hours = 1, grades = 60))
            elif "last":
                return jsonify(**RRD(statRRDFile).getLatestUpdate())
            else:
                abort(404)
        else:
            abort(404)

    @redapiBP.route('/redapi/monitoring/violets/<period>')
    def getAllVioletStats(period):
        if period == 'all':
            res = dict()
            workers = getWorkersList()
            for key in workers.keys():
                if key.startswith('violet'):
                    try:
                        res[key] = RRD("{}.rrd".format(key), statType=VIOLET).getChartData(hours = 1, grades = 60)
                    except Exception as e:
                        print 'api command failed', e
                        pass
            return jsonify(**res)
        elif 'last':
            res = dict()
            workers = getWorkersList()
            for key in workers.keys():
                if key.startswith('violet'):
                    try:
                        res[key] = RRD("{}.rrd".format(key), statType=VIOLET).getLatestUpdate()
                    except Exception as e:
                        print 'api command failed', e
                        pass
            return jsonify(**res)
        else:
            abort(404)

    #@redapiBP.route('/redapi/violet/getactiveworkers')
    def getWorkersList():
        try:
            res = {}
            for worker in scheduler.MQ.getActiveClients():
                if worker['user'] == 'violet':
                    worker_id = worker ['client_properties']['connection_id']
                    res[worker_id] = {
                                    'host': worker['host'],
                                    'user': worker['user']
                                    }
            return res
        except:
            abort(501)

    @redapiBP.route('/redapi/violet/getactiveworkers')
    def getWorkersListJson():
        return jsonify(**getWorkersList())

    @redapiBP.route('/redapi/status/<pluginType>/<int:page>')
    def getPluginStatus(pluginType, page):
        if page < 1:
            abort(404)
        hosts_query = db_session.query(Host)#.all()
        hosts_status = hosts_query.limit(PER_PAGE).offset((page - 1) * PER_PAGE).all()
        if pluginType == "all":
            res = [check.APIGetDict(short = False) for check in hosts_status]
        elif pluginType == "error":
            res = [check.APIGetDict(short = False, exitcode = STATUS_ERROR) for check in hosts_status]
        elif pluginType == "warn":
            res = [check.APIGetDict(short = False, exitcode = STATUS_WARNING) for check in hosts_status]
        elif pluginType == "ok":
            res = [check.APIGetDict(short = False, exitcode = STATUS_OK) for check in hosts_status]
        else:
            abort(404)
        return jsonify(*res)

        #hosts_query = db_session.query(Status).\
        #    filter(Status.last_exitcode == 0)
             #subquery()
        #hosts_query = db_session.query(Host).select_from(Status).\
        #    join(Status.host).\
        #    filter(Status.last_exitcode == '0')
        #hosts_query = db_session.query(Host).join(status_subq, Host.stats)
        #db_session.query(Host).join((Status, Host.stats))
                                #filter(Status.last_exitcode == 0)
        #hosts_status = hosts_query.limit(PER_PAGE).offset((page - 1) * PER_PAGE).all()

    @redapiBP.route('/redapi/plugins/<int:page>')
    def getPluginsList(page):
        if page < 1:
            abort(404)
        plugins_query = db_session.query(Plugin)
        plugins = plugins_query.limit(PER_PAGE).offset((page - 1) * PER_PAGE).all()
        res = [plugin.APIGetDict(short = False) for plugin in plugins]
        return jsonify(*res)

    @redapiBP.route('/redapi/suites/<int:page>')
    def getSuitesList(page):
        if page < 1:
            abort(404)
        suites_query = db_session.query(Suite)
        suites = suites_query.limit(PER_PAGE).offset((page - 1) * PER_PAGE).all()
        res = [suite.APIGetDict(short=False) for suite in suites]
        return jsonify(*res)

    @redapiBP.route('/redapi/subnets/<int:page>')
    def getSubnetsList(page):
        if page < 1:
            abort(404)
        subnets_query = db_session.query(Suite)
        subnets = subnets_query.limit(PER_PAGE).offset((page - 1) * PER_PAGE).all()
        res = [subnet.APIGetDict(short=False) for subnet in subnets]
        return jsonify(*res)

    @redapiBP.route('/redapi/hosts/<int:page>')
    def getHostsList(page):
        if page < 1:
            abort(404)
        hosts_query = db_session.query(Host)
        hosts = hosts_query.limit(PER_PAGE).offset((page - 1) * PER_PAGE).all()
        res = [host.APIGetDict(short=False) for host in hosts]
        return jsonify(*res)

    @redapiBP.route('/redapi/scheduler/jobs')
    def getSchedulerJobs():
        print scheduler.get_jobs()[PER_PAGE:]
        #print dir(scheduler)
        #print scheduler.get_jobs()[0].name
        #print scheduler.get_jobs()[0].next_run_time
        #print scheduler.get_jobs()[0].next_run_time
        #scheduler.print_jobs()
        return jsonify(**{})

    return redapiBP

#        for elem in glob('[0-9]*.rrd'):
#            stats[elem] = RRD(elem).getVioletChartData()
"""
from flask import Flask
from core.tools import parseConfig, draftClass, initLogging
from core.scheduler import Scheduler



redConfigFile = './config/red_config.json'
RedApp = Scheduler(redConfigFile)

BlueApp = Flask (__name__)

@BlueApp.route('/api/job/add/<id_>', methods=['GET','POST'])
def add_job(id_):
    try:
        ss.addJobFromDB(int(id_))
    except:
        abort(500)
    return 'Hello, World!'

@BlueApp.route('/api/job/remove/<id_>', methods=['GET','POST'])
def remove_job(id_):
    if id_ == 'all':
        ss.remove_all_jobs()
    return 'removed'

@BlueApp.route('/api/job/get/<id_>', methods=['GET','POST'])
def get_job(id_):
    if id_ == 'all':
        ss.get_jobs()
    else:
        try:
            ss.get_job(int(id_))
        except:
            abort(500)
    return '200'

@BlueApp.route('/api/job/pause/<id_>', methods=['GET','POST'])
def pause_job(id_):
    if id_ == 'all':
        ss.pause()
    else:
        try:
            ss.pause_job(id_)
        except:
            abort(500)
    return '200'

@BlueApp.route('/api/job/resume/<id_>', methods=['GET','POST'])
def resume_job(id_):
    if id_ == 'all':
        ss.resume()
    else:
        try:
            ss.resume_job(id_)
        except:
            abort(500)
    return '200'

@BlueApp.route('/api/schedule/reload', methods=['GET','POST'])
def reloadJobs():
    try:
        ss.fillSchedule()
    except:
        abort(500)
    return '200'

@BlueApp.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

"""
