"""ppmanager - tool for managing ppalette daemons

Usage:
  ppmanager.py start (red|violet|grey) [--debug]
  ppmanager.py (stop|restart|status) (red|violet|grey)
  ppmanager.py init_db --confirm

Options:
  -h --help     Show this screen
"""
import sys
import logging
from docopt import docopt
from core.tools import getPidPath, getApiServerType
from core.daemons import violetServer, greyServer, redServerWerkzeug,\
                         startViolet, startGrey
from core.database import init_db

apiServer = getApiServerType()

if apiServer == 'tornado':
    try:
        from tornado import version
        from core.daemons import redServerTornado as redServer
        from core.daemons import startRedTornado as startRed
    except ImportError:
        print 'WARNING: Config is set to tornado, but tornado seems not'
        print 'to be installed. Will use werkzeug for red.'
        from core.daemons import redServerWerkzeug as redServer
        from core.daemons import startRedWerkzeug as startRed
else:
    if apiServer != 'werkzeug':
        print 'WARNING: not able to process value for API server type'
        print 'tornado and werkzeug are supported'
        print 'Selecting werkzeug as default for red service'
    from core.daemons import redServerWerkzeug as redServer
    from core.daemons import startRedWerkzeug as startRed

LOGLEVEL = "INFO"
logging.basicConfig(stream=sys.stderr,
                    level=getattr(logging, LOGLEVEL))

services = {
    'red' : redServer,
    'violet' : violetServer,
    'grey' : greyServer
    }

# 'all' : ['red', 'violet', 'grey']
services_debug = {
    'red' : startRed,
    'violet' : startViolet,
    'grey' : startGrey
    }

operations = ['start', 'stop', 'restart', 'status']

extra = {
    'init_db' : [init_db, dict(create_tables=True)]
    }

def getInsertedValue(options, arguments):
    for item in options:
        if arguments.get(item):
            if item == 'status':
                item = 'is_running'
            return item
    return None

def startDaemon(service, operation, services):
    print 'Executing {} {}...'.format(operation, service)
    server = services[service]('{0}/{1}.pid'.format(getPidPath(), service))
    getattr(server, operation)()

if __name__ == '__main__':
    arguments = docopt(__doc__, version='ppmanager 0.0.1')
    logging.debug(arguments)
    DEBUG = True if arguments.get('--debug') else False

    if DEBUG:
        service = getInsertedValue(services_debug.keys(), arguments)
    else:
        service = getInsertedValue(services.keys(), arguments)

    if service:
        operation = getInsertedValue(operations, arguments)
        if not DEBUG:
            startDaemon(service, operation, services)
        else:
            if operation == 'start':
                services_debug.get(service)()

    else:
        extraOp = getInsertedValue(extra.keys(), arguments)
        if extraOp:
            commandList = extra.get(extraOp)
            commandList[0](**commandList[1])
