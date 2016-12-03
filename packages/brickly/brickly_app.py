#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

from TouchStyle import *
import ftrobopy

# Wrapper for brickly.py python code. The main purpose of
# this wrapper is to catch the output of brickly.py and send
# it to the browser as well as to a local GUI

PORT = 9002
CLIENT = ""    # any client

import time, sys, asyncio, websockets, queue, pty, json

# the websocket server is a seperate tread for handling the websocket
class WebsocketServerThread(QThread):
    def __init__(self): 
        super(WebsocketServerThread,self).__init__()
        self.clients = []
        self.queue = queue.Queue()

    def run(self): 
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        server = websockets.serve(self.handler, CLIENT, PORT)
        self.loop.run_until_complete(server)

        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)

    def queued(self):
        return not self.queue.empty();
        
    @asyncio.coroutine
    def handler(self, websocket, path):
        self.clients.append(websocket)

        # ToDo: keep list of clients, stop
        # when last client is gone
        while(websocket.open):
            if not self.queue.empty():
                yield from websocket.send(self.queue.get())
            else:
                yield from asyncio.sleep(0.1)

        asyncio.get_event_loop().stop()

# this object will be receiving everything from stdout
class io_sink(object):
    def __init__(self, name, ws_queue, ui_queue):
        self.name = name
        self.ws_queue = ws_queue
        self.ui_queue = ui_queue

    def write(self, message):
        # the websocket queue is shared by different sinks and thus the name
        # is added
        if(self.ws_queue):
            self.ws_queue.put(json.dumps( { self.name: message } ))
        if(self.ui_queue):
            self.ui_queue.put(message)

        # todo: re-think the delay
        time.sleep(0.01)     # artificially slow down print to keep the system usable

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass    

# another sperate thread executes the code itself
class RunThread(QThread):
    def __init__(self, ws_queue, ui_queue):
        super(RunThread,self).__init__()
        self.ws_queue = ws_queue    # general purpose msg queue to the websocket server
        self.ui_queue = ui_queue    # output queue to the local gui

        # connect to TXT
        txt_ip = os.environ.get('TXT_IP')
        if txt_ip == None: txt_ip = "localhost"
        self.txt = None
        try:
            self.txt = ftrobopy.ftrobopy(txt_ip, 65000)
            # all outputs normal mode
            M = [ self.txt.C_OUTPUT, self.txt.C_OUTPUT, self.txt.C_OUTPUT, self.txt.C_OUTPUT ]
            I = [ (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                  (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                  (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                  (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                  (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                  (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                  (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                  (self.txt.C_SWITCH, self.txt.C_DIGITAL ) ]
            self.txt.setConfig(M, I)
            self.txt.updateConfig()
        except:
            self.txt = None   

        # redirect stdout, sterr and hightlight info to websocket server.
        # redirect stdout also to the local screen
        sys.stdout = io_sink("stdout", self.ws_queue, self.ui_queue)
        sys.stderr = io_sink("stderr", self.ws_queue, None)
        self.highlight  = io_sink("highlight", self.ws_queue, None)

        if not self.txt:
            print("TXT init failed", file=sys.stderr)

    def run(self):
        path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(path, "brickly.py")
        if not os.path.isfile(fname):
            fname = os.path.join(path, "default.py")
        
        # load and execute locally stored blockly code
        with open(fname, encoding="UTF-8") as f:
            try:
                # replace global highlight calls by calls into the local class
                # this could be done on javascript side but this would make
                # the generated python code harder to read
                code_txt = f.read()
                code_txt = code_txt.replace("# highlightBlock(", "self.highlightBlock(");
                code_txt = code_txt.replace("setOutput(", "self.setOutput(");
                code_txt = code_txt.replace("getInput(", "self.getInput(");
                code = compile(code_txt, "brickly.py", 'exec')
                exec(code)
            except SyntaxError as e:
                print("Syntax error: " + str(e), file=sys.stderr)
            except:
                print("Unexpected error: " + str(sys.exc_info()[1]), file=sys.stderr)

            self.highlight.write("none")

    #
    def setOutput(self,port,val):
        if not self.txt:
            # if no TXT could be connected just write to stderr
            print("FAKE O" + str(port+1) + "=" + str(val), file=sys.stderr)
        else:
            if val:
                pwm_val = 512
            else:   
                pwm_val = 0

            self.txt.setPwm(port,pwm_val)

    def getInput(self,port):
        if not self.txt:
            # if no TXT could be connected just write to stderr
            print("FAKE I" + str(port+1) + "=" + str(True), file=sys.stderr)
            return True
        else:
            return not self.txt.getCurrentInput(port)
        
    # this function is called from the blockly code itself. This feature has
    # to be enabled on javascript side in the code generation. The delay 
    # limits the load on the browser/client
    def highlightBlock(self, str):
        time.sleep(0.1)          # TODO: make speed adjustable
        # send event to websocket thread for transmission
        self.highlight.write(str)

class Application(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)
        self.ui_queue = queue.Queue()

        # start the websocket server listening for web clients to connect
        self.ws = WebsocketServerThread()
        self.ws.start() 

        # start the run thread executing the blockly code
        self.thread = RunThread(self.ws.queue, self.ui_queue)
        self.thread.start()
  
        # create the empty main window
        w = TouchWindow("Brickly")

        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        w.setCentralWidget(self.txt)

        # a timer to read the ui output queue and to update
        # the screen
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(100)
        
        w.show()
        self.exec_()        

        self.ws.stop()

    def on_timer(self):
        if not self.ui_queue.empty():
            self.append(self.ui_queue.get())

    def append(self, str):
        self.txt.moveCursor(QTextCursor.End)
        self.txt.insertPlainText(str)

if __name__ == "__main__":
    Application(sys.argv)
