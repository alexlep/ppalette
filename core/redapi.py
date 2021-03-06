from flask import Blueprint, jsonify, request

from mq import MQ
from tools import Message, prepareDiscoveryMessages
from models import Host, Subnet, Plugin, History, Suite, Status
from database import db_session
from apitools import apiSingleCallHandler, apiListCallHandler,\
                     apiMonitoringHandler
import pvars as pv
from configs import rConfig

PER_PAGE = 10

def initRedApiBP(scheduler):
    redapiBP = Blueprint('redapi_blueprint', __name__)
    apiMQ = MQ(rConfig.queue)

    @redapiBP.route(pv.MONITORING)
    def getMonitoring():
        try:
            res, exitcode = apiMonitoringHandler(request.form,
                                                 apiMQ.getWorkersList).run()
        except Exception as e:
            res = dict(message=e.message)
            exitcode = 400
        return jsonify(**res), exitcode

    @redapiBP.route(pv.WORKERS)
    def getWorkersListJson():
        try:
            res = apiMQ.getWorkersList()
            exitcode = 200
        except Exception as e:
            res = dict(message="Unable to connect to RMQ monitoring - {}!".\
                  format(e))
            exitcode = 501
        return jsonify(**res), exitcode

    ############################################################################
    @redapiBP.route(pv.STATUS)
    @redapiBP.route(pv.STATUS + '/<pluginType>')
    @redapiBP.route(pv.STATUS + '/<pluginType>/<int:page>')
    def getPluginStatus(pluginType='all', page=1):
        res, exitcode = apiListCallHandler(Host, page, PER_PAGE,
                                           pluginType).run()
        return jsonify(**res), exitcode

    @redapiBP.route(pv.PLUGINS)
    @redapiBP.route(pv.PLUGINS + '/<int:page>')
    def getPluginsList(page=1):
        res, exitcode = apiListCallHandler(Plugin, page, PER_PAGE).run()
        return jsonify(**res), exitcode

    @redapiBP.route(pv.SUITES)
    @redapiBP.route(pv.SUITES + '/<int:page>')
    def getSuitesList(page=1):
        res, exitcode = apiListCallHandler(Suite, page, PER_PAGE).run()
        return jsonify(**res), exitcode

    @redapiBP.route(pv.SUBNETS)
    @redapiBP.route(pv.SUBNETS + '/<int:page>')
    def getSubnetsList(page=1):
        res, exitcode = apiListCallHandler(Subnet, page, PER_PAGE).run()
        return jsonify(**res), exitcode

    @redapiBP.route(pv.HOSTS)
    @redapiBP.route(pv.HOSTS + '/<int:page>')
    def getHostsList(page=1):
        res, exitcode = apiListCallHandler(Host, page, PER_PAGE).run()
        return jsonify(**res), exitcode

    ############################################################################

    @redapiBP.route(pv.HOST, methods=['GET','POST','PUT','DELETE'])
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
                                       params=request.form)
        res, exitcode = handler.run()
        return jsonify(**res), exitcode

    ############################################################################

    @redapiBP.route(pv.PLUGIN, methods=['GET','POST','PUT','DELETE'])
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
                                       params=request.form,
                                       scheduled=True)
        res, exitcode = handler.run()
        return jsonify(**res), exitcode

    ############################################################################

    @redapiBP.route(pv.SUITE, methods=['GET','POST','PUT','DELETE'])
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
                                       params=request.form)
        res, exitcode = handler.run()
        return jsonify(**res), exitcode

    ############################################################################

    @redapiBP.route(pv.SUBNET, methods=['GET','POST','PUT','DELETE'])
    def singleSubnetOps():
        """
        """
        handler = apiSingleCallHandler(method=request.method,
                                       dbmodel=Subnet,
                                       params=request.form,
                                       scheduled=True)
        res, exitcode = handler.run()
        return jsonify(**res), exitcode

    ############################################################################

    @redapiBP.route(pv.SCHEDULER)
    def getSchedulerJobs():
        jobs = scheduler.get_jobs()
        jobs_list = map(lambda j: dict(name=j.name, id=j.id,
                                       next_run_time=j.next_run_time), jobs)
        return jsonify(*jobs_list)

    ############################################################################

    @redapiBP.route(pv.SINGLE, methods=['GET'])
    def runSingleCheck():
        pluginName = request.form.get('plugin')
        hostIP = request.form.get('hostip')
        res, exitcode = scheduler.pushSingleCheck(pluginName, hostIP)
        return jsonify(**res), exitcode

    @redapiBP.route(pv.DISCOVERY, methods=['GET'])
    def runDiscovery():
        subnetname = request.form.get('subnet')
        res, exitcode = scheduler.sendDiscoveryFromAPI(subnetname)
        return jsonify(**res), exitcode

    return redapiBP

"""
@BlueApp.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
"""
