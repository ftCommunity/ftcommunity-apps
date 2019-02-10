#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
import ftrobopy
import time

__author__     = "Leon Schnieber"
__copyright__  = "Copyright 2018-2019"
__credits__    = "fischertechnik GmbH"
__maintainer__ = "Leon Schnieber"
__email__      = "olaginos-buero@outlook.de"
__status__     = "Developement"


class RoboProIOWrap(object):
    """
    This class handles all communication between the main library and the IOs of
    the different controllers. It can be modified if another controller-library
    is used.
    """


    def __init__(self, ifconfig):
        """
        ifconfig Variable-Format:
        Interface-Identifier as key, link to IO-Library as value
        config = {
        "IF1": ftrobopy.ftrobopy('192.168.7.2'),
        "EM1": ftrobopy.ftrobopy('192.168.8.2'),
        …
        "EM8": fttxpy.fttxpy(…),
        }
        """
        self.ifaces = {}
        if type(ifconfig) is dict and len > 1:  # a bit of checking before adding the external io-Wraps to the systems
            for ifconf in ifconfig:
                if ifconf in ["IF1", "EM1", "EM2", "EM3", "EM4", "EM5", "EM6", "EM7", "EM8"]:
                    self.ifaces[ifconf] = ifconfig[ifconf]
        self.ifaces["IF1"] = ftrobopy.ftrobopy("auto")
        time.sleep(0.5)

    def setSensorType(self, IFaceNumber, IFacePortNo, IFacePortType):
        pass

    def getSensorValue(self, IFaceNumber, IFacePortNo, IFacePortMode):
        """
        IFaceNumber-Values:
        IF1 = Master

        IFacePortNo-Values:
        I1 = 160
        I2 = 161
        …
        I8 = 167

        IFacePortMode-Values:
        0  = D 10V   Sensor-Type  6   (Spursensor)
        1  = D 5k    Sensor-Types 1-3 (Taster, Fototransitor, Reed-Kontakt)
        3  = A 10V   Sensor-Type  8   (Farbsensor)
        4  = A 5k    Sensor-Types 4-5 (NTC-Widerstand, Fotowiderstand)
        10 = Ultra…  Sensor-Type  7   (Abstandssensor)
        """
        iface = self.ifaces[IFaceNumber]
        if IFacePortMode == 1:  # digital 5k
            sensor = iface.input(IFacePortNo)
            value = sensor.state()
        elif IFacePortMode == 0: # spursensor
            sensor = iface.trailfollower(IFacePortNo)
            value = sensor.state()
        elif IFacePortMode == 3: # farbsensor
            sensor = iface.colorsensor(IFacePortNo)
            value = sensor.value()
        elif IFacePortMode == 4: # analog 5k
            sensor = iface.resistor(IFacePortNo)
            value = sensor.value()
        elif IFacePortMode == 10: # ultrasonic
            sensor = iface.ultrasonic(IFacePortNo)
            value = sensor.distance()
        return value

    def setOutputType(self, IFaceNumber, IFacePortNo, IFacePortType):
        pass

    def setOutputValue(self, IFaceNumber, IFacePortNo, IFacePortSettings):
        """
        Values of IFaceNumber:
        IF1 = Master
        …

        IFacePortNo-Values:
        0   = M1
        1   = M2
        …
        3   = M4
        4   = O1
        5   = O2
        …
        11  = O8

        IFacePortSettings: (dict)
        ["commandType"]   Language dependent set of commands.
        ["value"]         Ranges from 0 to 512

        List of availiable Command-types:
        "cw"   = CW Mot   (v=n)
        "ccw"  = CCW Mot  (v=n)
        "Stop" = Stop Mot (v=0)
        optionally, not known yet
        "On"   = On IO    (v=n)
        "Off"  = Off IO   (v=0)
        """
        iface = self.ifaces[IFaceNumber]
        val = int(IFacePortSettings["value"])
        if val > 512:
            val = 512
        if val < 0:
            val = 0
        if IFacePortNo >= 0 and IFacePortNo <= 3:
            output = iface.motor(IFacePortNo+1)
            if IFacePortSettings["commandType"] in ["Links", "ccw"]:
                output.setSpeed(-val)
            else:
                output.setSpeed(val)
            if "distance" in IFacePortSettings:
                if "syncTo" in IFacePortSettings:
                    output.setDistance(
                        IFacePortSettings["distance"],
                        syncto=iface.motor(IFacePortSettings["syncTo"]+1)
                    )
                else:
                    output.setDistance(IFacePortSettings["distance"])
        elif IFacePortNo >= 4 and IFacePortNo <= 11:
            output = iface.output(IFacePortNo-3)
            output.setLevel(IFacePortSettings["value"])
        if "sleep" in IFacePortSettings and "distance" in IFacePortSettings:
            while output.getCurrentDistance() < IFacePortSettings["distance"]:
                time.sleep(0.01)
            output.stop()

    def setSound(self, IFaceNumber, soundNumber=0, wait=False, repeat=1):
        iface = self.ifaces[IFaceNumber]
        iface.play_sound(int(soundNumber), int(repeat))
        if wait == True:
            while iface.sound_finished() == False:
                time.sleep(0.01)
