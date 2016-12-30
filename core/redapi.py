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
        try:
            return jsonify(**getWorkersList())
        except:
            # log it!
            abort(501)

    def getWorkersList():
        workers = scheduler.MQ.getActiveClients()
        res = dict()
        for worker in workers:
            if worker.get('user') == 'violet':
                worker_id = worker['client_properties']['connection_id']
                res[worker_id] = dict(host = worker.get('host'),
                                      user = worker.get('user'))
        return res

    ############################################################################
    @redapiBP.route('/redapi/status')
    @redapiBP.route('/redapi/status/<pluginType>')
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

    def generateHostStatsQuery(exitcode):
        return db_session.query(Host).join(Host.stats).\
                options(contains_eager(Host.stats)).\
                filter(Status.last_exitcode == exitcode)

    def paginationOutputOfQuery(query, page, perPage = PER_PAGE):
        return query.limit(PER_PAGE).offset((page - 1) * perPage).all()

    ############################################################################

    @redapiBP.route('/redapi/host', methods = ['GET','POST','PUT','DELETE'])
    def singleHostOps():
        """
        Api to handle single host.
        Available methods = GET, POST, PUT, DELETE
        ---
        GET
        /redapi/host?ip=<ip>
        get all the info for single host
        ---
        POST
        /redapi/host?ip=<ip>&hostname=<hostname>&suite=<suitename>&subnet=<subnetname>
        ---
        PUT
        /redapi/host?ip=<ip>&maintenance=<on|off>
        manage maintenance mode for host

        """
        exitcode = 200
        if request.method == 'GET':
            try:
                res, exitcode = apiHostGetRequest(request.args)
            except AssertionError:
                abort(404)
        elif request.method == 'POST':
            try:
                res, exitcode = apiHostPostRequest(request.args)
            except AssertionError:
                abort(404)
        elif request.method == 'PUT':
            try:
                res, exitcode = apiHostPutRequest(request.args)
            except AssertionError:
                abort(404)
        elif request.method == 'DELETE':
            try:
                res, exitcode = apiHostDeleteRequest(request.args)
            except AssertionError:
                abort(404)
        return jsonify(**res), exitcode

    def apiHostGetRequest(params):
        ip = params.get('ip') or '127.0.0.1'
        if not validateIP(ip):
            raise AssertionError
        host = db_session.query(Host).\
                    filter(Host.ipaddress == ip).first()
        if not host:
            res = dict(message = 'Host with provided IP not found')
            exitcode = 404
        else:
            res = host.APIGetDict(short = False)
            exitcode = 200
        return (res, exitcode)

    def apiHostPostRequest(params):
        try:
            params_checked = parseParamsForHost(params)
        except ValueError as ve:
            res = dict(message = ve.message)
            return (res, 501)
        db_session.add(Host(*params_checked))
        try:
            db_session.commit()
            res = dict(message = 'Host successfully added')
            exitcode = 200
        except IntegrityError as e:
            db_session.rollback()
            res = dict(message = e.message)
            exitcode = 501
        return (res, exitcode)

    def apiHostPutRequest(params):
        ip = params.get('ip')
        if not validateIP(ip):
            raise AssertionError
        host = db_session.query(Host).\
                    filter(Host.ipaddress == ip).first()
        if not host:
            res = dict(message = 'Host with provided IP not found')
            exitcode = 404
        else:
            if not params.get('maintenance'):
                host_upd = updateHostParams(host, *parseParamsForHost(params))
                scheduler.activateHostChecks(host_upd)
                db_session.add(host_upd)
                db_session.commit()
                res = dict(message = 'Host updated')
                exitcode = 200
            else:
                if params.get('maintenance') == 'on':
                    host.maintenanceON()
                    scheduler.pauseHostChecks(host)
                    db_session.add(host)
                    db_session.commit()
                    res = dict(message = 'Host updated')
                    exitcode = 200
                elif params.get('maintenance') == 'off':
                    host.maintenanceOFF()
                    if not scheduler.activateHostChecks(host):
                        res = dict(message = 'No suite attached to host!')
                        exitcode = 501
                    else:
                        db_session.add(host)
                        db_session.commit()
                        res = dict(message = 'Host updated')
                        exitcode = 200
        return (res, exitcode)

    def apiHostDeleteRequest(params):
        ip = params.get('ip')
        if not validateIP(ip):
            raise AssertionError
        host = db_session.query(Host).\
                    filter(Host.ipaddress == ip).first()
        if not host:
            res = dict(message = 'Host with provided IP not found')
            exitcode = 404
        else:
            try:
                db_session.delete(host)
                db_session.commit()
                scheduler.removeHostChecks(hosts)
                res = dict(message = 'Host with provided IP was deleted')
                exitcode = 200
            except Exception as e:
                res = dict(message = e.message)
                exitcode = 501
        return (res, exitcode)

    def updateHostParams(host, ip, suiteID, subnetID, hostname, login):
        if hostname:
            host.hostname = hostname
        if login:
            host.login = logins
        if subnetID:
            host.subnet_id = subnetID
        if suiteID:
            if host.suite_id:
                scheduler.removeHostChecks(host)
                host.stats[:] = list()
            host.suite_id = suiteID
        return host

    def parseParamsForHost(params):
        suiteID = subnetID = None
        ip = params.get('ip')
        if not validateIP(ip):
            raise ValueError("Failed to validate provided IP")
        suite = params.get('suite')
        if suite:
            suiteDB = Suite.query.filter(Suite.name == suite).first()
            if not suiteDB:
                raise ValueError("Provided suite is not found in DB")
            else:
                suiteID = suiteDB.id
        subnet = params.get('subnet')
        if subnet:
            subnetDB = Subnet.query.filter(Subnet.name == subnet).first()
            if not subnetDB:
                raise ValueError("Provided subnet is not found in DB")
            else:
                if not suite:
                    suiteID = subnetDB.suite.id
                subnetID = subnetDB.id
        hostname = params.get('hostname')
        if not hostname:
            hostname = resolveIP(ip)
        login = params.get('login')
        return (ip, suiteID, subnetID, hostname, login)

    ############################################################################

    @redapiBP.route('/redapi/plugin', methods = ['GET','POST','PUT','DELETE'])
    def singlePluginOps():
        """
        Api to handle single plugin.
        Available methods = GET, POST, PUT, DELETE
        ---
        GET
        /redapi/plugin?customname=<customname>
        get all the params for single plugin
        ---
        POST
        /redapi/plugin?customname=<customname>&script=<script>&interval=<interval>&params=<params>&ssh_wrapper=<on|off>
        ---
        PUT
        /redapi/host?ip=<ip>&maintenance=<on|off>
        manage maintenance mode for host

        """
        exitcode = 200
        if request.method == 'GET':
            try:
                res, exitcode = apiPluginGetRequest(request.args)
            except AssertionError:
                abort(404)
        elif request.method == 'POST':
            try:
                res, exitcode = apiPluginPostRequest(request.args)
            except AssertionError:
                abort(404)
        elif request.method == 'PUT':
            try:
                res, exitcode = apiPluginPutRequest(request.args)
            except AssertionError:
                abort(404)
        elif request.method == 'DELETE':
            try:
                res, exitcode = apiPluginDeleteRequest(request.args)
            except AssertionError:
                abort(404)
        return jsonify(**res), exitcode

    def apiPluginGetRequest(params):
        customname = params.get('customname')
        if not customname:
            raise AssertionError
        plugin = db_session.query(Plugin).\
                    filter(Plugin.customname == customname).first()
        if not plugin:
            res = dict(message = 'Plugin with provided customname not found')
            exitcode = 404
        else:
            res = plugin.APIGetDict(short = False)
            exitcode = 200
        return (res, exitcode)

    def apiPluginPostRequest(params):
        try:
            params_checked = parseParamsForPlugin(params)
        except ValueError as ve:
            res = dict(message = ve.message)
            return (res, 501)
        db_session.add(Plugin(*params_checked))
        try:
            db_session.commit()
            res = dict(message = 'Plugin successfully added')
            exitcode = 200
        except IntegrityError as e:
            db_session.rollback()
            res = dict(message = e.message)
            exitcode = 501
        return (res, exitcode)

    def apiPluginPutRequest(params):
        pass

    def apiPluginDeleteRequest(params):
        customname = params.get('customname')
        if not customname:
            raise AssertionError
        plugin = db_session.query(Plugin).\
                    filter(Plugin.customname == customname).first()
        if not plugin:
            res = dict(message = 'Plugin with provided customname not found')
            exitcode = 404
        else:
            try:
                db_session.delete(plugin)
                db_session.commit()
                #scheduler.removeHostChecks(hosts)
                res = dict(message = 'Plugin with provided customname was deleted')
                exitcode = 200
            except Exception as e:
                res = dict(message = e.message)
                exitcode = 501
        return (res, exitcode)

    def parseParamsForPlugin(params):
        customname = params.get('customname')
        if not customname:
            raise ValueError("customname is not set")
        interval = params.get('interval')
        if interval:
            try:
                int(interval)
            except:
                raise ValueError("interval value is incorrect")
        ssh_wrapper = params.get('ssh_wrapper') or False
        if ssh_wrapper:
            if ssh_wrapper == "on":
                ssh_wrapper = True
            else:
                raise ValueError("ssh_wrapper parameter is incorrect")
        script = params.get('script')
        if not script:
            raise ValueError("script name is not set")
        script_params = params.get('params')
        return (script, customname, interval, script_params, ssh_wrapper)

    ############################################################################

    @redapiBP.route('/redapi/scheduler/jobs')
    def getSchedulerJobs():
        """
        Temporary solution without pagination
        """
        jobs = scheduler.get_jobs()
        jobs_list = list()
        for job in jobs:
            jobs_list.append(dict(name=job.name, id=job.id))
        return jsonify(*jobs_list)

    return redapiBP

"""
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
