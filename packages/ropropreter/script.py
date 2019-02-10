#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
from TouchStyle import *
from TouchAuxiliary import *
from roProgram import RoboProProgram
import os
from os import listdir as osList

__author__     = "Leon Schnieber"
__email__      = "olaginos-buero@outlook.de"
__status__     = "Developement"

class TouchGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)

        self.status = "nothing"

        self.window = TouchWindow("RoProPreter")
        self.mainBox = QHBoxLayout()
        self.subBoxA = QVBoxLayout()
        # # title
        label = QLabel("Programm auswählen:")
        self.subBoxA.addWidget(label)
        # file list
        pathadd = os.path.realpath(__file__).replace("script.py", "")
        fileList = osList(pathadd + "files/")
        self.listWidget = QListWidget()
        for fileName in fileList:
            item = QListWidgetItem(fileName)
            self.listWidget.addItem(item)
        self.subBoxA.addWidget(self.listWidget)
        # execute-button
        self.button = QPushButton(".rpp Ausführen")
        self.button.clicked.connect(self.executeButtonClick)
        self.subBoxA.addWidget(self.button)

        self.window.centralWidget.setLayout(self.subBoxA)
        self.window.show()
        self.exec_()

    def executeButtonClick(self):
        if len(self.listWidget.selectedItems()) == 1:
            item = self.listWidget.selectedItems()[0]
            filename = item.text()
            self.runProgram(filename)

    def runProgram(self, programName):
        if self.status == "nothing":
            self.button.setEnabled(False)
            self.button.setText(".rpp läuft!")
            pathadd = os.path.realpath(__file__).replace("script.py", "")
            ropro = RoboProProgram(pathadd + "files/" + programName)
            self.status = "running"
            ropro.run()
            self.button.setText("fertig! .rpp Ausführen")
            self.button.setEnabled(True)
            self.status = "nothing"


if __name__ == "__main__":
    TouchGuiApplication(sys.argv)
