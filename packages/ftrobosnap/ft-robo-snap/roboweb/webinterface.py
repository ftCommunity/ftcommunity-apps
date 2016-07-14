""" A combined HTTP and WebSocket handler realizing the RoboWeb interface"""
import collections
import json
import urlparse
import os.path
from BaseHTTPServer import BaseHTTPRequestHandler
from SocketServer import BaseRequestHandler

import time

from roboweb import protocol
from SimpleHTTPServer import SimpleHTTPRequestHandler

from httpwebsockethandler.HTTPWebSocketsHandler import HTTPWebSocketsHandler

STATIC_FILES = ['/', '/index.html', '/favicon.ico']
STATIC_PREFIXES = [
    '/ide/', '/snap/'
]
STATIC_OVERLAYS = {
    '/ide/': '/snap/'
}


def is_static_path(path):
    return path in STATIC_FILES or static_prefix_of(path) is not None


def static_prefix_of(path):
    for prefix in STATIC_PREFIXES:
        if path.startswith(prefix):
            return prefix
    return None


def is_control_path(path):
    return path == '/control' or path.startswith('/control:')


class WebInterfaceHandler(HTTPWebSocketsHandler):
    """
    Handles HTTP and WebSocket requests from clients.

    This handler realizes both the actual web interface to the _controller
    software (either as a WebSocket connection or via HTTP POST/GET) and
    serves static files from selected subdirectories (Only HTTP GET/HEAD 
    allowed).
    
    Allowed static paths are:

    /
        redirects to ``/index.html``
    /index.html
        entry point for the web interface
    /snap/*
        the Snap! IDE (adapted for controlling the Robotics TXT)
    /ui/*
        additional pages and resources (images, style sheets etc.) for the web interface
    
    The actual web interface is located at ``/control`` and allows communication
    with the _controller using the RoboWeb protocol (see protocol.py for details).
    
    Messages can be exchanged either by doing a WebSocket handshake on the
    ``/control`` URL and sending/receiving RoboWeb protocol messages encoded in
    JSON, or by sending commands encoded as HTTP parameters via GET/POST.
    
    WebSocket is the preferred method for communication because it has
    less overhead than HTTP and allows the _controller to actively push messages
    to the client (e.g to signal input changes), as opposed to HTML where the
    current state must be polled by the client.
    """

    server_version = "RoboWeb/0.1"
    protocol_version = "HTTP/1.1"

    # noinspection PyAttributeOutsideInit
    def setup(self):
        HTTPWebSocketsHandler.setup(self)
        # TODO: get connection ID from Cookie/URL path/... to allow for more than one connection per client
        self.replies = collections.deque()
        # noinspection PyTypeChecker
        self.robotxt_connection = protocol.connect(
                connection_id=self.client_address[0],
                reply_callback=self.process_robotxt_message
        )

    def list_directory(self, path):
        # we do not allow directory listing.
        self.send_error(403)

    def do_GET(self):
        if is_static_path(self.path):
            # noinspection PyAttributeOutsideInit
            self.path = self._translate_overlay_path(self.path)
            SimpleHTTPRequestHandler.do_GET(self)
        elif is_control_path(self.path):
            if self.headers.get("Upgrade", None) == "websocket":
                self._handshake()
                # do_GET only returns after client close or socket error.
                self._read_messages()
            else:
                self._handle_roboweb_request_http(urlparse.unquote(self.path[9:]))
        else:
            self.send_error(404)

    def do_HEAD(self):
        if is_static_path(self.path):
            # noinspection PyAttributeOutsideInit
            self.path = self._translate_overlay_path(self.path)
            SimpleHTTPRequestHandler.do_HEAD(self)
        else:
            self.send_error(405)

    def do_POST(self):
        if is_control_path(self.path):
            content_type = self.headers.getheader('content-type')
            length = int(self.headers.getheader('content-length'))
            message = self.rfile.read(length)
            if content_type == 'application/json':
                self._handle_roboweb_request_http(message, content_type)
            else:
                self.send_error(415)
        else:
            self.send_error(405)

    def process_robotxt_message(self, message):
        self.replies.append(json.dumps(message, default=lambda o: repr(o)))
        if self.connected:
            while self.replies:
                self.send_message(self.replies.popleft())
        return True

    def _parse_message(self, raw_message):
        if not raw_message:
            return None
        try:
            return protocol.Request.from_dict(json.loads(raw_message))
        except ValueError as err:
            return protocol.Error('Failed to parse message %s as JSON' % (raw_message), err)

    def on_ws_message(self, message):
        parsed_message = self._parse_message(message)
        if isinstance(parsed_message, protocol.Error):
            self.process_robotxt_message(parsed_message)
        elif parsed_message is not None:
            self.robotxt_connection.send(parsed_message)

    def on_ws_connected(self):
        self.process_robotxt_message(protocol.GenericStatusReport(verbose=True))

    def on_ws_closed(self):
        self.robotxt_connection.disconnect()

    def _translate_overlay_path(self, path):
        overlay_prefix = static_prefix_of(path)
        if overlay_prefix is None:
            return path
        base = STATIC_OVERLAYS.get(overlay_prefix, None)
        if base is None:
            return path

        ospath = self.translate_path(path)
        if os.path.isfile(ospath):
            return path
        else:
            return base + path[len(overlay_prefix):]


    def _handle_roboweb_request_http(self, message):
        parsed_message = self._parse_message(message)
        if isinstance(parsed_message, protocol.Error):
            self.process_robotxt_message(parsed_message)
        elif parsed_message is not None:
            self.robotxt_connection.send(parsed_message)
        # If we have no reply queued up, wait a bit for a reply from the controller
        max_wait = time.time() + 5
        while not (self.replies or time.time() >= max_wait):
            time.sleep(0.1)
        # Cannot simply use '\n'.join(self.replies) and then clear the queue
        # because this would introduce a race condition
        data = ''
        while self.replies:
            data += self.replies.pop() + '\n'
        self.send_response(200)  # Note: protocol errors are not encoded in HTTP status codes
        self.send_header('Content-Type', 'application/x-json-stream')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)
        if self.close_connection:
            self.robotxt_connection.disconnect()

    def send_error(self, code, message=None):
        self.robotxt_connection.disconnect()
        BaseHTTPRequestHandler.send_error(self, code, message)


def msg_from_query_string(message):
    parsed = {}
    for name, value in urlparse.parse_qsl(message):
        value = _parse_http_param_value(value)
        if name in parsed:
            existing = parsed[name]
            if isinstance(existing, list):
                existing.append(value)
            else:
                parsed[name] = [existing, value]
        else:
            parsed[name] = value
    return protocol.Request.from_dict(parsed)


def _parse_http_param_value(value):
    if value[0] in ['[', '{']:
        return json.loads(value)
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            if value == 'true':
                return True
            elif value == 'false':
                return False
            else:
                return value
