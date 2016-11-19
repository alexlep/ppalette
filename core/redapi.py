from flask import Blueprint, render_template, abort, jsonify
from jinja2 import TemplateNotFound
from monitoring import RRD
from glob import glob
import time
import json

VIOLET = 'violet'
COMMON = 'common'

def initRedApiBP(scheduler):
    redapiBP = Blueprint('redapi_blueprint', __name__)
    statRRDFile = 'common_statistics.rrd'

    @redapiBP.route('/redapi/stats/common/<period>')
    def getCustomStats(period):
        if period == 'all':
            return jsonify(**RRD(statRRDFile).getChartData(hours = 1, grades = 60))
        elif period =='last':
            return jsonify(**RRD(statRRDFile).getLatestUpdate())
        else:
            abort(404)

    @redapiBP.route('/redapi/stats/violet/<violet_id>/<period>')
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

    @redapiBP.route('/redapi/stats/violets/<period>')
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
