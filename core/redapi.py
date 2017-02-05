import sys
from flask import Blueprint, abort, jsonify, request, url_for

from mq import MQ
from tools import Message, getListOfIPs
from models import Host, Subnet, Plugin, History, Suite, Status
from apitools import apiSingleCallHandler, apiListCallHandler,\
                     apiMonitoringHandler

PER_PAGE = 10

def initRedApiBP(scheduler):
    redapiBP = Blueprint('redapi_blueprint', __name__)
    statRRDFile = 'common_statistics.rrd'
    apiMQ = MQ(scheduler.config.queue)
    redApiOutChannel = apiMQ.initOutRabbitPyChannel()

    @redapiBP.route('/redapi/monitoring')
    def getMonitoring():
        try:
            res, exitcode = apiMonitoringHandler(request.args,
                                                 apiMQ.getWorkersList,
                                                 statRRDFile).run()
        except Exception as e:
            res = dict(message=e.message)
            exitcode = 400
        return jsonify(**res), exitcode

    @redapiBP.route('/redapi/workers')
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

    @redapiBP.route('/redapi/subnet', methods=['GET','POST','PUT','DELETE'])
    def singleSubnetOps():
        """
        """
        handler = apiSingleCallHandler(method=request.method,
                                       dbmodel=Subnet,
                                       params=request.args)
        res, exitcode = handler.run()
        return jsonify(**res), exitcode

    ############################################################################

    @redapiBP.route('/redapi/scheduler')
    def getSchedulerJobs():
        jobs = scheduler.get_jobs()
        jobs_list = map(lambda j: dict(name=j.name, id=j.id,
                                       next_run_time=j.next_run_time), jobs)
        return jsonify(*jobs_list)

    ############################################################################

    @redapiBP.route('/redapi/discovery', methods=['GET'])
    def runDiscovery():
        subnet = request.args.get('subnet')
        if subnet:
            res, exitcode = performDiscovery(subnet)
        else:
            res = dict(message='Subnet parameter is not found'.\
                       format(operation))
            exitcode = 404
        return jsonify(**res), exitcode

    def performDiscovery(subnetname):
        subnet = Subnet.query.filter_by(name=subnetname).first()
        if subnet:
            ipaddresses = getListOfIPs(subnet.subnet, subnet.netmask)
            for ipaddress in ipaddresses:
                discoveryJob = Message(subnet=subnet)
                discoveryJob.ipaddress = str(ipaddress)
                discoveryJob.action = 'discovery'
                discoveryJob.type = 'task'
                apiMQ.sendM(redApiOutChannel, discoveryJob.tojson())
            res = dict(message='Discovery request for {} was sent to clients'.\
                       format(subnetname))
            exitcode = 200
        else:
            res = dict(message='Discovery cancelled - {} not found in db'.\
                       format(subnetname))
            exitcode = 404
        return res, exitcode

    return redapiBP

"""
@BlueApp.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
"""
