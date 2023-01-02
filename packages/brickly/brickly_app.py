#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

from TouchStyle import *
from qjoystick import QJoystick

try:
    import sys
    sys._excepthook = sys.excepthook # always save before overriding

    def application_exception_hook(exctype, value, traceback):
        # Let's try to write the problem
        print("Exctype : %s, value : %s traceback : %s"%(exctype, value, traceback))
        # Call the normal Exception hook after (this will probably abort application)
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)

    # Do not forget to our exception hook
    sys.excepthook = application_exception_hook
except:
    print("Failed to install an exception hook")
    

PORT = 9002
CLIENT = ""    # any client

MAX_TEXT_LINES=50           # same as web ui

USER_PROGRAMS = "user"      # directory containing the user programs
FLOAT_FORMAT = "{0:.3f}"    # limit to three digits to keep the output readable
OUTPUT_DELAY = 0.01
MAX_HIGHLIGHTS_PER_SEC = 25

import time, sys, asyncio, websockets, queue, pty, json, math, re
import xml.etree.ElementTree
import threading
import ftrobopy

# the websocket server is a seperate tread for handling the websocket
class WebsocketServerThread(QThread):
    command = pyqtSignal(str)
    setting = pyqtSignal(dict)
    python_code = pyqtSignal(str)
    blockly_code = pyqtSignal(str)
    program_name = pyqtSignal(list)
    client_connected = pyqtSignal(bool)
    speed_changed = pyqtSignal(int)
    plugin_cmd = pyqtSignal(str, str, str)
    plugin = pyqtSignal(str, str)
    
    def __init__(self): 
        super(WebsocketServerThread,self).__init__()
        self.websocket = None

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
        # reject any further client besides the first (main) one
        if self.websocket:
            return

        self.websocket = websocket

        self.client_connected.emit(True)

        # run while client is connected
        while(websocket.open):
            try:
                # receive json encoded commands via websocket
                msg_str = yield from websocket.recv()
                msg = json.loads(msg_str)

                # emit pyqt signals for any valid request
                if 'speed' in msg:
                    self.speed_changed.emit(int(msg['speed']))
                if 'lang' in msg:
                    self.setting.emit( { 'lang': msg['lang'] } )
                if 'skill' in msg:
                    self.setting.emit( { 'skill': msg['skill'] })
                if 'command' in msg:
                    self.command.emit(msg['command'])
                if 'program_name' in msg:
                    self.program_name.emit(msg['program_name'])
                if 'python_code' in msg:
                    self.python_code.emit(msg['python_code'])
                if 'blockly_code' in msg:
                    self.blockly_code.emit(msg['blockly_code'])
                if 'plugin' in msg:
                    self.plugin.emit(msg['plugin']['name'], msg['plugin']['code'])

                # check if one entry begins with "plugin:"
                for i in msg:
                    parts = i.split(':')
                    if len(parts) == 3 and parts[0] == "plugin":
                        self.plugin_cmd.emit(parts[1], parts[2], msg[i])
                    
            except websockets.exceptions.ConnectionClosed:
                pass

            finally:
                pass
            
        # the websocket is no more ....
        self.client_connected.emit(False)
        self.websocket = None

    # send a message to the connected client
    @asyncio.coroutine
    def send_async(self, str):
        yield from self.websocket.send(str)

    def send(self, str):
        # If there is no client then just drop the messages.
        if self.websocket and self.websocket.open:
            # Get the symbol for ensure_future / async.
            # TODO: Remove this hack as soon as we don't need compatibility
            # with python < 3.4.4 anymore
            hack = getattr(asyncio, 'ensure_future', getattr(asyncio, 'async', None))
            self.loop.call_soon_threadsafe(hack, self.send_async(str))

    def connected(self):
        return self.websocket != None

# this object will be receiving everything from stdout
class io_sink(object):
    def __init__(self, name, thread, ui_queue):
        self.name = name
        self.ui_queue = ui_queue
        self.thread = thread

    def write(self, message):
        # todo: slow down stdout and stderr only
        time.sleep(OUTPUT_DELAY)

        if(self.thread):
            self.thread.send(json.dumps( { self.name: message } ))
        if(self.ui_queue):
            self.ui_queue.put(message)

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass    

class UserInterrupt(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return "UserInterrupt: " + repr(self.value)

# load the client side of plugins
class PluginLoader:
    def __init__(self, run_thread):
        self.run_thread = run_thread

    def loadCode(self, name, code):
        # create a class
        class_code = "class Plugin_"+name+":\n" + code
        exec(class_code, globals())

        # instantiate the class
        return eval("Plugin_"+name+"( self.run_thread )")

    def load(self, name):
        path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(path, "plugins", name+".xml")

        try:
            root = xml.etree.ElementTree.parse(fname).getroot()
        except:
            return None

        # root element must be plugin
        if root.tag != "plugin": 
            return None

        # report plugin version number
        if 'version' in root.attrib:
            print("Plugin", name, "version", root.attrib['version'])
        
        # only the first "exec" element is executed
        for child in root:
            if child.tag == "exec":
                return self.loadCode(name, child.text)

        return None

    def loadAll(self):
        plugins = { }
        plugin_names = [ ]

        # read the plugins file
        path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(path, "plugins", "plugins.list")
        try:
            with open(fname) as f:
                for line in f:
                    l = line.split(';')[0].strip()
                    if(len(l) > 0):
                        plugin_names.append(l)        
        except:
            return

        # got list, now try to load em all
        for p in plugin_names:
            plugins[p] = self.load(p)

        return plugins
            
# another sperate thread executes the code itself
class RunThread(QThread):
    done = pyqtSignal()
    
    def __init__(self, ws_thread, ui_queue):
        super(RunThread,self).__init__()

        loader = PluginLoader(self)
        self.plugins = loader.loadAll()

        self.speed = 90  # range 0 .. 100
        self.txt_io_lock = None
        self.joystick = None

        self.ws_thread = ws_thread  # websocket server thread
        self.ui_queue = ui_queue    # output queue to the local gui

        # connect to TXT
        try:
            txt_ip = os.environ.get('TXT_IP')
            if not txt_ip: txt_ip = "localhost"
            self.txt = ftrobopy.ftrobopy(txt_ip, 65000)
        except:
            self.txt = None

        if self.txt:
            # all outputs normal mode
            self.M = [ self.txt.C_OUTPUT, self.txt.C_OUTPUT,
                       self.txt.C_OUTPUT, self.txt.C_OUTPUT ]
            self.I = [ (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                       (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                       (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                       (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                       (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                       (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                       (self.txt.C_SWITCH, self.txt.C_DIGITAL ),
                       (self.txt.C_SWITCH, self.txt.C_DIGITAL ) ]
            self.txt.setConfig(self.M, self.I)
            self.txt.updateConfig()
                
        self.motor = [ None, None, None, None ]
        self.mobile = None
 
        # redirect stdout, stderr info to websocket server.
        # redirect stdout also to the local screen
        sys.stdout = io_sink("stdout", self.ws_thread, self.ui_queue)
        sys.stderr = io_sink("stderr", self.ws_thread, None)

        if not self.txt:
            print("TXT init failed", file=sys.stderr)

        # this is a convenience function to be used by plugins
    def tx(self, msg):
        self.ws_thread.send( msg )

    def setJoystick(self, js):
        self.joystick = js

    def send_highlight(self, id, thread_id=None):
        if thread_id != None:
            self.ws_thread.send(json.dumps( { "highlight": id, "thread": thread_id } ))
        else:
            self.ws_thread.send(json.dumps( { "highlight": id } ))

    def set_program_name(self, name):
        self.program_name = name

    def run(self):
        self.stop_requested = False
        self.sync_open = False
        path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(path, USER_PROGRAMS, os.path.splitext(self.program_name[0])[0] + ".py")

        # file really does exist?
        if os.path.isfile(fname):
            # load and execute locally stored blockly code
            with open(fname, encoding="UTF-8") as f:
                try:
                    # replace global calls by calls into the local class
                    # this could be done on javascript side but this would make
                    # the bare generated python code harder to read
                    global brickly
                    brickly = self    # make self accessible to all functions of blockly code
                
                    code_txt = f.read()

                    code_txt = code_txt.replace("# speed", "brickly.speed");
                    code_txt = code_txt.replace("# highlightBlock(", "brickly.highlightBlock(0,");
 
                    functions = [ "jsIsPresent", "jsGetButton", "jsGetAxis",
                                  "setOutput", "setMotor","setMotorSync", "setMotorOld",
                                  "mobileConfig", "mobileDrive", "mobileDriveWhile",
                                  "mobileTurn", "wait", "sync", "print", "str", "setMotorOff",
                                  "motorHasStopped", "getInput", "inputConvR2T",
                                  "playSound", "textClear", "textPrintColor" ]
                    for func in functions:
                        code_txt = code_txt.replace(func+"(", "brickly."+func+"(");

                    # Threading needs a bunch of special support. Mainly we need to detect all
                    # functions which are supposed to be threads and then add some code to actually
                    # run these threads. Also the code must be modified to make sure that each thread
                    # has it's own "highlight" when displaying the execution state in the browser.
                    # Finally the threads need their own exception handling
                        
                    # check for "thread" functions inside the program and extract all thread related code
                    # into a seperate string
                    thread = None
                    threads = []
                    code_lines = code_txt.split('\n');
                    code_txt = ""
                    for l in code_lines:
                        if not l.strip():
                            # empty lines go wherever we currently are
                            if thread:
                                thread += l+"\n";
                            else:
                                code_txt += l + "\n";
                        else:
                            # lines containing text either belong to threads
                            # or to the main program

                            if l == "def thread():":
                                # a thread starts
                                
                                # remove previous "highlight" line as it belonged to
                                # the thread function itself
                                code_txt = "\n".join(code_txt.split('\n')[:-2])+"\n"
                                
                                thread = ""
                            else:
                                # still in thread
                                if thread != None:
                                    if l[0] == ' ':
                                        # line indented -> belongs to thread
                                        thread += l+"\n";
                                    else:
                                        # otherwise thread ends here
                                        threads.append(thread)
                                        thread = None
                                        code_txt += l + "\n";
                                else:
                                    code_txt += l + "\n";

                    # append the last thread if there was one
                    if thread:
                        threads.append(thread)
                        # multithreaded programs need a lock on the hardware
                        self.txt_io_lock = threading.Lock()

                    # create a matching list of highlight timers for all threads and the main thread
                    self.highlight_timer = [0] * (len(threads)+1)
                    
                    if len(threads) > 0:
                        # prepend code to main code to start the threads and append thread code
                        code_threads_init = ""
                        
                        # add code of all threads
                        for ti in range(len(threads)):
                            ts = str(ti+1)  # threads id as a string
                            
                            # bind the highlight to the thread so each thread has its own highlight
                            thread_code_raw = threads[ti].replace("highlightBlock(0,", "highlightBlock("+ts+",");

                            # make sure highlight is disabled when thread ends
                            thread_code_raw += "  brickly.highlightBlock(" + ts + ",'none')"
                            
                            # indent entire thread code an additional level for the surrounding try
                            thread_code = ""
                            for line in thread_code_raw.splitlines():
                                thread_code += "  "+line+"\n"

                            # surround thread with code to catch user interrupt exception
                            thread_code  = "  try:\n" + thread_code
                            thread_code += "  except UserInterrupt as e:\n"
                            thread_code += "    pass\n"
                            
                            code_threads_init += "def thread_" + ts + "():\n"
                            code_threads_init += thread_code
                            code_threads_init += "\n"

                            # print("T:", code_threads_init)
                            
                        for ti in range(len(threads)):
                            ts = str(ti+1)  # threads id as a string
                            code_threads_init += "t"+ts+" = threading.Thread(target=thread_"+ts+", args=[])\n"
                            code_threads_init += "t"+ts+".start()\n"

                        code_txt = code_threads_init + code_txt

                        # this is the end of the main thread, unhighlight it and wait for threads
                        
                        code_txt += "brickly.highlightBlock(0,'none')\n"
                        for ti in range(len(threads)):
                            code_txt += "t"+str(ti+1)+".join()\n"

                    # inform all interested plugins that the program now runs
                    for p in self.plugins:
                        init = getattr(self.plugins[p], "init", None)
                        if callable(init):
                            self.plugins[p].init();

                    exec(code_txt, globals())

                except SyntaxError as e:
                    print("Syntax error: " + str(e), file=sys.stderr)
                except UserInterrupt as e:
                    pass
                except:
                    print("Unexpected error: " + str(sys.exc_info()[1]), file=sys.stderr)

                # close a "sync" block which was left open. The TXT doesn't like it 
                # to be kept open
                if self.sync_open:
                    if self.txt:
                        self.txt.SyncDataEnd();
                    self.sync_open = False
                
                # inform all interested plugins that the program has ended
                for p in self.plugins:
                    cleanup = getattr(self.plugins[p], "cleanup", None)
                    if callable(cleanup):
                        self.plugins[p].cleanup();

            self.done.emit()
            self.send_highlight("none")

            # shut down all outputs
            if self.txt:
                for i in range(4):
                    # switch motors off
                    if self.M[i] == self.txt.C_MOTOR:
                        # print("stop motor")
                        self.motor[i]['dev'].stop()
                        self.M[i] = self.txt.C_OUTPUT
                        self.motor[i] = None
                    # turn outputs off
                    if self.M[i] == self.txt.C_OUTPUT:
                        self.txt.setPwm(2*i,  0)
                        self.txt.setPwm(2*i+1,0)

                self.txt.setConfig(self.M, self.I)
                self.txt.updateConfig()

            # forget all user setup configs
            self.motor = [ None, None, None, None ]
            self.mobile = None
                
    def stop(self):
        self.stop_requested = True

    def set_speed(self, val):
        self.speed = val

    def on_plugin_cmd(self, name, cmd, data):
        # Received a plugin specific command from the browser. This
        # calls a method inside the plugin
        getattr(self.plugins[name], cmd)(data)

    def wait(self, duration):
        # make sure we never pause more than 100ms to be able
        # to react fast on user interrupts
        while(duration > 0.1):
            time.sleep(0.1)
            duration -= 0.1
            if self.stop_requested:
                raise UserInterrupt(42)
            
        time.sleep(duration)

    # custom string conversion
    def str(self, arg):
        # use custom conversion for booleans
        if type(arg) is bool:
            if arg: return QCoreApplication.translate("Logic", "true")
            else:   return QCoreApplication.translate("Logic", "false")

        # use custom conversion for float numbers
        if type(arg) is float:
            if math.isinf(arg):
                return "∞" 
            if math.isnan(arg):
                return "???"   # this doesn't need translation ...
            else:
                return FLOAT_FORMAT.format(arg).rstrip('0').rstrip('.')
            
        return str(arg)

    def print(self, *args, **kwargs):
        argsl = list(args)  # tuples are immutable, so use a list

        # make sure floats are converted using our custom conversion
        for i in range(len(argsl)):
            if type(argsl[i]) is float or type(argsl[i]) is bool:
                argsl[i] = self.str(argsl[i])

        # todo: don't call print but push data directly into queue
        print(*tuple(argsl), **kwargs)

    # ================================ joystick ===============================

    def jsIsPresent(self):
        return (self.joystick != None) and (len(self.joystick.joysticks()) > 0)

    def jsGetAxis(self, axis):
        self.acquire()
        
        # try ir remote if support present
        if self.txt and float(ftrobopy.version()) >= 1.68:
            if axis == "x":
                val = self.txt.joystick(0).leftright()
            elif axis == "y":
                val = -self.txt.joystick(0).updown()
            elif axis == "rx":
                val = self.txt.joystick(1).leftright()
            elif axis == "ry":
                val = -self.txt.joystick(1).updown()
            else:
                val = None        

            # ir remote returned something?
            if val:
                self.release()
                return 100.0 * val / 15
                
        val = self.joystick.axis(None, axis)
        if val == None: val = 0
        self.release()
        return 100.0 * val

    def jsGetButton(self, button):
        self.acquire()
        
        # try ir remote if support present
        if self.txt and float(ftrobopy.version()) >= 1.68:
            if button == "ir_on":
                val = self.txt.joybutton(0).pressed()
            elif button == "ir_off":
                val = self.txt.joybutton(1).pressed()
            else:
                val = None        

            # ir remote returned something?
            if val:
                self.release()
                return val

        val = self.joystick.button(None, button)
        if val == None: val = False
        self.release()
        return val != 0

    # ================================== FT IO ================================

    def sync(self, begin):
        if begin:
            if not self.sync_open:
                if self.txt:
                    self.txt.SyncDataBegin();
                self.sync_open = True
        else:
            if self.sync_open:
                if self.txt:
                    self.txt.SyncDataEnd();            
                self.sync_open = False

    def acquire(self):
        if self.txt_io_lock:
            self.txt_io_lock.acquire()

    def release(self):
        if self.txt_io_lock:
            self.txt_io_lock.release()

    # --------------------------------- motors --------------------------------

    def createMotor(self, port):
        # check if a motor object exists and create one of not
        if not self.motor[port]:
            # generate a motor object
            self.motor[port] = { }

            # set defaults
            self.motor[port]['dir'] = 1        # turning right
            self.motor[port]['gear'] = 63      # 63 steps per turn (new encoder motors)
            self.motor[port]['syncto'] = None  # not sync'd to any other motor
            self.motor[port]['dev'] = None
            
        if self.txt and self.M[port] != self.txt.C_MOTOR:
            self.acquire()
            
            # update config
            self.M[port] = self.txt.C_MOTOR
            self.txt.setConfig(self.M, self.I)
            self.txt.updateConfig()

            self.motor[port]['dev'] = self.txt.motor(port+1)
            self.release()

    def setMotorSync(self, port_a=0, port_b=0):
        if port_a == port_b: return

        # TODO: check if motors are already synced
        # to another motor

        # make sure both motors exist
        self.createMotor(port_a)
        self.createMotor(port_b)
        self.acquire()
        self.motor[port_a]['syncto'] = self.motor[port_b]['dev']
        self.motor[port_b]['syncto'] = self.motor[port_a]['dev']
        self.release()

    def setMotor(self, port=0, name=None, val=0):
        if not name: return

        # print("M"+str(port+1), name, val) 

        self.acquire()
        
        # make sure motor object already exists
        self.createMotor(port)

        # speed and distance are directly applied, everything else
        # is stored in the motor object
        if(name == 'speed'):
            # limit from -100% to +100%
            val = max(-100, min(100, val))
            # and scale it to 0 ... 512 range
            pwm_val = int(5.12 * val)
            # apply direction
            pwm_val = self.motor[port]['dir'] * pwm_val;
            
            if self.txt:
                self.motor[port]['dev'].setSpeed(pwm_val)

        elif(name == 'dist'):
            if val < 0: val = 0

            if self.txt:
                impulses = int(self.motor[port]['gear']*val)
                if impulses < -32768: impulses = -32768
                if impulses >  32767: impulses =  32767                
                self.motor[port]['dev'].setDistance(impulses, self.motor[port]['syncto'])
        
        elif(name == 'dir'):
            if val < 0: val = -1
            else:       val = 1
            self.motor[port][name] = val

        elif(name == 'gear'):
            if val < 0: val = -val
            self.motor[port][name] = val

        else:
            print("Unknown parameter name", name, file=sys.stderr)

        self.release()
        
    def setMotorOld(self,port=0,dir=1,val=0,steps=None):
        # this is for the old all-on-one motor blocks 

        self.acquire()
        
        # make sure val is in 0..100 range
        val = max(-100, min(100, val))
        # and scale it to 0 ... 512 range
        pwm_val = int(5.12 * val)
        # apply direction
        pwm_val = dir * pwm_val;

        # make sure motor object already exists
        self.createMotor(port)
                
        if self.txt:
            if steps:
                impulses = int(self.motor[port]['gear']*steps)
                if impulses < -32768: impulses = -32768
                if impulses >  32767: impulses =  32767
                
                self.motor[port]['dev'].setDistance(impulses)
                
            self.motor[port]['dev'].setSpeed(pwm_val)

        self.release()
        
    def setMotorOff(self,port=0):
        self.acquire()
                                
        if not self.txt:
            # if no TXT could be connected just write to stderr
            print("M" + str(port+1) + "= off", file=sys.stderr)
        else:
            # make sure that the port is in motor mode
            if self.M[port] == self.txt.C_MOTOR:
                self.motor[port]['dev'].stop()

        self.release()
            
    def motorHasStopped(self,port=0):
        self.acquire()
        
        if not self.txt:
            # if no TXT could be connected just write to stderr
            print("M" + str(port+1) + "= off?", file=sys.stderr)
            self.release()
            return True

        # make sure that the port is in motor mode
        if self.M[port] != self.txt.C_MOTOR:
            self.release()
            return True

        # print("M", port, self.motor[port], self.motor[port]['dev'].finished())
        retval = self.motor[port]['dev'].finished()
        self.release()
        return retval

    def setOutput(self,port=0,val=0):
        self.acquire()
        
        # make sure val is in 0..100 range
        val = max(0, min(100, val))
        # and scale it to 0 ... 512 range
        pwm_val = int(5.12 * val)

        if not self.txt:
            # if no TXT could be connected just write to stderr
            print("O" + str(port+1) + "=" + str(pwm_val), file=sys.stderr)
        else:
            # check if that port is in output mode and change if not
            if self.M[int(port/2)] != self.txt.C_OUTPUT:
                self.M[int(port/2)] = self.txt.C_OUTPUT
                self.txt.setConfig(self.M, self.I)
                self.txt.updateConfig()
                # forget about any motor object that may exist
                self.motor[int(port/2)] = None                
        
            self.txt.setPwm(port,pwm_val)
            
        self.release()

    # --------------------------------- mobile robots --------------------------------

    def mobileCreate(self):
        # create a default mobil config if none exists
        if not self.mobile:
            # defaults are for discovery set
            self.mobile = { }
            self.mobile['motors'] = [ 0, 1 ]       # M1 & M2
            self.mobile['motor_gear'] = 63         # TXT encoder motor with 63 impules per round
            self.mobile['gear'] = 0.5              # Z10 : Z20
            self.mobile['wheels'] = [ 5.8, 15.4 ]  # 5.8 cm wheel diameter and 15.4 cm wheel distance

        # motor rotations per driven cm
        self.mobile['cm2rot'] =  (math.pi * self.mobile['wheels'][0] * self.mobile['gear'])
        # motor rotations per rotated deg
        self.mobile['deg2rot'] = (self.mobile['cm2rot'] * 360 / (self.mobile['wheels'][1] * math.pi))

        # make sure motor objects for both motors exist
        self.createMotor(self.mobile['motors'][0])
        self.createMotor(self.mobile['motors'][1])

        # print("cm per rot", self.mobile['cm2rot'])
        # print("deg per rot", self.mobile['deg2rot'])

    def mobileConfig(self, motors, type, gear, wheels):
        # print("Config:", motors, type, gear, wheels)

        # create an empty config of none exists yet
        if not self.mobile:
            self.mobile = { }

        self.mobile['motors'] = motors
        self.mobile['motor_gear'] = type
        self.mobile['gear'] = gear
        self.mobile['wheels'] = wheels

        # do some sanity checks to prevent divisions by zero

        # motor gear must never be 0.
        if not self.mobile['motor_gear']: self.mobile['motor_gear'] = 1
        if not self.mobile['gear']: self.mobile['gear'] = 1
        if not self.mobile['wheels'][0]: self.mobile['wheels'][0] = 1
        if not self.mobile['wheels'][1]: self.mobile['wheels'][1] = 1

    def mobileDriveWhile(self, dir, w, val):
        self.acquire()
            
        # make sure mobil setup exists
        self.mobileCreate()

        if not self.txt:
            print("Drive", dir, w, val, file=sys.stderr)
        else:
            m0 = self.mobile['motors'][0]
            m1 = self.mobile['motors'][1]

            speed = 512                # full throttle forward
            if dir < 0: speed = -512   # full throttle backward
            
            # run both motors synchronous in the same direction at the same speed
            self.txt.SyncDataBegin()
            self.motor[m0]['dev'].setDistance(0, self.motor[m1]['dev'])
            self.motor[m1]['dev'].setDistance(0, self.motor[m0]['dev'])
            self.motor[m0]['dev'].setSpeed(speed)
            self.motor[m1]['dev'].setSpeed(speed)
            self.txt.SyncDataEnd()

            # wait for event
            if w:
                while(eval(val)):
                    self.txt.updateWait()
                    if self.stop_requested:
                        raise UserInterrupt(42)
            else:
                while(not eval(val)):
                    self.txt.updateWait()
                    if self.stop_requested:
                        raise UserInterrupt(42)
                    
            self.txt.SyncDataBegin()
            self.motor[m0]['dev'].stop()
            self.motor[m1]['dev'].stop()
            self.txt.SyncDataEnd()
            
        self.release()

    def mobileDrive(self, dir, dist=0):
        self.acquire()
        
        # make sure mobil setup exists
        self.mobileCreate()

        if not self.txt:
            print("Drive", dir, dist, file=sys.stderr)
        else:
            m0 = self.mobile['motors'][0]
            m1 = self.mobile['motors'][1]

            # mobile robot has 2:1 gear and a wheel diameter of 6cm 
            # -> one wheel rotation == 10cm -> gear/10 impulses per cm
            dist = int(dist * self.mobile['motor_gear'] / self.mobile['cm2rot'])
            # limit dist to ~47m as FT api doesn't cope with more
            if dist < -32768: dist = -32768
            if dist >  32767: dist =  32767
                
            speed = 512                # full throttle forward
            if dir < 0: speed = -512   # full throttle backward

            # run both motors synchronous in the same direction at the same speed
            self.txt.SyncDataBegin()
            self.motor[m0]['dev'].setDistance(dist, self.motor[m1]['dev'])
            self.motor[m1]['dev'].setDistance(dist, self.motor[m0]['dev'])
            self.motor[m0]['dev'].setSpeed(speed)
            self.motor[m1]['dev'].setSpeed(speed)
            self.txt.SyncDataEnd()

            # wait for both motors to stop
            while(not (self.motor[m0]['dev'].finished() and
                       self.motor[m1]['dev'].finished())):
                self.txt.updateWait()
                if self.stop_requested:
                    raise UserInterrupt(42)

        self.release()
            
    def mobileTurn(self, dir, angle=0):
        self.acquire()
        
        # make sure mobil setup exists
        self.mobileCreate()

        if not self.txt:
            print("Turn", dir, angle, file=sys.stderr)
        else:
            m0 = self.mobile['motors'][0]
            m1 = self.mobile['motors'][1]

            # mobile robot has 2:1 gear and a wheel diameter of 6cm 
            # and a wheel distance of ~15.5cm
            dist = int(angle * self.mobile['motor_gear'] / self.mobile['deg2rot'])
            # limit dist to ~47m as FT api doesn't cope with more
            if dist < -32768: dist = -32768
            if dist >  32767: dist =  32767
            speed = 512                # full throttle forward
            if dir < 0: speed = -512   # full throttle backward

            # run both motors synchronous in opposite direction at the same speed
            self.txt.SyncDataBegin()
            self.motor[m0]['dev'].setDistance(dist, self.motor[m1]['dev'])
            self.motor[m1]['dev'].setDistance(dist, self.motor[m0]['dev'])
            self.motor[m0]['dev'].setSpeed(speed)
            self.motor[m1]['dev'].setSpeed(-speed)
            self.txt.SyncDataEnd()

            # wait for both motors to stop
            while(not (self.motor[m0]['dev'].finished() and
                       self.motor[m1]['dev'].finished())):
                self.txt.updateWait()

        self.release()
        
    # --------------------------------- inputs --------------------------------

    def getInput(self,type,port):
        self.acquire()
        if not self.txt:
            # if no TXT could be connected just write to stderr
            print("I" + str(port+1) + " " + type + " = 0", file=sys.stderr)
            self.release()
            return 0
        else:
            input_type = {
                "voltage":    ( self.txt.C_VOLTAGE,    self.txt.C_ANALOG  ),
                "switch" :    ( self.txt.C_SWITCH,     self.txt.C_DIGITAL ),
                "resistor":   ( self.txt.C_RESISTOR,   self.txt.C_ANALOG  ),
                "ultrasonic": ( self.txt.C_ULTRASONIC, self.txt.C_ANALOG  )
            }
        
            # check if type of port has changed and update config
            # in that case
            if self.I[port] != input_type[type]:
                self.I[port] = input_type[type]
                self.txt.setConfig(self.M, self.I)
                self.txt.updateConfig()
                time.sleep(0.1)   # wait some time so the change can take effect

            # get value
            retval = self.txt.getCurrentInput(port)
            self.release()
            return retval

    def inputConvR2T(self,sys="degCelsius",val=0):
        K2C = 273.0
        B = 3900.0
        R_N = 1500.0
        T_N = K2C + 25.0

        if val == 0: return float('nan')
        
        # convert resistance to kelvin
        t = T_N * B / (B + T_N * math.log(val / R_N))

        # convert kelvin to deg celius or deg fahrenheit
        if sys == "degCelsius":      t -= K2C
        if sys == "degFahrenheit":   t = t * 9 / 5 - 459.67
        
        return t

    # --------------------------------- sound --------------------------------

    def playSound(self,snd):
        self.acquire()
        if not self.txt:
            # if no TXT could be connected just write to stderr
            print("SND " + str(snd), file=sys.stderr)
        else:
            if snd < 1:  snd = 1
            if snd > 29: snd = 29
            
            self.txt.setSoundIndex(snd)
            self.txt.incrSoundCmdId()
        self.release()
        
    # --------------------------------- custom text --------------------------------

    def textClear(self):
        # clear remote and local
        self.ws_thread.send(json.dumps( { "gui_cmd": "clear" } ))
        self.ui_queue.put( { "cmd": "clear" } )

    def textPrintColor(self, color, msg):
        self.ui_queue.put( { "text_color": [ color, self.str(msg)+"\n" ] } )
        self.ws_thread.send(json.dumps( { "text_color": [ color, self.str(msg)+"\n" ] } ))
        

    # this function is called from the blockly code itself. This feature has
    # to be enabled on javascript side in the code generation. The delay 
    # limits the load on the browser/client
    def highlightBlock(self, id, str=None):
        # if only one parameter was given, then it's a global highlight (this is
        # only used for removal)
        if not str:
            str = id
            id = None
        
        if self.stop_requested:
            raise UserInterrupt(42)

        # remove any timer list if all highlights are removed
        # and always send this regardless of timer
        if not id and str == None:
            self.send_highlight(str, id)
        else:
            now = time.time()*1000.0
            if now > self.highlight_timer[id] + (1000/MAX_HIGHLIGHTS_PER_SEC):
                self.highlight_timer[id] = now

                time.sleep((100-self.speed)/100)  # some max speed limit
                self.send_highlight(str, id)

class ProgramListWidget(QListWidget):
    selected = pyqtSignal(list)
    
    def __init__(self, files, current, parent=None):
        super(ProgramListWidget, self).__init__(parent)
        self.current = current
        
        self.setUniformItemSizes(True)
        self.setViewMode(QListView.ListMode)
        self.setMovement(QListView.Static)

        # react on clicks
        self.itemClicked.connect(self.onItemClicked)

        selected = None
        for f in files:
            item = QListWidgetItem(self.htmlDecode(f[1]))
            item.setData(Qt.UserRole, f)
            if(f[0] == current[0]): selected = item
            self.addItem(item);

        # highlight current program
        self.setCurrentItem(selected)

    def htmlDecode(self, str):
        return str.replace("&quot;", '"').replace("&#39;", "'").replace("&lt;", '<').replace("&gt;", '>').replace("&amp;", '&');
    
    def onItemClicked(self, item):
        prg = item.data(Qt.UserRole)
        if(prg[0] != self.current[0]):
            self.selected.emit(prg)

class SelectionDialog(TouchDialog):
    selection_changed = pyqtSignal(list)

    def __init__(self, files, current, parent):
        TouchDialog.__init__(self, QCoreApplication.translate("Selection", "Program"), parent)
        self.vbox = QVBoxLayout()

        self.prglist = ProgramListWidget(files, current, self)
        self.prglist.selected.connect(self.on_selection_changed);
        self.vbox.addWidget(self.prglist)

        self.centralWidget.setLayout(self.vbox)

    def on_selection_changed(self, prg):
        self.selection_changed.emit(prg)
        self.close()

# a button that sends resize events
class BricklyPushButton(QPushButton):
    resize = pyqtSignal()

    def __init__(self, str, parent=None):
        QPushButton.__init__(self, str, parent)
        self.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        if event.type() == event.Resize:
            self.resize.emit()
        return False

# a textedit with overlayed button
class BricklyTextEdit(QPlainTextEdit):
    run = pyqtSignal()
    
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        self.installEventFilter(self)
        self.setMaximumBlockCount(MAX_TEXT_LINES)
        self.setStyleSheet("QPlainTextEdit { font: 12px; }")
 
        self.run_but = BricklyPushButton(QCoreApplication.translate("Menu","Run"), self)
        self.run_but.clicked.connect(self.on_run_clicked)
        self.run_but.resize.connect(self.pos_button)
        style = "QPushButton { padding: 8; background-color: #5c96cc; }"
        self.run_but.setStyleSheet(style)

        self.pos_button()
        
    def pos_button(self):
        self.run_but.move((self.width()-self.run_but.width())/2,
                          (self.height()-2*self.run_but.height()));
        
    def on_run_clicked(self):
        self.run.emit()

    def eventFilter(self, obj, event):
        if event.type() == event.Resize:
            self.pos_button()
        return False

    def but_show(self, show=True):
        if show: self.run_but.show()
        else:    self.run_but.hide()

class Application(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)

        translator = QTranslator()
        path = os.path.dirname(os.path.realpath(__file__))
        translator.load(QLocale.system(), os.path.join(path, "brickly_"))
        self.installTranslator(translator)

        # start the websocket server listening for web clients to connect
        self.ws = WebsocketServerThread()
        self.ws.start()
        self.ws.command.connect(self.on_command)
        self.ws.setting.connect(self.on_setting)
        self.ws.client_connected.connect(self.on_client_connected)
        self.ws.python_code.connect(self.on_python_code)        # received python code
        self.ws.blockly_code.connect(self.on_blockly_code)      # received blockly code
        self.ws.program_name.connect(self.on_program_name)
        self.ws.plugin.connect(self.on_plugin)

        # start joystick monitoring
        self.joystick = QJoystick(self)

        # create the empty main window
        self.w = TouchWindow("Brickly")

        # default settings that may later be overwritten by browser
        self.settings = { }
        self.program_name = [ "brickly-0.xml", "Brickly" ]
        self.load_settings_js()

        # create the main menu
        menu = self.w.addMenu()
        self.menu_run = menu.addAction(QCoreApplication.translate("Menu","Run"))
        self.menu_run.triggered.connect(self.on_menu_run)
        self.menu_select = menu.addAction(QCoreApplication.translate("Menu","Select..."))
        self.menu_select.triggered.connect(self.on_menu_select)

        #
        
        # the program text output screen
        self.text = BricklyTextEdit()
        self.text.setReadOnly(True)
        self.text.run.connect(self.on_run_clicked)
        
        self.w.setCentralWidget(self.text)

        # a timer to read the ui output queue and to update
        # the screen
        self.ui_queue = queue.Queue()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(10)
        
        # start the run thread executing the blockly code
        self.thread = RunThread(self.ws, self.ui_queue)
        self.thread.setJoystick(self.joystick)
        self.thread.done.connect(self.on_program_ended)
        self.ws.speed_changed.connect(self.thread.set_speed)
        self.ws.plugin_cmd.connect(self.thread.on_plugin_cmd)

        self.w.show()
        self.exec_()        

        self.ws.stop()

    def delete_file(self, name):
        path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(path, USER_PROGRAMS, name)
        if os.path.isfile(fname): os.remove(fname)

    def write_to_file(self, name, data):
        path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(path, USER_PROGRAMS, name)
        with open(fname, 'w', encoding="UTF-8") as f:
            f.write(data)
            f.close()

    def on_client_connected(self, connected):
        # on connection tell browser whether code is being executed
        # and whether we are connected to TXT hardware so it can update
        # the toolbox if not
        if connected:
            self.ws.send(json.dumps( { "running": self.thread.isRunning() } ))
            self.ws.send(json.dumps( { "txt": self.thread.txt != None } )) 
#            self.ws.send(json.dumps( { "txt": True } ))   # always report to be a TXT

        # disable local program selection while connected
        self.menu_select.setEnabled(not connected);

    def on_python_code(self, str):
        # store python code under same name as blockly code. But use py extension
        fname = os.path.splitext(self.program_name[0])[0] + ".py"
        self.write_to_file(fname, str)
        
    def on_blockly_code(self, str):
        self.write_to_file(self.program_name[0], str)

    def on_plugin(self, name, data):
        # plugin installtion is solved really trivial: The plugin is being written
        # to the sd card and the program is being stopped. It's up to the browser
        # to restart it afterwards. Not a nice solution but useful ...
        print("Installing plugin ...", name)
        path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(path, "plugins", name + ".xml")
        with open(fname, 'w', encoding="UTF-8") as f:
            f.write(data)
            f.close()

        # and make sure the plugin appears in the plugins.list
        
        # read the plugins file
        path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(path, "plugins", "plugins.list")
        plugin_names = [ ]
        try:
            with open(fname) as f:
                for line in f:
                    l = line.split(';')[0].strip()
                    if(len(l) > 0):
                        plugin_names.append(l)
                f.close()
        except:
            return

        if not name in plugin_names:
            with open(fname, 'a', encoding="UTF-8") as f:
                print(name, file=f)
                f.close()

        # close app
        self.w.close()
        
    def on_setting(self, setting):
        # received settings from web browser
        for i in setting.keys():
            self.settings[i] = setting[i]

    def on_command(self, str):
        # handle commands received from browser
        if str == "run":  self.program_run()
        if str == "stop": self.thread.stop()
        if str == "delete": self.program_delete()
        if str == "save_settings": self.save_settings()
        if str == "list_program_files": self.cmd_list_programs()

    def save_settings(self):
        # save current settings
        settings = ""
        for i in self.settings:
            settings += "var " + i + " = "
            if type(self.settings[i]) is str:
                settings += "'"+ self.settings[i]+"'"
            else:
                settings += str(self.settings[i])
            settings += ";\n"

        self.write_to_file("settings.js", settings)

    def on_timer(self):
        while not self.ui_queue.empty():
            # get from queue
            e = self.ui_queue.get()

            # strings are just sent
            if type(e) is str:
                self.append(e)
            else:
                if 'cmd' in e:
                    if e['cmd'] == "clear":
                        self.text.clear();
                if 'text_color' in e:
                    self.append(e['text_color'][1], e['text_color'][0])

    def append(self, str, color=None):
        self.text.moveCursor(QTextCursor.End)
        if not hasattr(self, 'tf') or not self.tf:
            self.tf = self.text.currentCharFormat()
            self.tf.setFontWeight(QFont.Bold);

        if color:
            tf = self.text.currentCharFormat()
            tf.setForeground(QBrush(QColor(color)))
            self.text.textCursor().insertText(str, tf);
        else:
            self.text.textCursor().insertText(str, self.tf);

    def on_program_ended(self):
        self.menu_run.setText(QCoreApplication.translate("Menu","Run"))

        # bring start button to top
        self.text.but_show(True);
        
    def program_delete(self):
        # delete the blockly xml file ...
        self.delete_file(self.program_name[0])
        # ... and the generated python as well
        self.delete_file(os.path.splitext(self.program_name[0])[0] + ".py")

    def program_run(self):
        # bring text view to top
        self.text.but_show(False);

        # change "Run" to "Stop!"
        self.menu_run.setText(QCoreApplication.translate("Menu","Stop!"))
        
        # clear screen
        self.ws.send(json.dumps( { "gui_cmd": "clear" } ))
        self.text.clear()

        # and tell web gui that the program now runs
        self.ws.send(json.dumps( { "gui_cmd": "run" } ))
        
        # and start thread (again)
        self.thread.set_program_name(self.program_name)
        self.thread.start()

    def program_stop(self):
        # the web browser is asking to stop the current program
        # the GUI will be updated once the thread has stoppped
        self.thread.stop()

    def on_run_clicked(self):
        if not self.thread.isRunning():
            self.program_run()
        
    def on_menu_run(self):
        # the local user has selected the run/stop menu entry
        # on the touchscreen
        if self.thread.isRunning():
            self.program_stop()
        else:
            self.program_run()

    def on_menu_select(self):
        program_files = self.get_program_list()
        
        dialog = SelectionDialog(program_files, self.program_name, self.w)
        dialog.selection_changed.connect(self.on_program_changed)
        dialog.exec_()

    def set_program(self, prg):
        self.program_name = prg

        # the label in the title bar seems to decode html. But it does not
        # decode &quot;, &amp; and &#39; ... 
        self.w.titlebar.setText(prg[1].replace("&quot;", '"').replace("&amp;", '&').replace("&#39;", "'"))
        
    def on_program_changed(self, prg):
        self.set_program(prg)
        self.text.clear()
        self.program_run()
        
    def get_program_list(self):
        # search for all brickly programs in current user dir and return 
        # their file names and the embedded program names
        program_files = []
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), USER_PROGRAMS)
        files = [f for f in os.listdir(path) if re.match(r'^brickly-[0-9]*\.xml$', f)]
        for f in files:
            # use file name as program name as default ...
            name = os.path.splitext(f)[0]
            
            # ... but then try to extract the program name from the xml
            root = xml.etree.ElementTree.parse(os.path.join(path, f)).getroot()
            for child in root:
                # remove any namespace from the tag
                if '}' in child.tag: child.tag = child.tag.split('}', 1)[1]
                if child.tag == "settings" and 'name' in child.attrib:
                    name = child.attrib['name']
                    
            program_files.append( [f, name] )

        return program_files;

    def cmd_list_programs(self):
        # the browser client has requested a list of all user program files
        program_files = self.get_program_list()

        # send whole list of files as json
        self.ws.send(json.dumps( { "program_files": program_files } ))

    def on_program_name(self, x):
        # x[0] is the file name
        # x[1] is the internal program name

        # check if program name has changed and erase screen if yes
        if self.program_name != x:
            self.set_program(x)        
            self.text.clear()

        # also store the current program name in the settings
        self.on_setting( { "program_file_name": x[0], "program_name": x[1] } );

        # load the javascript settings file to be able to use it's contents
        # in stand-alone mode as well. Especially the name of the current
        # program 
    def load_settings_js(self):
        fname = os.path.join(os.path.dirname(os.path.realpath(__file__)), USER_PROGRAMS, "settings.js")
        if os.path.isfile(fname):
            # load and execute locally stored blockly code
            with open(fname, encoding="UTF-8") as f:
                for l in f:
                    parts = l.split('=')
                    name = parts[0].strip().split()[1];
                    value = parts[1].strip().rstrip('; ').strip('"\'');

                    # we are interested in the 'program_file_name' only
                    if(name == "program_file_name"):
                        self.program_name[0] = value;
                    if(name == "program_name"):
                        self.program_name[1] = value;
                    if(name == "skill"):
                        self.settings['skill'] = int(value)
                    if(name == "lang"):
                        self.settings['lang'] = value

        # make sure window title gets updated
        self.set_program(self.program_name)
        
if __name__ == "__main__":
    Application(sys.argv)
