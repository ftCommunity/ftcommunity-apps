#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys
import time
import ftrobopy
from gui import SensorInputObject, ActorOutputObject
from camera import *
from TouchStyle import *

__author__     = "Leon Schnieber"
__email__      = "olaginos-buero@outlook.de"
__status__     = "Production"

class FtcGuiApplication(TouchApplication):
    TAB_STYLE = """
        QTabBar {
            color: white;
            font: 20px
            }

        QTabBar::tab {
            border: none;
            border-radius: none
            }

        QTabBar::tab:!selected {
            color: lightgrey;
            }
    """

    def __init__(self, args):
        TouchApplication.__init__(self, args)

        self.__ioStart()

        window = TouchWindow("IOlyser")

        page_1 = QWidget()
        vbox = QVBoxLayout()

        self.obj_list_input = []
        for i in range(8):
            n = i + 1
            obj = SensorInputObject(self.io, n)
            vbox.addLayout(obj.q_box)

            self.obj_list_input.append(obj)

        # Add the first Tab
        page_1.setLayout(vbox)

        ########################################################################
        # Start filling the second tab
        page_2 = QWidget()
        vbox = QVBoxLayout()

        self.obj_list_output = []
        for i in range(4):
            n = i + 1
            obj = ActorOutputObject(self.io, n)
            vbox.addLayout(obj.q_box)

            self.obj_list_output.append(obj)

        page_2.setLayout(vbox)

        ########################################################################
        page_3 = QWidget()
        vbox = QVBoxLayout()
        # Add camera element to the camera-page
        cam = CamWidget()
        vbox.addWidget(cam)


        page_3.setLayout(vbox)
        ########################################################################

        # Create the Tab-Element and add the pages to that
        self.tabBar = QTabWidget()
        self.tabBar.addTab(page_1,"Input")
        self.tabBar.addTab(page_2,"Output")
        self.tabBar.addTab(page_3,"Camera")
        self.tabBar.setStyleSheet(self.TAB_STYLE)
        # Add the Tab-widget to the Window
        window.setCentralWidget(self.tabBar)

        # Move the Block to the Display.
        window.show()
        # Call some background functions
        self.__readerThread()
        print("Threadingcheck")

        self.exec_()

    def __ioStart(self):
        self.io = ftrobopy.ftrobopy("auto")
        time.sleep(1)

    def __readerThread(self):
        print("Thread started.")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.__readerProcess)
        self.timer.start(10)


    def __readerProcess(self):
        if self.tabBar.currentIndex() == 0:
            for line_obj in self.obj_list_input:
                line_obj.readSensor()
        if self.tabBar.currentIndex() == 1:
            for line_obj in self.obj_list_output:
                line_obj.readSensor()


if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
