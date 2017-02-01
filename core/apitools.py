from sqlalchemy.orm import contains_eager
from sqlalchemy.exc import IntegrityError
from tools import validateIP, resolveIP, validateInt, validatePage
from models import Host, Subnet, Plugin, History, Suite, Status
from core.database import db_session

STATUS_OK = 0
STATUS_WARNING = 1
STATUS_ERROR = 2

def apiValidateMandParam(option, params):
    value = params.get(option)
    if not value:
        raise ValueError("{} is not set".format(option))
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
    def __init__(self, method, dbmodel, params, scheduler=None):
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
        self.scheduler = scheduler
        self.identificator = self.ID_MAPPER.get(self.modelname)
        self.checker = CHECK_MAPPER.get(self.modelname)
        self.handler = REQUEST_MAPPER.get(method)

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
        newRecord = self.dbmodel(*params_checked)
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
        # object related hooks
        if self.scheduler:
            if exitcode == 200:
                self.scheduler.registerJob(newRecord)
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
            record.updateParams(*params_checked)
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
                db_session.delete(record)
                db_session.commit()
                res = dict(message='{0} {1} was deleted'.\
                           format(self.modelname, value))
                exitcode = 200
            except Exception as e:
                res = dict(message=e.message)
                exitcode = 501
        # object related hooks
        if self.scheduler:
            if exitcode == 200:
                self.scheduler.remove_job(record.pluginUUID)
        return (res, exitcode)

    def parseParamsForPlugin(self):
        suiteDB = None
        if not self.edit:
            customname = apiValidateMandParam(self.identificator,
                                              self.params)
            script = apiValidateMandParam('script', self.params)
        else:
            script = self.params.get('script')
        interval = apiValidateIntegerParam('interval', self.params)
        script_params = self.params.get('params')
        ssh_wrapper = apiValidateTriggerParam('ssh_wrapper', self.params)
        suites = self.params.getlist('suite')
        suitesDB = self.genRecList(suites, Suite) if suites else None
        if not self.edit:
            res = (script, customname, interval, script_params, ssh_wrapper,
                   suiteDB)
        else:
            res = (script, interval, script_params, ssh_wrapper, suitesDB)
        return res

    def parseParamsForSuite(self):
        name = apiValidateMandParam(self.identificator, self.params)
        subnets = self.params.getlist('subnetname')
        ips = self.params.getlist('ipaddress')
        plugins = self.params.getlist('plugin')
        ipsDB = self.genRecList(ips, Host) if ips else None
        pluginsDB = self.genRecList(plugins, Plugin) if plugins \
                                                          else None
        subnetsDB = self.genRecList(subnets, Subnet) if subnets \
                                                          else None
        if not self.edit:
            res = (name, ipsDB, pluginsDB, subnetsDB)
        else:
            res = (ipsDB, pluginsDB, subnetsDB)
        return res

    def parseParamsForHost(self):
        suiteID = subnetID = None
        if not self.edit:
            ip = apiValidateMandParam(self.identificator, self.params)
            if not validateIP(ip):
                raise ValueError("Failed to validate subnet!")
        suite = self.params.get('suite')
        if suite:
            suiteDB = Suite.query.filter(Suite.name == suite).first()
            if not suiteDB:
                raise ValueError("Provided suite was not found in DB")
            else:
                suiteID = suiteDB.id
        subnet = self.params.get('subnet')
        if subnet:
            subnetDB = Subnet.query.filter(Subnet.name == subnet).first()
            if not subnetDB:
                raise ValueError("Provided subnet was not found in DB")
            else:
                if not suite:
                    suiteID = subnetDB.suite.id
                subnetID = subnetDB.id
        login = self.params.get('login')
        if not self.edit:
            hostname = self.params.get('hostname') or resolveIP(ip)
            res = (ip, suiteID, subnetID, hostname, login)
        else:
            maintenance = apiValidateTriggerParam('maintenance', self.params)
            hostname = self.params.get('hostname')
            res = (suiteID, subnetID, hostname, login, maintenance)
        return res

    def parseParamsForSubnet(self):
        suiteID = None
        name = apiValidateMandParam(self.identificator, self.params)
        subnet = apiValidateMandParam('subnet', self.params)
        netmask = apiValidateMandParam('netmask', self.params)
        if not validateIP(subnet):
            raise ValueError("Failed to validate subnet!")
        if not validateIP(netmask):
            raise ValueError("Failed to validate netmask!")
        suite = self.params.get('suite')
        if suite:
            suiteDB = Suite.query.filter(Suite.name == suite).first()
            if not suiteDB:
                raise ValueError("Suite {} not found in db".format(suite))
            else:
                suiteID = suiteDB.id
        res = (name, subnet, netmask, suiteID)
        return res

    def genRecList(self, IDs, dbmodel):
        res = list()
        modelname = dbmodel.__name__
        for value in IDs:
            record = db_session.query(dbmodel).\
                        filter(getattr(dbmodel,
                                       self.ID_MAPPER.\
                                            get(modelname)) == value).first()
            if not record:
                raise ValueError('Failed to add {0} {1}: {2} is not in DB'.\
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
