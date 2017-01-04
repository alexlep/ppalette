from tools import validateIP, resolveIP

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
