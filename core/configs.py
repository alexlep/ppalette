import sys
from pvars import violetConfigFile, redConfigFile, greyConfigFile,\
                  commonConfigFile
from tools import parseConfig, initLogging

vConfig = parseConfig(violetConfigFile)
vLogger = initLogging(vConfig.log, 'violet')

rConfig = parseConfig(redConfigFile)
rLogger = initLogging(rConfig.log, 'red')

gConfig = parseConfig(greyConfigFile)
gLogger = initLogging(gConfig.log, 'grey')

cConfig = parseConfig(commonConfigFile)
