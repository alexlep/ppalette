from flask import Blueprint, abort, jsonify, request, url_for
from sqlalchemy.orm import contains_eager
from sqlalchemy.exc import IntegrityError

from monitoring import RRD
from core.models import Host, Subnet, Plugin, History, Suite, Status
#bcrypt, Schedule
from tools import validateIP, resolveIP
from apitools import apiValidateMandParam, apiValidateIntegerParam,\
                     apiValidateTriggerParam, apiValidateIpParam
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
        if request.method == 'GET':
            res, exitcode = apiHostGetRequest(request.args)
        elif request.method == 'POST':
            res, exitcode = apiHostPostRequest(request.args)
        elif request.method == 'PUT':
            res, exitcode = apiHostPutRequest(request.args)
        elif request.method == 'DELETE':
            res, exitcode = apiHostDeleteRequest(request.args)
        return jsonify(**res), exitcode

    def apiHostGetRequest(params):
        try:
            ip = apiValidateIpParam('ip', params)
        except ValueError as ve:
            return (dict(message=ve.message), 400)
        host = db_session.query(Host).\
                    filter(Host.ipaddress == ip).first()
        if not host:
            res = dict(message='Host with IP {} not found'.format(ip))
            exitcode = 400
        else:
            res = host.APIGetDict(short=False)
            exitcode = 200
        return (res, exitcode)

    def apiHostPostRequest(params):
        try:
            params_checked = parseParamsForHost(params)
        except ValueError as ve:
            return (dict(message=ve.message), 400)
        db_session.add(Host(*params_checked))
        try:
            db_session.commit()
            res = dict(message='Host {} successfully added'.\
                       format(params.get('ip')))
            exitcode = 200
        except IntegrityError as e:
            db_session.rollback()
            res = dict(message=e.message)
            exitcode = 501
        return (res, exitcode)

    def apiHostPutRequest(params):
        try:
            ip = apiValidateIpParam('ip', params)
        except ValueError as ve:
            return (dict(message=ve.message), 400)
        host = db_session.query(Host).\
                    filter(Host.ipaddress == ip).first()
        if not host:
            res = dict(message='Host with IP {} not found'.format(ip))
            exitcode = 400
        else:
            try:
                host_params = parseParamsForHost(params=params, edit=True)
            except ValueError as ve:
                res = dict(message=ve.message)
                return (res, 400)
            host.updateParams(*host_params)
            db_session.add(host)
            try:
                db_session.commit()
                res = dict(message='Host {} updated'.format(ip))
                exitcode = 200
            except IntegrityError as e:
                db_session.rollback()
                res = dict(message=e.message)
                exitcode = 501
        return (res, exitcode)

    def apiHostDeleteRequest(params):
        try:
            ip = apiValidateIpParam('ip', params)
        except ValueError as ve:
            return (dict(message=ve.message), 400)
        host = db_session.query(Host).\
                    filter(Host.ipaddress == ip).first()
        if not host:
            res = dict(message='Host with IP {} not found'.format(ip))
            exitcode = 400
        else:
            try:
                db_session.delete(host)
                db_session.commit()
                res = dict(message='Host with IP {} was deleted'.format(ip))
                exitcode = 200
            except Exception as e:
                res = dict(message=e.message)
                exitcode = 501
        return (res, exitcode)

    def parseParamsForHost(params, edit = False):
        suiteID = subnetID = None
        if not edit:
            ip = apiValidateIpParam('ip', params)
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
        login = params.get('login')
        if not edit:
            hostname = params.get('hostname') or resolveIP(ip)
            res = (ip, suiteID, subnetID, hostname, login)
        else:
            maintenance = apiValidateTriggerParam('maintenance', params)
            hostname = params.get('hostname')
            res = (suiteID, subnetID, hostname, login, maintenance)
        return res

    ############################################################################

    @redapiBP.route('/redapi/plugin', methods = ['GET','POST','PUT','DELETE'])
    def singlePluginOps():
        """
        Api to handle single plugin.
        Available methods = GET, POST, PUT, DELETE
        ---
        GET
        /redapi/plugin?customname=<str>
        get all the params for single plugin
        ---
        POST
        /redapi/plugin?customname=<str>&script=<str>&interval=<int>&params=<str>&ssh_wrapper=<on|off>&suite=<str>
        create new plugin
        ---
        PUT
        /redapi/plugin?customname=<str>&script=<str>&interval=<int>&params=<str>&ssh_wrapper=<on|off>&suite=<str>
        modify configuration of existing plugin
        ---
        DELETE
        /redapi/plugin?customname=<str>
        delete single plugin from DB

        """
        if request.method == 'GET':
            res, exitcode = apiPluginGetRequest(request.args)
        elif request.method == 'POST':
            res, exitcode = apiPluginPostRequest(request.args)
        elif request.method == 'PUT':
            res, exitcode = apiPluginPutRequest(request.args)
        elif request.method == 'DELETE':
            res, exitcode = apiPluginDeleteRequest(request.args)
        return jsonify(**res), exitcode

    def apiPluginGetRequest(params):
        try:
            customname = apiValidateMandParam('customname', params)
        except ValueError as ve:
            return (dict(message=ve.message), 400)
        plugin = db_session.query(Plugin).\
                    filter(Plugin.customname == customname).first()
        if not plugin:
            res = dict(message='Plugin with name {} not found'.\
                       format(customname))
            exitcode = 400
        else:
            res = plugin.APIGetDict(short = False)
            exitcode = 200
        return (res, exitcode)

    def apiPluginPostRequest(params):
        try:
            params_checked = parseParamsForPlugin(params)
        except ValueError as ve:
            res = dict(message = ve.message)
            return (res, 400)
        newPlugin = Plugin(*params_checked)
        db_session.add(newPlugin)
        try:
            db_session.commit()
            scheduler.registerJob(newPlugin)
            res = dict(message = 'Plugin successfully added')
            exitcode = 200
        except IntegrityError as e:
            db_session.rollback()
            res = dict(message = e.message)
            exitcode = 501
        return (res, exitcode)

    def apiPluginPutRequest(params):
        try:
            customname = apiValidateMandParam('customname', params)
        except ValueError as ve:
            res = dict(message = ve.message)
            return (res, 400)
        plugin = db_session.query(Plugin).\
                    filter(Plugin.customname == customname).first()
        if not plugin:
            res = dict(message = 'Plugin with name {} not found'.\
                       format(customname))
            exitcode = 400
        else:
            try:
                params_checked = parseParamsForPlugin(params=params, edit=True)
            except ValueError as ve:
                res = dict(message = ve.message)
                return (res, 400)
            plugin.updateParams(*params_checked)
            db_session.add(plugin)
            try:
                db_session.commit()
                res = dict(message='Plugin with name {} was updated'.\
                           format(customname))
                exitcode = 200
            except Exception as e:
                res = dict(message = e.message)
                exitcode = 501
        return (res, exitcode)

    def apiPluginDeleteRequest(params):
        try:
            customname = apiValidateMandParam('customname', params)
        except ValueError as ve:
            res = dict(message = ve.message)
            return (res, 400)
        plugin = db_session.query(Plugin).\
                    filter(Plugin.customname == customname).first()
        if not plugin:
            res = dict(message = 'Plugin with name {} not found'.\
                       format(customname))
            exitcode = 400
        else:
            try:
                db_session.delete(plugin)
                db_session.commit()
                scheduler.remove_job(plugin.pluginUUID)
                res = dict(message='Plugin with name {} was deleted'.\
                           format(customname))
                exitcode = 200
            except Exception as e:
                res = dict(message = e.message)
                exitcode = 501
        return (res, exitcode)

    def parseParamsForPlugin(params, edit=False):
        suiteDB = None
        if not edit:
            customname = apiValidateMandParam('customname', params)
            script = apiValidateMandParam('script', params)
        else:
            script = params.get('script')
        interval = apiValidateIntegerParam('interval', params)
        script_params = params.get('params')
        ssh_wrapper = apiValidateTriggerParam('ssh_wrapper', params)
        suite = params.get('suite')
        if suite:
            suiteDB = Suite.query.filter(Suite.name == suite).first()
            if not suiteDB:
                raise ValueError("Provided suite is not found in DB")
        if not edit:
            res = (script, customname, interval, script_params, ssh_wrapper,
                   suiteDB)
        else:
            res = (script, interval, script_params, ssh_wrapper, suiteDB)
        return res

    ############################################################################

    @redapiBP.route('/redapi/scheduler/jobs')
    def getSchedulerJobs():
        jobs = scheduler.get_jobs()
        jobs_list = list()
        for job in jobs:
            jobs_list.append(dict(name=job.name, id=job.id,
                                  next_run_time=job.next_run_time))
        return jsonify(*jobs_list)

    return redapiBP

"""
@BlueApp.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
"""
