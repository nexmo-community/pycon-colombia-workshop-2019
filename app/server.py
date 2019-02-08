import os
import json
import requests
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
from tornado import gen
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
                }
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


class InboundCallHandler(tornado.websocket.WebSocketHandler):

    connections = []

    def initialize(self, **kwargs):
        self.transcriber = tornado.websocket.websocket_connect(
            f"wss://stream.watsonplatform.net/speech-to-text/api/v1/recognize?watson-token={self.transcriber_token}&model=en-UK_NarrowbandModel",
            on_message_callback=self.on_transcriber_message,
        )

    @property
    def transcriber_token(self):
        resp = requests.get(
            "https://stream.watsonplatform.net/authorization/api/v1/token",
            auth=(
                os.environ["WATSON_TRANSCRIPTION_USERNAME"],
                os.environ["WATSON_TRANSCRIPTION_PASSWORD"],
            ),
            params={"url": "https://stream.watsonplatform.net/speech-to-text/api"},
        )
        return resp.content.decode("utf-8")

    def on_transcriber_message(self, message):
        if message:
            message = json.loads(message)
            if "results" in message:
                transcript = message["results"][0]["alternatives"][0]["transcript"]
                logger.info(transcript)

    @gen.coroutine
    def on_message(self, message):
        transcriber = yield self.transcriber

        if type(message) != str:
            transcriber.write_message(message, binary=True)
        else:
            data = json.loads(message)
            logger.info(data)
            data["action"] = "start"
            data["continuous"] = True
            data["interim_results"] = True
            transcriber.write_message(json.dumps(data), binary=False)

    def open(self):
        logger.info("New connection opened")
        self.connections.append(self)

    @gen.coroutine
    def on_close(self):
        logger.info("Connection closed")
        self.connections.remove(self)
        transcriber = yield self.transcriber
        data = {"action": "stop"}
        transcriber.write_message(json.dumps(data), binary=False)
        transcriber.close()


def make_app():
    return tornado.web.Application(
        [
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "app/static"}),
            (r"/", VAPIServer),
            (r"/inbound-call-socket", InboundCallHandler),
            (r"/recordings", RecordingsServer),
        ]
    )


if __name__ == "__main__":
    app = make_app()
    app.listen(8000)
    tornado.ioloop.IOLoop.current().start()
