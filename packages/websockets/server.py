#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import os, sys, time
import ftrobopy
from TxtStyle import *
import asyncio
import websockets

PORT = 9001
CLIENT = ""    # any client

# a seperate thread controls the websockets
class ServerThread(QThread):
    message = pyqtSignal(str)
    clients_changed = pyqtSignal(int)

    def __init__(self):
        super(ServerThread,self).__init__()
        self.clients = []

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        server = websockets.serve(self.handler, CLIENT, PORT)
        self.loop.run_until_complete(server)

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.loop.close()

    @asyncio.coroutine
    def handler(self, websocket, path):
        connected = True
        self.clients.append(websocket)
        self.clients_changed.emit(len(self.clients))

        while connected:
            try:
                msg = yield from websocket.recv()
                # forward message to main thread
                self.message.emit(msg)
                
            except websockets.exceptions.ConnectionClosed:
                self.clients.remove(websocket)
                self.clients_changed.emit(len(self.clients))
                connected = False

            finally:
                pass

    # send a message to all connected clients
    @asyncio.coroutine
    def broadcast(self, str):
        for i in self.clients:
            yield from i.send(str)

    # called whenever a message is to be broadcasted
    def on_message(self, str):
        # schedule message for transmission
        self.loop.call_soon_threadsafe(asyncio.async, self.broadcast(str))

class SmallLabel(QLabel):
    def __init__(self, str, parent=None):
        super(SmallLabel, self).__init__(str, parent)
        self.setObjectName("smalllabel")
        self.setAlignment(Qt.AlignLeft)

class StateWidget(QWidget):
    def __init__(self,title,val,parent=None):
        super(StateWidget,self).__init__(parent)
        hbox = QHBoxLayout()
        title_lbl = SmallLabel(title +":")
        hbox.addWidget(title_lbl)
        self.val = QLabel(val)
        self.val.setAlignment(Qt.AlignRight)
        hbox.addWidget(self.val)
        self.setLayout(hbox)

    def set(self, val):
        self.val.setText(val)

    def get(self):
        return self.val.text()

class FtcGuiApplication(TxtApplication):
    message = pyqtSignal(str)

    def __init__(self, args):
        TxtApplication.__init__(self, args)
        self.w = TxtWindow("WSDemo")

        txt_ip = os.environ.get('TXT_IP')
        if txt_ip == None: txt_ip = "localhost"
        try:
            self.txt = ftrobopy.ftrobopy(txt_ip, 65000)
        except:
            self.txt = None

        if self.txt:
            # all outputs normal mode
            M = [ self.txt.C_OUTPUT, self.txt.C_OUTPUT, 
                  self.txt.C_OUTPUT, self.txt.C_OUTPUT ]
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
            
        # poll button at 10 Hz
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.do_timer)
        self.timer.start(100);

        # create the websocket server thread and connect it via some signal
        thread = ServerThread()
        thread.start()
        # connection to server thread to transmit data
        thread.connect(self, SIGNAL('message(QString)'), thread.on_message)
        # connection to server thread to receive data
        thread.connect(thread, SIGNAL('message(QString)'), self.on_web_rx)
        # connection to server thread to receive client number
        thread.connect(thread, SIGNAL('clients_changed(int)'), self.on_web_clients_changed)

        # add a simple gui with a button and one label
        vbox = QVBoxLayout()

        # keep track of I/O state
        self.state = { 'I1':0, 'O1':0, 'O2':0 }

        self.clients = StateWidget("Web clients", "0")
        vbox.addWidget(self.clients)

        self.state_i1 = StateWidget("Input 1", "Off")
        vbox.addWidget(self.state_i1)

        self.state_o1 = StateWidget("Output 1", "Off")
        vbox.addWidget(self.state_o1)

        self.state_o2 = StateWidget("Output 2", "Off")
        vbox.addWidget(self.state_o2)

        # add a few buttons to control the outputs
        hbox_w = QWidget()
        hbox = QHBoxLayout()

        but_o1 = QPushButton("O1")
        but_o1.pressed.connect(self.on_button_pressed)
        but_o1.released.connect(self.on_button_released)
        hbox.addWidget(but_o1)

        but_o2 = QPushButton("O2")
        but_o2.pressed.connect(self.on_button_pressed)
        but_o2.released.connect(self.on_button_released)
        hbox.addWidget(but_o2)

        hbox_w.setLayout(hbox)

        vbox.addWidget(hbox_w)

        self.w.centralWidget.setLayout(vbox)
        
        self.w.show() 
        self.exec_()        

    # this clot is called whenever the number of web clients change
    def on_web_clients_changed(self, num):
        # check if number of clients has increased
        if num > int(self.clients.get()):
            # if yes re-send current state so all clients
            # (incl the new one) get the whole state
            for i in self.state:
                if self.state[i]:
                    self.message.emit(i+":On")
                else:
                    self.message.emit(i+":Off")

        # display new number of clients
        self.clients.set(str(num))

    # this slot is called whenever a message has been received
    # from any web client
    def on_web_rx(self, msg):
        port, state = msg.split(':')
        if state == "On": self.set_output(port, True)
        else:             self.set_output(port, False)

    def on_button_pressed(self):
        self.set_output(self.sender().text(), True)

    def on_button_released(self):
        self.set_output(self.sender().text(), False)

    def name2widget(self, name):
        if name == "I1": return self.state_i1
        if name == "O1": return self.state_o1
        if name == "O2": return self.state_o2
        return None

    def set_output(self, name, val):
        if val:
            self.state[name] += 1
            if self.state[name] == 1:
                self.name2widget(name).set("On")
                self.message.emit(name+":On")

                # set txt's physical outputs accordingly
                if self.txt:
                    if name == "O1": self.txt.setPwm(0,512)
                    if name == "O2": self.txt.setPwm(1,512)
        else:
            self.state[name] -= 1
            if self.state[name] == 0:
                self.name2widget(name).set("Off")
                self.message.emit(name+":Off")

                # set txt's physical outputs accordingly
                if self.txt:
                    if name == "O1": self.txt.setPwm(0,0)
                    if name == "O2": self.txt.setPwm(1,0)

    # this timer regularily checks the input I1 for changes
    def do_timer(self):

        # poll input
        if self.txt:
            i1 = self.txt.getCurrentInput(0)
        else:
            i1 = True      # fake true input

        if self.state['I1'] != i1:
            self.state['I1'] = i1
            if self.state['I1']:
                self.name2widget('I1').set("On")
                self.message.emit("I1:On")
            else:
                self.name2widget('I1').set("Off")
                self.message.emit("I1:Off")
           
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
