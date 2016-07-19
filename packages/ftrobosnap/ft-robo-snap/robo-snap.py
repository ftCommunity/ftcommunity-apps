#!/usr/bin/python
"""
Start the Robotic TXT Controller web interface

Usage: robo-snap.py robotxt [port]

where robotxt is the host name or IP address of the Robotics TXT controller, 
and [port] is the (optional) local port to bind to (defaults to 65003).

If you run robo-snap directly on the Robotics TXT, use "localhost" as the
controller address.
"""

import sys
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn

from roboweb import webinterface, protocol

if len(sys.argv) < 2 or len(sys.argv) > 3:
    print(__doc__.strip())
    sys.exit(1)

protocol.robotxt_address = sys.argv[1]

if len(sys.argv) > 2:
    port = int(sys.argv[2])
else:
    port = 65003


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


def _ws_main():
    try:
        server = ThreadedHTTPServer(('0.0.0.0', port), webinterface.WebInterfaceHandler)
        server.daemon_threads = True
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, shutting down server')
        server.socket.close()


if __name__ == '__main__':
    _ws_main()
