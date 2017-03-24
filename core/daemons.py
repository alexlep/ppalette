from py_daemon.py_daemon import Daemon

def prepareRed():
    from flask import Flask
    from redapi import initRedApiBP
    from pscheduler import Scheduler
    from pvars import redConfigFile

    RedScheduler = Scheduler(redConfigFile)
    RedScheduler.start()

    RedApi = Flask (__name__)
    RedApi.register_blueprint(initRedApiBP(RedScheduler))
    host, port = RedScheduler.getApiHostPortConfig()

    RedApi.secret_key="my_favourite_secret_key_here"
    return (RedApi, host, port)

def startRedTornado():
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    RedApi, host, port = prepareRed()

    http_server = HTTPServer(WSGIContainer(RedApi))
    http_server.listen(port)
    try:
        IOLoop.instance().start()
    except KeyboardInterrupt as ki:
        print "Interrupting blue tornado (KeyboardInterrupt received)..."
        IOLoop.instance().stop()
        print "Done."

def startRedWerkzeug():
    RedApi, host, port = prepareRed()
    RedApi.run(debug=False, host=host, port=port, threaded=True)

def startViolet():
    import signal
    from violet import Violet
    from pvars import violetConfigFile

    VioletApp = Violet(violetConfigFile)
    signal.signal(signal.SIGINT, VioletApp)
    VioletApp.startProcesses()

def startGrey():
    from grey import Grey, db_session
    from pvars import greyConfigFile

    GreyApp = Grey(greyConfigFile)
    try:
        GreyApp.startConsumer()
    except KeyboardInterrupt:
        print ("ABORTING GREY LISTENER")
        db_session.close()

class redServerTornado(Daemon):
    def run(self):
        startRedTornado()

class redServerWerkzeug(Daemon):
    def run(self):
        startRedWerkzeug()

class violetServer(Daemon):
    def run(self):
        startViolet()

class greyServer(Daemon):
    def run(self):
        startGrey()
