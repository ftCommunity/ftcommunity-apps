#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys
from TxtStyle import *

class FtcGuiApplication(TxtApplication):
    def __init__(self, args):
        TxtApplication.__init__(self, args)

        # create the empty main window
        w = TxtWindow("Settings")
        vbox = QVBoxLayout()

        button_DE = QPushButton("Sprache: DE")
        button_DE.clicked.connect(self.on_button_clicked_DE)
        vbox.addWidget(button_DE)
        button_EN = QPushButton("Language: EN")
        button_EN.clicked.connect(self.on_button_clicked_EN)
        vbox.addWidget(button_EN)

        self.button_state = False

        w.centralWidget.setLayout(vbox)
        w.show()
        self.exec_()
    def on_button_clicked_DE(self):
        print('DE')
    def on_button_clicked_EN(self):
        print('EN')

if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
