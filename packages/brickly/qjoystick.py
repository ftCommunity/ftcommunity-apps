# -*- coding: utf-8 -*-
#
# QT derived linux joystick class by Till Harbaum
# Based upon https://gist.github.com/rdb/8864666
#
# Released by rdb under the Unlicense (unlicense.org)
# Based on information from:
# https://www.kernel.org/doc/Documentation/input/joystick-api.txt

# todo: gracefully handle unplugged joysticks

import os, struct, array, time
from fcntl import ioctl

try:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
except:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    

DEV_DIR = '/dev/input'

# one thread is created for each joystick which is being 
# monitored
class JoystickThread(QThread):
    button_changed = pyqtSignal(object, str, bool)
    axis_changed = pyqtSignal(object, str, float)
    disconnected = pyqtSignal(object)
    
    def __init__(self, device):
        super(JoystickThread,self).__init__()
        self.device = device
        self.running = True

    def run(self):
        while self.running:
            # gracefully handle unplugged devices
            try:
                evbuf = self.device["jsdev"].read(8)
            except OSError:
                self.disconnected.emit(self.device)
                self.running = False

            if evbuf:
                time, value, type, number = struct.unpack('IhBB', evbuf)
                
                if type & 0x01:
                    if number < len(self.device["button"]):
                        button = self.device["button"][number]["name"]
                        self.device["button"][number]["value"] = value
                        self.button_changed.emit(self.device, button, value)

                if type & 0x02:
                    if number < len(self.device["axis"]):
                        axis = self.device["axis"][number]["name"]
                        fvalue = value / 32767.0
                        self.device["axis"][number]["value"] = fvalue
                        self.axis_changed.emit(self.device, axis, fvalue)

# one thread permananently searches for new joysticks
class JoystickDetectThread(QThread):
    new_device = pyqtSignal(str)
    device_gone = pyqtSignal(str)

    def __init__(self):
        super(JoystickDetectThread,self).__init__()
        self.running = True
        self.detected = []

    def run(self):
        while self.running:
            # get list of currently know devices
            det = []
            for i in self.detected:
                det.append(i)

            for fn in os.listdir(DEV_DIR):
                if fn.startswith('js'):
                    if os.access(os.path.join(DEV_DIR, fn), os.R_OK):
                        if not fn in self.detected:
                            self.new_device.emit(fn)
                            self.detected.append(fn)
                        if fn in det:
                            det.remove(fn)

            # det will now only contain those devices that don't
            # exist anymore
            for fn in det:
                self.device_gone.emit(fn)
                self.detected.remove(fn)

            time.sleep(1)

    def remove(self, fn):
        self.detectected.remove(fn)

class QJoystick(QObject):
    button_changed = pyqtSignal(object, str, bool)
    axis_changed = pyqtSignal(object, str, float)
    
    def __init__(self, parent=None):
        super(QJoystick,self).__init__(parent)
        self.devices = []
        
        self.dectect_thread = JoystickDetectThread()
        self.dectect_thread.new_device.connect(self.on_new_device)
        self.dectect_thread.device_gone.connect(self.on_device_removed)
        self.dectect_thread.start()
        
    def on_device_removed(self, fn):
        for i in self.devices:
            if i["id"] == fn:
                self.on_disconnect(i)

    def on_new_device(self, fn):
        device = { }
        device["id"] = fn
                
        # We'll store the states here.
        device["axis"] = [ ]
        device["button"] = [ ]

        # Open the joystick device.
        device["jsdev"] = open(os.path.join(DEV_DIR, fn), 'rb')

        # Get the device name.
        buf = bytearray(64)
        ioctl(device["jsdev"], 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
        device["name"] = buf.decode("utf-8").strip('\x00')

        # Get number of axes and buttons.
        buf = bytearray(1)
        ioctl(device["jsdev"], 0x80016a11, buf) # JSIOCGAXES
        num_axes = buf[0]

        buf = bytearray(1)
        ioctl(device["jsdev"], 0x80016a12, buf) # JSIOCGBUTTONS
        num_buttons = buf[0]

        # Get the axis map.
        buf = bytearray(0x40)
        ioctl(device["jsdev"], 0x80406a32, buf) # JSIOCGAXMAP

        for axis in buf[:num_axes]:
            device["axis"].append({ "name": self.get_axis_name(axis), "value": 0.0 })

        # Get the button map.
        buf = array.array('H', [0] * 200)
        ioctl(device["jsdev"], 0x80406a34, buf) # JSIOCGBTNMAP

        for btn in buf[:num_buttons]:
            device["button"].append({ "name": self.get_button_name(btn), "value": 0 })

        # create a thread for every joystick
        device["thread"] = JoystickThread(device)
        device["thread"].button_changed.connect(self.on_button_changed)
        device["thread"].axis_changed.connect(self.on_axis_changed)
        device["thread"].disconnected.connect(self.on_disconnect)
        device["thread"].start()

        self.devices.append(device)

    def on_disconnect(self, dev):
        self.devices.remove(dev)

    def on_button_changed(self, dev, name, value):
        self.button_changed.emit(dev, name, value)
                
    def on_axis_changed(self, dev, name, value):
        self.axis_changed.emit(dev, name, value)
        
    def button(self, dev, name):
        if not dev:
            # if no device was given use the newest one
            if not len(self.devices):
                return None
            else:
                dev = self.devices[-1]

        values = [d["value"] for d in dev["button"] if d['name'] == name]
        if len(values) == 0: return None
        return values[0]
        
    def axis(self, dev, name):
        if not dev:
            # if no device was given use the newest one
            if not len(self.devices):
                return None
            else:
                dev = self.devices[-1]

        values = [d["value"] for d in dev["axis"] if d['name'] == name]
        if len(values) == 0: return None
        return values[0]
        
    def joysticks(self):
        return self.devices
    
    def get_axis_name(self, axis):
        # These constants were borrowed from linux/input.h
        axis_names = {
            0x00 : 'x',
            0x01 : 'y',
            0x02 : 'z',
            0x03 : 'rx',
            0x04 : 'ry',
            0x05 : 'rz',
            0x06 : 'trottle',
            0x07 : 'rudder',
            0x08 : 'wheel',
            0x09 : 'gas',
            0x0a : 'brake',
            0x10 : 'hat0x',
            0x11 : 'hat0y',
            0x12 : 'hat1x',
            0x13 : 'hat1y',
            0x14 : 'hat2x',
            0x15 : 'hat2y',
            0x16 : 'hat3x',
            0x17 : 'hat3y',
            0x18 : 'pressure',
            0x19 : 'distance',
            0x1a : 'tilt_x',
            0x1b : 'tilt_y',
            0x1c : 'tool_width',
            0x20 : 'volume',
            0x28 : 'misc',
        }

        if axis in axis_names:
            return axis_names[axis]
        else:
            return 'unknown(0x%02x)' % axis

    def get_button_name(self, btn):
        button_names = {
            0x120 : 'trigger',
            0x121 : 'thumb',
            0x122 : 'thumb2',
            0x123 : 'top',
            0x124 : 'top2',
            0x125 : 'pinkie',
            0x126 : 'base',
            0x127 : 'base2',
            0x128 : 'base3',
            0x129 : 'base4',
            0x12a : 'base5',
            0x12b : 'base6',
            0x12f : 'dead',
            0x130 : 'a',
            0x131 : 'b',
            0x132 : 'c',
            0x133 : 'x',
            0x134 : 'y',
            0x135 : 'z',
            0x136 : 'tl',
            0x137 : 'tr',
            0x138 : 'tl2',
            0x139 : 'tr2',
            0x13a : 'select',
            0x13b : 'start',
            0x13c : 'mode',
            0x13d : 'thumbl',
            0x13e : 'thumbr',
                    
            0x220 : 'dpad_up',
            0x221 : 'dpad_down',
            0x222 : 'dpad_left',
            0x223 : 'dpad_right',
                    
            # XBox 360 controller uses these codes.
            0x2c0 : 'dpad_left',
            0x2c1 : 'dpad_right',
            0x2c2 : 'dpad_up',
            0x2c3 : 'dpad_down',
        }

        if btn in button_names:
            return button_names[btn]
        else:
            return 'unknown(0x%03x)' % btn
