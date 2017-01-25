from flask import Blueprint, abort, jsonify, request, url_for

from monitoring import RRD
from models import Host, Subnet, Plugin, History, Suite, Status
from apitools import apiSingleCallHandler, apiListCallHandler

VIOLET = 'violet'
COMMON = 'common'
PER_PAGE = 10

def initRedApiBP(scheduler):
    redapiBP = Blueprint('redapi_blueprint', __name__)
    statRRDFile = 'common_statistics.rrd'

    @redapiBP.route('/redapi/monitoring/common')
    @redapiBP.route('/redapi/monitoring/common/<period>')
    def getCustomStats(period='last'):
        if period == 'all':
            return jsonify(**RRD(statRRDFile).\
                           getChartData(hours=1, grades=60))
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
                return jsonify(**rrdinst.getChartData(hours=1, grades=60))
            elif "last":
                return jsonify(**RRD(statRRDFile).getLatestUpdate())
            else:
                abort(404)
        else:
            abort(404)

    @redapiBP.route('/redapi/monitoring/violets')
    @redapiBP.route('/redapi/monitoring/violets/<period>')
    def getAllVioletStats(period='last'):
        if period not in ('all', 'last'):
            abort(404)
        res = dict()
        workers = getWorkersList()
        for key in workers.keys():
            if key.startswith('violet'):
                rrdinst = RRD("{}.rrd".format(key), statType=VIOLET)
                try:
                    res[key] = rrdinst.getChartData(hours=1, grades=60)\
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
                res[worker_id] = dict(host=worker.get('host'),
                                      user=worker.get('user'))
        return res

    ############################################################################
    @redapiBP.route('/redapi/status')
    @redapiBP.route('/redapi/status/<pluginType>')
    @redapiBP.route('/redapi/status/<pluginType>/<int:page>')
    def getPluginStatus(pluginType='all', page=1):
        res, exitcode = apiListCallHandler(Host, page, PER_PAGE,
                                           pluginType).run()
        return jsonify(**res), exitcode

    @redapiBP.route('/redapi/plugins')
    @redapiBP.route('/redapi/plugins/<int:page>')
    def getPluginsList(page=1):
        res, exitcode = apiListCallHandler(Plugin, page, PER_PAGE).run()
        return jsonify(**res), exitcode

    @redapiBP.route('/redapi/suites')
    @redapiBP.route('/redapi/suites/<int:page>')
    def getSuitesList(page=1):
        res, exitcode = apiListCallHandler(Suite, page, PER_PAGE).run()
        return jsonify(**res), exitcode

    @redapiBP.route('/redapi/subnets')
    @redapiBP.route('/redapi/subnets/<int:page>')
    def getSubnetsList(page=1):
        res, exitcode = apiListCallHandler(Subnet, page, PER_PAGE).run()
        return jsonify(**res), exitcode

    @redapiBP.route('/redapi/hosts')
    @redapiBP.route('/redapi/hosts/<int:page>')
    def getHostsList(page=1):
        res, exitcode = apiListCallHandler(Host, page, PER_PAGE).run()
        return jsonify(**res), exitcode

    ############################################################################

    @redapiBP.route('/redapi/host', methods=['GET','POST','PUT','DELETE'])
    def singleHostOps():
        """
        Api to handle single host.
        Available methods = GET, POST, PUT, DELETE
        ---
        GET
        /redapi/host?ipaddress=<ip>
        get all the info for single host
        ---
        POST
        /redapi/host?ipaddress=<ip>&hostname=<hostname>&suite=<suitename>&subnet=<subnetname>
        ---
        PUT
        /redapi/host?ipaddress=<ip>&maintenance=<on|off>
        manage maintenance mode for host

        """
        handler = apiSingleCallHandler(method=request.method,
                                       dbmodel=Host,
                                       params=request.args)
        res, exitcode = handler.run()
        return jsonify(**res), exitcode

    ############################################################################

    @redapiBP.route('/redapi/plugin', methods=['GET','POST','PUT','DELETE'])
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
        handler = apiSingleCallHandler(method=request.method,
                                       dbmodel=Plugin,
                                       params=request.args,
                                       scheduler=scheduler)
        res, exitcode = handler.run()
        return jsonify(**res), exitcode

    ############################################################################

    @redapiBP.route('/redapi/suite', methods=['GET','POST','PUT','DELETE'])
    def singleSuiteOps():
        """
        Api to handle single suite.
        Available methods = GET, POST, PUT, DELETE
        ---
        GET
        /redapi/suite
        get all the params for single suite
        ---
        POST
        /redapi/suite
        create new suite
        ---
        PUT
        /redapi/suite
        modify configuration of existing plugin
        ---
        DELETE
        /redapi/suite
        delete single suite from DB

        """
        handler = apiSingleCallHandler(method=request.method,
                                       dbmodel=Suite,
                                       params=request.args)
        res, exitcode = handler.run()
        return jsonify(**res), exitcode

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
