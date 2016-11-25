from flask import Blueprint, abort, jsonify, request, url_for
from sqlalchemy.orm import contains_eager
from sqlalchemy.exc import IntegrityError

from monitoring import RRD
from core.models import Host, Subnet, Plugin, History, Suite, Status
#bcrypt, Schedule
from tools import resolveIP, validateIP
import time

VIOLET = 'violet'
COMMON = 'common'
PER_PAGE = 10
STATUS_OK = 0
STATUS_WARNING = 1
STATUS_ERROR = 2

def initRedApiBP(scheduler, db_session):
    redapiBP = Blueprint('redapi_blueprint', __name__)
    statRRDFile = 'common_statistics.rrd'

    @redapiBP.route('/redapi/monitoring/common')
    @redapiBP.route('/redapi/monitoring/common/<period>')
    def getCustomStats(period = 'last'):
        if period == 'all':
            return jsonify(**RRD(statRRDFile).\
                           getChartData(hours = 1, grades = 60))
        elif period =='last':
            return jsonify(**RRD(statRRDFile).getLatestUpdate())
        else:
            abort(404)

    @redapiBP.route('/redapi/monitoring/violet/<violet_id>/<period>')
    def getSingleVioletStats(violet_id, period):
        if (violet_id.startswith('violet')) and \
            (violet_id in getWorkersList().keys()):
            if period == "all":
                rrdinst = RRD("{}.rrd".format(violet_id), statType=VIOLET)
                return jsonify(**rrdinst.getChartData(hours = 1, grades = 60))
            elif "last":
                return jsonify(**RRD(statRRDFile).getLatestUpdate())
            else:
                abort(404)
        else:
            abort(404)

    @redapiBP.route('/redapi/monitoring/violets')
    @redapiBP.route('/redapi/monitoring/violets/<period>')
    def getAllVioletStats(period = 'last'):
        if period not in ('all', 'last'):
            abort(404)
        res = dict()
        workers = getWorkersList()
        for key in workers.keys():
            if key.startswith('violet'):
                rrdinst = RRD("{}.rrd".format(key), statType=VIOLET)
                try:
                    res[key] = rrdinst.getChartData(hours = 1, grades = 60)\
                               if period == 'all' else\
                               rrdinst.getLatestUpdate()
                except Exception as e:
                    print 'api command failed', e
                    pass
        return jsonify(**res)

    @redapiBP.route('/redapi/violet/getactiveworkers')
    def getWorkersListJson():
        return jsonify(**getWorkersList())

    @redapiBP.route('/redapi/status')
    @redapiBP.route('/redapi/status/<pluginType>/<int:page>')
    def getPluginStatus(pluginType = 'all', page = 1):
        if page < 1:
            abort(404)
        if pluginType == "all":
            hosts_query = db_session.query(Host)#.all()
        elif pluginType == "error":
            hosts_query = generateHostStatsQuery(STATUS_ERROR)
        elif pluginType == "warn":
            hosts_query = generateHostStatsQuery(STATUS_WARNING)
        elif pluginType == "ok":
            hosts_query = generateHostStatsQuery(STATUS_OK)
        else:
            abort(404)
        hosts_status = paginationOutputOfQuery(hosts_query, page)
        res = [check.APIGetDict(short = False) for check in hosts_status]
        return jsonify(*res)

    @redapiBP.route('/redapi/plugins')
    @redapiBP.route('/redapi/plugins/<int:page>')
    def getPluginsList(page = 1):
        if page < 1:
            abort(404)
        plugins_query = db_session.query(Plugin)
        plugins = paginationOutputOfQuery(plugins_query, page)
        res = [plugin.APIGetDict(short = False) for plugin in plugins]
        return jsonify(*res)

    @redapiBP.route('/redapi/suites')
    @redapiBP.route('/redapi/suites/<int:page>')
    def getSuitesList(page = 1):
        if page < 1:
            abort(404)
        suites_query = db_session.query(Suite)
        suites = paginationOutputOfQuery(suites_query, page)
        res = [suite.APIGetDict(short=False) for suite in suites]
        return jsonify(*res)

    @redapiBP.route('/redapi/subnets')
    @redapiBP.route('/redapi/subnets/<int:page>')
    def getSubnetsList(page = 1):
        if page < 1:
            abort(404)
        subnets_query = db_session.query(Subnet)
        subnets = paginationOutputOfQuery(subnets_query, page)
        res = [subnet.APIGetDict(short=False) for subnet in subnets]
        return jsonify(*res)

    @redapiBP.route('/redapi/hosts')
    @redapiBP.route('/redapi/hosts/<int:page>')
    def getHostsList(page = 1):
        if page < 1:
            abort(404)
        hosts_query = db_session.query(Host)
        hosts = paginationOutputOfQuery(hosts_query, page)
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

    @redapiBP.route('/redapi/host', methods = ['GET','PUT'])
    def singleHostOps():
        exitcode = 200
        if request.method == 'GET':
            ip = request.args.get('ip') or '127.0.0.1'
            if not validateIP(ip):
                abort(404)
            host = db_session.query(Host).\
                        filter(Host.ipaddress == ip).first()
            if not host:
                res = dict(message = 'Host with provided IP not found')
                exitcode = 404
            else:
                res = host.APIGetDict(short = False)
        elif 'PUT':
            try:
                ip, suiteID, subnetID =  parseParamsForNewHost(request.args)
            except AssertionError:
                abort(404)
            newHost = Host()
            newHost.ipaddress = ip
            newHost.hostname = resolveIP(ip)
            newHost.suite_id = suiteID
            newHost.subnet_id = subnetID
            db_session.add(newHost)
            try:
                db_session.commit()
                res = dict(message = 'Host successfully added')
            except IntegrityError as e:
                db_session.rollback()
                res = dict(message = e.message)
                exitcode = 501
        return jsonify(**res), exitcode

    ############################################################################
    def parseParamsForNewHost(params):
        suiteID = subnetID = None
        ip = params.get('ip')
        if not validateIP(ip):
            raise AssertionError
        suite = params.get('suite')
        if suite:
            suiteDB = Suite.query.filter(Suite.name == suite).first()
            if not suiteDB:
                raise AssertionError
            else:
                suiteID = suiteDB.id
        subnet = params.get('subnet')
        if subnet:
            subnetDB = Subnet.query.filter(Subnet.name == subnet).first()
            if not subnetDB:
                raise AssertionError
            else:
                if not suite:
                    suiteID = subnetDB.suite.id
                subnetID = subnetDB.id
        return (ip, suiteID, subnetID)

    def getWorkersList():
        try:
            workers = scheduler.MQ.getActiveClients()
        except:
            abort(404)
        res = dict()
        for worker in workers:
            if worker.get('user') == 'violet':
                worker_id = worker['client_properties']['connection_id']
                res[worker_id] = dict(host = worker.get('host'),
                                      user = worker.get('user'))
        return res

    def generateHostStatsQuery(exitcode):
        return db_session.query(Host).join(Host.stats).\
                options(contains_eager(Host.stats)).\
                filter(Status.last_exitcode == exitcode)

    def paginationOutputOfQuery(query, page, perPage = PER_PAGE):
        return query.limit(PER_PAGE).offset((page - 1) * perPage).all()

    return redapiBP

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
