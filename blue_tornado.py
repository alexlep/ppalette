from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import bluered

port = 5000

if __name__ =='__main__':
    http_server = HTTPServer(WSGIContainer(bluered.BlueApp))
    http_server.listen(port)
    print "Listening on port {0}...".format(port)
    try:
        IOLoop.instance().start()
    except KeyboardInterrupt as ki:
        print "Interrupting blue tornado (KeyboardInterrupt received)..."
        IOLoop.instance().stop()
        print "Done."
