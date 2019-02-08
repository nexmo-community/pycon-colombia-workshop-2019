import os
import json
import tornado.ioloop
import tornado.web
from tornado import escape
from tornado.escape import utf8
from logzero import logfile, logger

logfile("/tmp/pycon-colombia-workshop.log", maxBytes=1e6, backupCount=3)


class VAPIServer(tornado.web.RequestHandler):
    def write(self, chunk):
        chunk = escape.json_encode(chunk)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        chunk = utf8(chunk)
        self._write_buffer.append(chunk)

    def get(self):
        to = self.get_argument("to", None, True)
        logger.info(f"NCCO fetched for call to {to}")
        self.write(
            [
                {
                    "action": "stream",
                    "streamUrl": [
                        f"{os.environ['SERVER_URL']}/static/British-calls-recorded.mp3"
                    ],
                },
                {
                    "action": "record",
                    "eventUrl": [f"{os.environ['SERVER_URL']}/recordings"],
                },
                {
                    "action": "connect",
                    "eventUrl": [f"{os.environ['SERVER_URL']}"],
                    "from": os.environ["NEXMO_VIRTUAL_NUMBER"],
                    "endpoint": [
                        {
                            "type": "websocket",
                            "uri": f"{os.environ['SERVER_URL']}/inbound-call-socket",
                            "content-type": "audio/l16;rate=16000",
                            "headers": {},
                        }
                    ],
                },
            ]
        )

    def post(self):
        event = json.loads(self.request.body)
        logger.info(f"Call to {event['to']} status: {event['status']}")
        self.write([{"status": "ok"}])


class RecordingsServer(tornado.web.RequestHandler):
    def post(self):
        recording_meta = json.loads(self.request.body)
        logger.info(
            f"New recording available for {recording_meta['conversation_uuid']}"
        )
        self.write("OK")


def make_app():
    return tornado.web.Application(
        [
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "app/static"}),
            (r"/", VAPIServer),
            (r"/recordings", RecordingsServer),
        ]
    )


if __name__ == "__main__":
    app = make_app()
    app.listen(8000)
    tornado.ioloop.IOLoop.current().start()
