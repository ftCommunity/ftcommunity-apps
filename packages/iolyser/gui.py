#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
from TouchStyle import *

__author__     = "Leon Schnieber"
__email__      = "olaginos-buero@outlook.de"
__status__     = "Production"


class GeneralIOObject():
    STYLE_BIG_LABEL = """
        QLabel {
            font-size: 18px;
            color: white;
            }
    """

    STYLE_SMALL_LABEL = """
        QLabel {
            text-align: center;
            font-size: 15px;
            color:white
            }
    """

    STYLE_BUTTON = """
        QPushButton {
            width: 100px;
            height: 90%;
            font-size: 13px;
            color: white;
            border-radius: 0;
            border-style: none;
            }
        QPushButton:pressed {
            background-color: #123456;
            }
    """

class SensorInputObject(GeneralIOObject):

    STATUS_STATE_DB = ["pushbutton", "resistor", "ultrasonic", "voltage", "linesens"]

    def __init__(self, ioObject, ioPortNo):
        """
        Creates one Sensor-Row consisting of three columns: Label, Value and a
        button to switch between different input-types.
        """

        self.input_type = self.STATUS_STATE_DB[0]

        self.ioObject = ioObject
        self.ioPortNo = ioPortNo

        self.q_box = QHBoxLayout()

        title = "I" + str(self.ioPortNo)
        self.__q_label = QLabel(title)
        self.__q_label.setStyleSheet(self.STYLE_BIG_LABEL)
        self.q_box.addWidget(self.__q_label)

        self.__q_value = QLabel("NULL")
        self.__q_value.setStyleSheet(self.STYLE_SMALL_LABEL)
        self.q_box.addWidget(self.__q_value)

        self.__q_typeSelect = QPushButton("pushbutton")
        self.__q_typeSelect.setStyleSheet(self.STYLE_BUTTON)
        self.__q_typeSelect.clicked.connect(self.__toggleSelectButton)
        self.q_box.addWidget(self.__q_typeSelect)

    def readSensor(self):
        io = self.ioObject
        n = self.ioPortNo
        if self.input_type == "pushbutton":
            value = io.input(n).state()
            unit = ""
        elif self.input_type == "resistor":
            try:
                value = io.resistor(n).value()
            except NameError:
                value = io.resistor(n).resistance()
            unit = "Ω"
        elif self.input_type == "ultrasonic":
            value = io.ultrasonic(n).distance()
            unit = "cm"
        elif self.input_type == "voltage":
            value = io.voltage(n).voltage()
            unit = "mV"
        elif self.input_type == "linesens":
            value = io.trailfollower(n).state()
            unit = ""
        else:
            value = "Err."
            unit = ""

        labelText = str(value) + " " + unit
        self.__q_value.setText(labelText)

    def __toggleSelectButton(self):
        if self.input_type in self.STATUS_STATE_DB:
            idx = self.STATUS_STATE_DB.index(self.input_type) + 1
            if len(self.STATUS_STATE_DB) <= idx:
                idx = 0
            self.input_type = self.STATUS_STATE_DB[idx]
        else:
            self.input_type = self.STATUS_STATE_DB[0]

        self.__q_typeSelect.setText(self.input_type)


class ActorOutputObject(GeneralIOObject):

    SPEED = 512

    STYLE_BUTTON_RIGHT_ALIGNED = """
        QPushButton {
            width: 100px;
            height: 90%;
            font-size: 13px;
            text-align: left;
            color: white;
            border-radius: 0;
            border-style: none;
            }
        QPushButton:pressed {
            background-color: #123456;
            }
    """

    def __init__(self, ioObject, ioPortNo):

        self.ioObject = ioObject
        self.ioPortNo = ioPortNo

        self.__motor = self.ioObject.motor(self.ioPortNo)

        self._counter_value = 0
        self.__motor.setDistance(1000)

        self.q_box = QHBoxLayout()


        self.__q_hCenterBox = QVBoxLayout()

        self.__q_label = QLabel("M" + str(ioPortNo))
        self.__q_label.setStyleSheet(self.STYLE_BIG_LABEL)
        self.__q_hCenterBox.addWidget(self.__q_label)

        self.__q_btnResetCounter = QPushButton("C" + str(ioPortNo) + ":\t 0")
        self.__q_btnResetCounter.setStyleSheet(self.STYLE_BUTTON_RIGHT_ALIGNED)
        self.__q_btnResetCounter.clicked.connect(self.__resetCounter)

        self.__q_hCenterBox.addWidget(self.__q_btnResetCounter)
        self.q_box.addLayout(self.__q_hCenterBox)


        self.__q_btnLeft = QPushButton("left / O" + str(ioPortNo*2-1))
        self.__q_btnLeft.setStyleSheet(self.STYLE_BUTTON)
        self.__q_btnLeft.pressed.connect(lambda: self.__switchMotorOn("left"))
        self.__q_btnLeft.released.connect(self.__switchMotorOff)
        self.q_box.addWidget(self.__q_btnLeft)


        self.__q_btnRight = QPushButton("right / O" + str(ioPortNo*2))
        self.__q_btnRight.setStyleSheet(self.STYLE_BUTTON)
        self.__q_btnRight.pressed.connect(lambda: self.__switchMotorOn("right"))
        self.__q_btnRight.released.connect(self.__switchMotorOff)
        self.q_box.addWidget(self.__q_btnRight)

    def readSensor(self):
        self._counter_value = self.__motor.getCurrentDistance()
        self.__q_btnResetCounter.setText("C" + str(self.ioPortNo) + ":\t " + str(self._counter_value))

    def __switchMotorOn(self, direction):
        if direction == "left":
            self.__motor.setSpeed(self.SPEED)
        else:
            self.__motor.setSpeed(-self.SPEED)

    def __switchMotorOff(self):
        print("stop called", self.ioPortNo)
        self.__motor.setSpeed(0)

    def __resetCounter(self):
        self.__motor.setDistance(0)
