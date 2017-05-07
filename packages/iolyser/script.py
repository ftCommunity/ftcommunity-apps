#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys
import ftrobopy
import time
#import camera
#import threading
from camera import *
from TouchStyle import *

#style section
BUTTON_STYLE = """
QPushButton {width: 100px; font-size: 13px; color:white; border-radius: 0; border-style: none; height: 90%}
QPushButton:pressed {background-color: #123456}
"""

BIG_LABEL = """
QLabel {font-size: 18px; color:white}
"""

SMALL_LABEL = """
QLabel {text-align: center; font-size: 15px; color:white}
"""

TAB_STYLE = """
QTabBar {color: white; font: 20px}
QTabBar::tab {border: none; border-radius: none}
QTabBar::tab:!selected {color:lightgrey;}
"""




class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)

        #create the window
        window = TouchWindow("IOlyser")



        #Start filling the first tab
        page_1 = QWidget()
        vbox = QVBoxLayout()

        n = 1
        self.inputListObject = []
        while n <= 8:
            #create a sub-box for each line
            hbox = QHBoxLayout()
            #Display Title for each Input
            title = QLabel("I"+str(n))
            title.setStyleSheet(BIG_LABEL)
            hbox.addWidget(title)
            #Display value-element for each Input
            value = QLabel("NULL")
            value.setStyleSheet(SMALL_LABEL)
            hbox.addWidget(value)
            #Display Settings-Button for each Input
            type = QPushButton("pushbutton")
            type.setStyleSheet(BUTTON_STYLE)
            type.clicked.connect(self.__toggleInputType)
            hbox.addWidget(type)

            self.inputListObject.append([n,type,value]) #Add each line to a list for some other functions
            #Add the "line" to the Tab
            vbox.addLayout(hbox)

            n = n + 1
        #Add the first Tab
        page_1.setLayout(vbox)

        #######################################################################################################################################
        #Start filling the second tab
        page_2 = QWidget()
        vbox = QVBoxLayout()

        n = 1
        self.outputListObject = []
        self.outputNames = {'1': ['O1', 'O2'], '2': ['O3', 'O4'], '3': ['O5', 'O6'], '4': ['O7', 'O8']}
        while n <= 4:
            #Create a sub-box for each motor
            hbox = QHBoxLayout()
            #Button for "turn left"
            left = QPushButton("left / " + self.outputNames[str(n)][0])
            left.setStyleSheet(BUTTON_STYLE)
            left.pressed.connect(self.__switchMotorOn)
            left.released.connect(self.__switchMotorOff)
            hbox.addWidget(left)
            #Label for "motor"
            label = QLabel("M"+str(n))
            label.setStyleSheet(BIG_LABEL)
            hbox.addWidget(label)
            #Botton for "turn right"
            right = QPushButton("right / " + self.outputNames[str(n)][1])
            right.setStyleSheet(BUTTON_STYLE)
            right.pressed.connect(self.__switchMotorOn)
            right.released.connect(self.__switchMotorOff)
            hbox.addWidget(right)

            speed = 512

            self.outputListObject.append([n,left,right,speed]) #Add each line to a list for some other functions
            #Add the "lines" to the Tab
            vbox.addLayout(hbox)

            n = n + 1
        page_2.setLayout(vbox)

        #########################################################################################################################################,
        page_3 = QWidget()
        vbox = QVBoxLayout()
        #Add camera element to the camera-page
        cam = CamWidget()
        vbox.addWidget(cam)


        page_3.setLayout(vbox)
        #########################################################################################################################################

        #Create the Tab-Element and add the pages to that
        self.tabBar = QTabWidget()
        self.tabBar.addTab(page_1,"Input")
        self.tabBar.addTab(page_2,"Output")
        self.tabBar.addTab(page_3,"Camera")
        self.tabBar.setStyleSheet(TAB_STYLE)
        #Add the Tab-widget to the Window
        window.setCentralWidget(self.tabBar)

        #Move the Block to the Display.
        window.show()
        #Call some background functions
        print("Execute things")
        self.__ioStart()
        self.__readerThread()
        print("Threadingcheck")
        print(self.tabBar.currentIndex())

        self.exec_()
    def __ioStart(self):
        self.io = ftrobopy.ftrobopy("127.0.0.1",65000)
        time.sleep(1)
    def __readerThread(self):
        print("Thread started.")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.__readerProcess)
        self.timer.start(10);

        #self.thread = threading.Thread(target=self.__readerProcess)
        #self.thread.start()

    def __readerProcess(self):
        #while True:
        if self.tabBar.currentIndex() == 0:
            #Process each line of Input and change their content
            for line in self.inputListObject:
                n = line[0] #Get the Input-number
                btn = line[1] #Get the Button (also the Type)
                value = line[2] #Get the Element to write to.

                #Get the mode of the input:
                type = btn.text()
                unit = ""
                #try:
                if type == "pushbutton":
                    sensor = self.io.input(n).state()
                elif type == "resistor":
                    try:
                        sensor = self.io.resistor(n).value()
                    except:
                        sensor = self.io.resistor(n).resistance()
                    unit = "Ohm"
                elif type == "ultrasonic":
                    sensor = self.io.ultrasonic(n).distance()
                    unit = "cm"
                elif type == "voltage":
                    sensor = self.io.voltage(n).voltage()
                    unit = "mV"
                elif type == "linesens":
                    sensor = self.io.trailfollower(n).state()
                else:
                    sensor = "NUL"
                # except:
                #     sensor = "N"



                value.setText(str(sensor) + str(unit))


    def __toggleInputType(self):
        #Get the object, which called this function
        rec = self.sender()
        #Find the object id in the self.inputListObject-list and update the value there
        #pushbutton, resistor5k,resistor15k,ultrasonic,voltage,linesens
        if rec.text() == "pushbutton":
            rec.setText("resistor")
        #elif rec.text() == "resistor5k":
        #   rec.setText("resistor15k")
        elif rec.text() == "resistor":
            rec.setText("ultrasonic")
        elif rec.text() == "ultrasonic":
            rec.setText("voltage")
        elif rec.text() == "voltage":
            rec.setText("linesens")
        elif rec.text() == "linesens":
            rec.setText("pushbutton")
        else:
            rec.setText("pushbutton")

    def __switchMotorOn(self):
        rec = self.sender()
        for mot in self.outputListObject:
            if rec == mot[1]:
                self.io.motor(mot[0]).setSpeed(mot[3])
            elif rec == mot[2]:
                self.io.motor(mot[0]).setSpeed(-mot[3])


    def __switchMotorOff(self):
        rec = self.sender()
        for mot in self.outputListObject:
            if rec == mot[1]:
                self.io.motor(mot[0]).stop()
            if rec == mot[2]:
                self.io.motor(mot[0]).stop()


if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
