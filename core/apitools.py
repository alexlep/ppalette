from tools import validateIP, resolveIP
from models import Host, Subnet, Plugin, History, Suite, Status
from core.database import db_session

def apiValidateMandParam(option, params):
    value = params.get(option)
    if not value:
        raise ValueError("{} is not set".format(option))
    return value

def apiValidateIntegerParam(option, params):
    value = params.get(option)
    if value:
        try:
            int(value)
        except:
            raise ValueError("{} value is incorrect".format(option))
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
            'Subnet' : self.parseParamsForSuite
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
        ipsDB = pluginsDB = subnetsDB = None
        name = apiValidateMandParam(self.identificator, self.params)
        subnets = self.params.getlist('subnetname')
        ips = self.params.getlist('ipaddress')
        plugins = self.params.getlist('pluginname')
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
            ip = apiValidateIpParam(self.identificator, self.params)
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
