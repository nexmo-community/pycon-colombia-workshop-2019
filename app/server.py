import tornado.ioloop
import tornado.web
from tornado import escape
from tornado.escape import utf8
from logzero import logfile, logger

logfile("/tmp/pycon-colombia-workshop.log", maxBytes=1e6, backupCount=3)


class NCCOHandler(tornado.web.RequestHandler):
    def write(self, chunk):
        chunk = escape.json_encode(chunk)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        chunk = utf8(chunk)
        self._write_buffer.append(chunk)

    def get(self):
        logger.info("Call received")
        self.write([{"action": "talk", "text": "Hello PyCon"}])


def make_app():
    return tornado.web.Application([(r"/ncco", NCCOHandler)])


if __name__ == "__main__":
    app = make_app()
    app.listen(8000)
    tornado.ioloop.IOLoop.current().start()
