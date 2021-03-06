from sqlalchemy.orm import contains_eager
from sqlalchemy.exc import IntegrityError

from tools import validateIP, validateNetwork, resolveIP, validateInt,\
                  validatePage, getPluginModule
from models import Host, Subnet, Plugin, History, Suite, Status
from core.database import db_session
from configs import cConfig, rLogger

monit = getPluginModule(cConfig.mon_engine,
                        cConfig.mon_plugin_path,
                        rLogger)

STATUS_OK = 0
STATUS_WARNING = 1
STATUS_ERROR = 2
VIOLET = 'violet'
COMMON = 'common'


def apiValidateMandParam(option, params):
    value = params.get(option)
    if not value:
        raise ValueError("Mandatory arg {} is not set".format(option))
    return value

def apiValidateIntegerParam(option, params):
    value = params.get(option)
    if value:
        validateInt(value)
    return value

def apiValidateTriggerParam(option, params):
    value = params.get(option)
    if value:
        if value == "on":
            res = True
        elif value == "off":
            res = False
        else:
            raise ValueError("{} trigger is incorrect".format(option))
    else:
        res = None
    return res

def apiValidateIpParam(option, params):
    value = params.get(option)
    if not validateIP(value):
        raise ValueError("Failed to validate IP {}".format(value))
    return value

class apiSingleCallHandler(object):
    ID_MAPPER = {
        'Host' : 'ipaddress',
        'Plugin' : 'customname',
        'Suite' : 'name',
        'Subnet' : 'name'
        }
    def __init__(self, method, dbmodel, params, scheduled=False):
        CHECK_MAPPER = {
            'Host' : self.parseParamsForHost,
            'Plugin' : self.parseParamsForPlugin,
            'Suite' : self.parseParamsForSuite,
            'Subnet' : self.parseParamsForSubnet
            }
        REQUEST_MAPPER = {
            'GET' : self.apiCommonGetRequest,
            'POST' : self.apiCommonPostRequest,
            'PUT' : self.apiCommonPutRequest,
            'DELETE' : self.apiCommonDeleteRequest
        }
        self.dbmodel = dbmodel
        self.params = params
        self.modelname = dbmodel.__name__
        self.edit = True if method == 'PUT' else False
        self.identificator = self.ID_MAPPER.get(self.modelname)
        self.checker = CHECK_MAPPER.get(self.modelname)
        self.handler = REQUEST_MAPPER.get(method)
        self.scheduled = scheduled

    def run(self):
        return self.handler()

    def apiCommonGetRequest(self):
        try:
            value = apiValidateMandParam(self.identificator, self.params)
        except ValueError as ve:
            return (dict(message=ve.message), 400)
        record = db_session.query(self.dbmodel).\
                    filter(getattr(self.dbmodel,
                                   self.identificator) == value).first()
        if not record:
            res = dict(message='{0} {1} not found'.\
                       format(self.modelname, value))
            exitcode = 404
        else:
            res = record.APIGetDict(short=False)
            exitcode = 200
        return (res, exitcode)

    def apiCommonPostRequest(self):
        try:
            params_checked = self.checker()
        except ValueError as ve:
            return (dict(message=ve.message), 400)
        newRecord = self.dbmodel(**params_checked)
        db_session.add(newRecord)
        try:
            db_session.commit()
            res = dict(message='{} successfully added'.\
                       format(self.modelname))
            exitcode = 200
        except IntegrityError as e:
            db_session.rollback()
            res = dict(message=e.message)
            exitcode = 501
        return (res, exitcode)

    def apiCommonPutRequest(self):
        try:
            value = apiValidateMandParam(self.identificator, self.params)
        except ValueError as ve:
            return (dict(message=ve.message), 400)
        record = db_session.query(self.dbmodel).\
                    filter(getattr(self.dbmodel,
                                   self.identificator) == value).first()
        if not record:
            res = dict(message='{0} {1} not found'.\
                       format(self.modelname, value))
            exitcode = 404
        else:
            try:
                params_checked = self.checker()
            except ValueError as ve:
                res = dict(message=ve.message)
                return (res, 400)
            record.updateParams(**params_checked)
            if self.scheduled:
                record.markForUpdate()
            db_session.add(record)
            try:
                db_session.commit()
                res = dict(message='{0} {1} was updated'.\
                           format(self.modelname, value))
                exitcode = 200
            except Exception as e:
                res = dict(message=e.message)
                exitcode = 501
        return (res, exitcode)

    def apiCommonDeleteRequest(self):
        try:
            value = apiValidateMandParam(self.identificator, self.params)
        except ValueError as ve:
            return (dict(message=ve.message), 400)
        record = db_session.query(self.dbmodel).\
                    filter(getattr(self.dbmodel,
                                   self.identificator) == value).first()
        if not record:
            res = dict(message='{0} {1} not found'.format(self.modelname,
                                                          value))
            exitcode = 404
        else:
            try:
                if self.scheduled:
                    record.markForDelete()
                    message = "{0} {1} marked for "\
                              "deletion".format(self.modelname,
                                                value)
                else:
                    db_session.delete(record)
                    message = '{0} {1} was deleted'.format(self.modelname,
                                                           value)
                db_session.commit()
                res = dict(message=message)
                exitcode = 200
            except Exception as e:
                res = dict(message=e.message)
                exitcode = 501
        return (res, exitcode)

    def parseParamsForPlugin(self):
        res = dict()
        if not self.edit:
            customname = apiValidateMandParam(self.identificator,
                                              self.params)
            script = apiValidateMandParam('script', self.params)
            res.update(customname=customname, script=script)
        else:
            script = self.params.get('script')
            res.update(script=script)
        res.update(interval=apiValidateIntegerParam('interval', self.params))
        res.update(params=self.params.get('params'))
        res.update(ssh_wrapper=apiValidateTriggerParam('ssh_wrapper',
                                                       self.params))
        suites = self.params.getlist('suite')
        res.update(suites=self.genRecList(suites, Suite) if suites else None)
        return res

    def parseParamsForSuite(self):
        res = dict()
        name = apiValidateMandParam(self.identificator, self.params)
        if not self.edit:
            res.update(name=name)
        ips = self.params.getlist('ipaddress')
        subnets = self.params.getlist('subnetname')
        plugins = self.params.getlist('plugin')
        res.update(hosts=self.genRecList(ips, Host) if ips else None)
        res.update(plugins=self.genRecList(plugins,Plugin) if plugins else None)
        res.update(subnets=self.genRecList(subnets, Subnet) \
                   if subnets else None)
        return res

    def parseParamsForHost(self):
        res = dict()
        if not self.edit:
            ip = apiValidateMandParam(self.identificator, self.params)
            if not validateIP(ip):
                raise ValueError("Failed to validate IP {}".format(ip))
            res.update(ip=ip)
            res.update(hostname=self.params.get('hostname') or resolveIP(ip))
        else:
            res.update(maintenance=apiValidateTriggerParam('maintenance',
                                                           self.params))
            res.update(hostname=self.params.get('hostname'))
        suite = self.params.get('suite')
        if suite:
            suiteDB = Suite.query.filter(Suite.name == suite).first()
            if not suiteDB:
                raise ValueError("Suite {} was not found in DB".format(suite))
            else:
                res.update(suite_id=suiteDB.id)
        subnet = self.params.get('subnet')
        if subnet:
            subnetDB = Subnet.query.filter(Subnet.name == subnet).first()
            if not subnetDB:
                raise ValueError("Subnet {} was not found in DB".format(subnet))
            else:
                res.update(subnetID=subnetDB.id)
                if not res.get('suite_id'):
                    res.update(suite_id=subnetDB.suite.id)
        res.update(enablehistory=apiValidateTriggerParam('history',
                                                         self.params))
        res.update(login=self.params.get('login'))
        return res

    def parseParamsForSubnet(self):
        res = dict()
        if not self.edit:
            res.update(name=apiValidateMandParam(self.identificator,
                                                 self.params))
        subnet = apiValidateMandParam('subnet', self.params)
        netmask = apiValidateMandParam('netmask', self.params)
        if validateNetwork(subnet, netmask):
            res.update(subnet=subnet, netmask=netmask)
        else:
            raise ValueError("Wrong subnet/netmask {0}/{1}".format(subnet,
                                                                   netmask))
        suite = self.params.get('suite')
        if suite:
            suiteDB = Suite.query.filter(Suite.name == suite).first()
            if suiteDB:
                res.update(suite_id=suiteDB.id)
            else:
                raise ValueError("Suite {} not found in db".format(suite))
        res.update(auto_discovery=apiValidateTriggerParam('autodisc',
                                                         self.params))
        res.update(interval=apiValidateIntegerParam('interval',
                                                              self.params))
        return res

    def genRecList(self, IDs, dbmodel):
        res = list()
        modelname = dbmodel.__name__
        if ',' in IDs[0]:
            IDs = IDs[0].split(',')
        for value in IDs:
            record = db_session.query(dbmodel).\
                        filter(getattr(dbmodel,
                                       self.ID_MAPPER.\
                                            get(modelname)) == value).first()
            if not record:
                raise ValueError('Failed to add to {0} {1}: {2} is not in DB'.\
                                 format(modelname, value, modelname))
            else:
                res.append(record)
        return res

class apiListCallHandler(object):
    def __init__(self, dbmodel, page, perpage, pluginType=None):
        self.dbmodel = dbmodel
        self.page = page
        self.perpage = perpage
        self.pluginType = pluginType

    def run(self):
        try:
            validatePage(self.page)
        except ValueError as ve:
            fullres = dict(message=ve.message)
            exitcode = 400
        else:
            if not self.pluginType:
                model_query = db_session.query(self.dbmodel)
            else:
                try:
                    model_query = self.getStatusQuery(self.pluginType)
                except ValueError as ve:
                    fullres = dict(message=ve.message)
                    exitcode = 400
                    return (fullres, exitcode)
            objects, total, total_pages = self.paginationQuery(model_query)
            res = [obj.APIGetDict(short=False) for obj in objects]
            if not res:
                fullres = dict(message='Wrong page number or missing data')
                exitcode = 400
            else:
                fullres = dict(objects=res, total_objects=total,
                               total_pages=total_pages,
                               page=self.page, per_page=self.perpage)
                exitcode = 200
        return (fullres, exitcode)

    def getStatusQuery(self, pluginType):
        if pluginType == "all":
            st_query = db_session.query(Host)
        elif pluginType == "error":
            st_query = self.generateHostStatsQuery(STATUS_ERROR)
        elif pluginType == "warn":
            st_query = self.generateHostStatsQuery(STATUS_WARNING)
        elif pluginType == "ok":
            st_query = self.generateHostStatsQuery(STATUS_OK)
        else:
            raise ValueError('Plugin type is not in (all,error,warn,ok)')
        return st_query

    def generateHostStatsQuery(self, exitcode):
        return db_session.query(Host).join(Host.stats).\
                options(contains_eager(Host.stats)).\
                filter(Status.last_exitcode == exitcode)

    def paginationQuery(self, query):
        items = query.limit(self.perpage).\
                      offset((self.page-1) * self.perpage).all()
        if self.page == 1 and len(items) < self.perpage:
            total = len(items)
            total_pages = 1
        else:
            total = query.order_by(None).count()
            total_pages = total / self.perpage
            if total % self.perpage:
                total_pages += 1
        return (items, total, total_pages)

class apiMonitoringHandler(object):
    def __init__(self, args, getWorkersMethod):
        self.monType = args.get('type')
        if self.monType in ('violet', 'violets'):
            self.workers = getWorkersMethod()
        if self.monType == ('violet'):
            self.violet_id = apiValidateMandParam('violet_id', args)
            self.vconn = True if self.violet_id in self.workers.keys() \
                              else False
        self.period = args.get('period') or 'all'

    def run(self):
        if self.monType == 'common':
            res, exitcode = self.getCommonStats()
        elif self.monType == 'violets':
            res, exitcode = self.getAllVioletsStats()
        elif self.monType == 'violet':
            res, exitcode = self.getSingleVioletStats()
        else:
            res = dict(message='Invalid argument for monitoring - {}!'.\
                       format(self.monType))
            exitcode = 400
        return res, exitcode

    def getAllVioletsStats(self):
        res, exitcode = (dict(), 200)
        if any(self.workers):
            for key in self.workers.keys():
                try:
                    res[key] = self.fetchSingleVioletStats(key, self.period)
                except Exception as e:
                    res = dict(message='api command failed: {}'.format(e))
                    exitcode = 501
        return res, exitcode

    def getCommonStats(self):
        res = monit.Monitor().getChartData(hours=1, grades=60)\
            if self.period == 'all'\
            else monit.Monitor().getLatestUpdate()
        exitcode = 200
        return res, exitcode

    def getSingleVioletStats(self):
        try:
            res = self.fetchSingleVioletStats(self.violet_id, self.period)
            res.update(connected=self.vconn)
            exitcode = 200
        except Exception as e:
            if 'No such file or directory' in e.args[0]:
                message = 'No statistics found for {}'.format(self.violet_id)
            else:
                message = e
            res = dict(message=message)
            exitcode = 400
        return res, exitcode

    def fetchSingleVioletStats(self, violet_id, period):
        monitor = monit.Monitor(violet_id)
        return monitor.getChartData(hours=1, grades=60)\
              if period == 'all'\
              else monitor.getLatestUpdate()
