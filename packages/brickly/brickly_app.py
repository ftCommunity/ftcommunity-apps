#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

from TouchStyle import *

# TODO:
# At startup highlights get lost by rate limit for unknown reason ...

# Wrapper for brickly.py python code. The main purpose of
# this wrapper is to catch the output of brickly.py and send
# it to the browser as well as to a local GUI

PORT = 9002
CLIENT = ""    # any client

OUTPUT_DELAY = 0.01
MAX_HIGHLIGHTS_PER_SEC = 25

import time, sys, asyncio, websockets, queue, pty, json

# the websocket server is a seperate tread for handling the websocket
class WebsocketServerThread(QThread):
    def __init__(self): 
        super(WebsocketServerThread,self).__init__()
        self.clients = []
        self.queue = queue.Queue()
        self.websocket = None

        # initial speed must not be > 90 to prevent rate limit from dropping
        # highlights before the browser has sent the actual speed value
        self.speed = 90  # range 0 .. 100

    def speed(self):
        return self.speed
        
    def run(self): 
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        start_server = websockets.serve(self.handler, CLIENT, PORT)
        websocketServer = self.loop.run_until_complete(start_server)

        try:
            self.loop.run_forever()
        finally:
            websocketServer.close()
            self.loop.run_until_complete(websocketServer.wait_closed())

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        
    @asyncio.coroutine
    def handler(self, websocket, path):
        self.websocket = websocket
        self.clients.append(websocket)

        # Client has finally connected. First
        # send all queued messages
        while not self.queue.empty():
            yield from self.websocket.send(self.queue.get())
        
        # ToDo: keep list of clients, stop
        # when last client is gone
        while(websocket.open):
            try:
                msg_str = yield from websocket.recv()
                msg = json.loads(msg_str)

                if 'speed' in msg:
                    self.speed = int(msg['speed'])

            except websockets.exceptions.ConnectionClosed:
                pass

            finally:
                pass
            
        # the websocket is no more ....
        self.websocket = None

    # send a message to all connected clients
    @asyncio.coroutine
    def send_async(self, str):
        yield from self.websocket.send(str)

    def send(self, allow_queueing, str):
        # If there is no client then just queue the messages. These will
        # then be sent once a client has connected
        if self.websocket and self.websocket.open:
            self.loop.call_soon_threadsafe(asyncio.async, self.send_async(str))
        elif allow_queueing:
            self.queue.put(str)

    def connected(self):
        return self.websocket != None
            
# this object will be receiving everything from stdout
class io_sink(object):
    def __init__(self, name, allow_queueing, thread, ui_queue):
        self.name = name
        self.allow_queueing = allow_queueing
        self.ui_queue = ui_queue
        self.thread = thread

    def write(self, message):
        # slow down everything that allows queuing
        # to keep the system usable
        if self.allow_queueing:
            time.sleep(OUTPUT_DELAY)

        # the websocket queue is shared by different sinks and thus the name
        # is added
        if(self.thread):
            self.thread.send(self.allow_queueing, json.dumps( { self.name: message } ))
        if(self.ui_queue):
            self.ui_queue.put(message)

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass    

# another sperate thread executes the code itself
class RunThread(QThread):
    def __init__(self, ws_thread, ui_queue):
        super(RunThread,self).__init__()
        self.ws_thread = ws_thread  # websocket server thread
        self.ui_queue = ui_queue    # output queue to the local gui

        # connect to TXT
        txt_ip = os.environ.get('TXT_IP')
        if txt_ip == None: txt_ip = "localhost"
        self.txt = None
        try:
            import ftrobopy
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

        # redirect stdout, sterr and highlight info to websocket server.
        # redirect stdout also to the local screen
        sys.stdout = io_sink("stdout", False, self.ws_thread, self.ui_queue)
        sys.stderr = io_sink("stderr", False, self.ws_thread, None)
        self.highlight  = io_sink("highlight", True, self.ws_thread, None)

        if not self.txt:
            print("TXT init failed", file=sys.stderr)

    def run(self):
        self.online = False
        path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(path, "brickly.py")
        stamp_fname = os.path.join(path, "brickly.stamp")
        if not os.path.isfile(fname):
            fname = os.path.join(path, "default.py")
        else:
            # A brickly.py was found. Now check if there's a stamp
            # that's older than brickly.py. If it is then the
            # brickly.py has never been run before which in turn
            # means that brickly_app has been launched from the
            # web interface

            # if no stamp exists at all then we are also running
            # online
            if not os.path.isfile(stamp_fname):
                self.online = True
            else:
                brickly_time = os.stat(fname).st_mtime
                stamp_time = os.stat(stamp_fname).st_mtime
                if brickly_time > stamp_time:
                    self.online = True

        stamp = open(stamp_fname, 'w')
        stamp.close()

        # load and execute locally stored blockly code
        with open(fname, encoding="UTF-8") as f:
            try:
                # replace global calls by calls into the local class
                # this could be done on javascript side but this would make
                # the bare generated python code harder to read
                code_txt = f.read()
                code_txt = "global self_\nself_ = self\n" + code_txt
                code_txt = code_txt.replace("# highlightBlock(", "self_.highlightBlock(");
                code_txt = code_txt.replace("setOutput(", "self_.setOutput(");
                code_txt = code_txt.replace("getInput(", "self_.getInput(");
                code_txt = code_txt.replace("playSound(", "self_.playSound(");

                # convert global functions to methods
                code = compile(code_txt, "brickly.py", 'exec')

                # if running in online mode wait for the client to
                # connect
                if self.online:
                    # wait for client before executing code
                    while not self.ws_thread.connected():
                        time.sleep(0.01)

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
            print("O" + str(port+1) + "=" + str(val), file=sys.stderr)
        else:
            if val:
                pwm_val = 512
            else:   
                pwm_val = 0

            self.txt.setPwm(port,pwm_val)

    def getInput(self,port):
        if not self.txt:
            # if no TXT could be connected just write to stderr
            print("I" + str(port+1) + "=" + str(True), file=sys.stderr)
            return True
        else:
            return not self.txt.getCurrentInput(port)

    def playSound(self,snd):
        if not self.txt:
            # if no TXT could be connected just write to stderr
            print("SND " + str(snd), file=sys.stderr)
        else:
            self.txt.setSoundIndex(snd)
            self.txt.incrSoundCmdId()
        
    # this function is called from the blockly code itself. This feature has
    # to be enabled on javascript side in the code generation. The delay 
    # limits the load on the browser/client
    def highlightBlock(self, str):
        if not hasattr(self, 'last'):
            self.last = 0

        now = time.time()*1000.0
        if now > self.last + (1000/MAX_HIGHLIGHTS_PER_SEC):
            self.last = now

            time.sleep((100-self.ws_thread.speed)/100)
            self.highlight.write(str)
            
class Application(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)

        # start the websocket server listening for web clients to connect
        self.ws = WebsocketServerThread()
        self.ws.start() 

        # create the empty main window
        w = TouchWindow("Brickly")

        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        w.setCentralWidget(self.txt)

        # a timer to read the ui output queue and to update
        # the screen
        self.ui_queue = queue.Queue()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(10)
        
        # start the run thread executing the blockly code
        self.thread = RunThread(self.ws, self.ui_queue)
        self.thread.start()
  
        w.show()
        self.exec_()        

        self.ws.stop()

    def on_timer(self):
        while not self.ui_queue.empty():
            self.append(self.ui_queue.get())

    def append(self, str):
        self.txt.moveCursor(QTextCursor.End)
        self.txt.insertPlainText(str)

if __name__ == "__main__":
    Application(sys.argv)
