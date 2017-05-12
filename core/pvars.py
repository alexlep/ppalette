import os

#workingDir = os.path.dirname(os.path.abspath(__file__))
workingDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
configDir = workingDir + '/config'
redConfigFile = configDir + '/red_config.json'
greyConfigFile = configDir + '/grey_config.json'
violetConfigFile = configDir + '/violet_config.json'
commonConfigFile = configDir + '/common.json'

#
prefix = '/redapi'
HOST = prefix + '/host'
HOSTS = prefix + '/hosts'
PLUGIN = prefix + '/plugin'
PLUGINS = prefix + '/plugins'
SUITE = prefix + '/suite'
SUITES = prefix + '/suites'
SUBNET = prefix + '/subnet'
SUBNETS = prefix + '/subnets'
STATUS = prefix + '/status'
DISCOVERY = prefix + '/discovery'
SCHEDULER = prefix + '/scheduler'
WORKERS = prefix + '/workers'
MONITORING = prefix + '/monitoring'
SINGLE = prefix + '/singlecheck'

#
defTimeFormat = "%H:%M:%S:%d:%m:%Y"
