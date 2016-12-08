#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

# Wrapper for brickly.py python code. The main purpose of
# this wrapper is to catch the output of brickly.py and send
# it to the browser as well as to a local GUI

PORT = 9002
CLIENT = ""    # any client

import time, sys, threading, asyncio, websockets, queue, pty, json
import os

# debug to file since stdout doesn't exist
dbg = open('/tmp/brickly.log', 'w', encoding="UTF-8")

# the websocket server is a seperate tread for handling the websocket
class websocket_server(threading.Thread): 
    def __init__(self): 
        threading.Thread.__init__(self) 
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
        print("WS Client connect ...", file=dbg)
        dbg.flush()
        self.clients.append(websocket)

        # ToDo: keep list of clients, stop
        # when last client is gone
        while(websocket.open):
            if not self.queue.empty():
                yield from websocket.send(self.queue.get())
            else:
                yield from asyncio.sleep(0.1)

        print("WS client disconnect!", file=dbg)
        dbg.flush()
        asyncio.get_event_loop().stop()

# this object will be receiving everything from stdout
class io_sink(object):
    def __init__(self, name, queue, fd):
        self.name = name
        self.file = fd
        self.queue = queue

    def write(self, message):
        if(self.file):
            self.file.write(message)
            self.file.flush()
            time.sleep(0.01)     # artificially slow down print to keep the system usable
            
        self.queue.put(json.dumps( { self.name: message } ))

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass    

# this function is called from the blockly code itself. This feature has
# to be enabled on javascript side in the code generation. The delay 
# limits the load on the browser/client
def highlightBlock(str):
    time.sleep(0.1)          # TODO: make speed adjustable
    global highlight
    highlight.write(str)

thread = websocket_server()
thread.start() 

# redirect stdout and sterr to websocket server as well as into file
sys.stdout = io_sink("stdout", thread.queue, dbg)
sys.stderr = io_sink("stderr", thread.queue, dbg)
highlight  = io_sink("highlight", thread.queue, None)

# connect to TXT
txt_ip = os.environ.get('TXT_IP')
if txt_ip == None: txt_ip = "localhost"
txt = None
try:
    import ftrobopy
    txt = ftrobopy.ftrobopy(txt_ip, 65000)
    # all outputs normal mode
    M = [ txt.C_OUTPUT, txt.C_OUTPUT, txt.C_OUTPUT, txt.C_OUTPUT ]
    I = [ (txt.C_SWITCH, txt.C_DIGITAL ),
          (txt.C_SWITCH, txt.C_DIGITAL ),
          (txt.C_SWITCH, txt.C_DIGITAL ),
          (txt.C_SWITCH, txt.C_DIGITAL ),
          (txt.C_SWITCH, txt.C_DIGITAL ),
          (txt.C_SWITCH, txt.C_DIGITAL ),
          (txt.C_SWITCH, txt.C_DIGITAL ),
          (txt.C_SWITCH, txt.C_DIGITAL ) ]
    txt.setConfig(M, I)
    txt.updateConfig()
except:
    print("TXT init failed", file=sys.stderr)
    txt = None   

# TXT specific helper routines
def setOutput(port, val):
    if not txt:
        # if no TXT could be connected just write to stderr
        print("O" + str(port+1) + "=" + str(val), file=sys.stderr)
    else:
        if val:
            pwm_val = 512
        else:   
            pwm_val = 0

        txt.setPwm(port,pwm_val)

def getInput(port):
    if not txt:
        # if no TXT could be connected just write to stderr
        print("I" + str(port+1) + "=" + str(True), file=sys.stderr)
        return True
    else:
        return not txt.getCurrentInput(port)

def playSound(snd):
    if not txt:
        # if no TXT could be connected just write to stderr
        print("SND " + str(snd), file=sys.stderr)
    else:
        txt.setSoundIndex(snd)
        txt.incrSoundCmdId()

# load and execute blockly code
with open("brickly.py", encoding="UTF-8") as f:
    try:
        code_txt = f.read()
        code_txt = code_txt.replace("# highlightBlock(", "highlightBlock(");
        code = compile(code_txt, "brickly.py", 'exec')
        exec(code)
    except SyntaxError as e:
        print("Syntax error: " + str(e), file=sys.stderr)
    except:
        print("Unexpected error: " + sys.exc_info()[1], file=sys.stderr)

# program stays alive for 5 seconds after download
highlight.write("none")
time.sleep(5)

# wait for queue to become empty. This means that the client
# has connected and has fetched all results. We could add a timeout
# here to cope with the fact that the client may never connect
#while thread.queued():
#    time.sleep(0.1)

# now we could the server thread as we don't need it anymore. But letting
# it run makes the client side happy as it doesn't have to deal with a
# lost websocket connection
time.sleep(1)
thread.stop()

