#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys
import configparser
import os
from TxtStyle import *
global configpath
configpath = '/media/sdcard/data/config.conf'


class FtcGuiApplication(TxtApplication):

    def __init__(self, args):
        TxtApplication.__init__(self, args)
        global_config = '/media/sdcard/data/config.conf'
        language = ''
        default_language = ''
        language_list = ['EN', 'DE']
        try:
            config = configparser.SafeConfigParser()
            config.read(global_config)
            language = config.get('general', 'language')
        except:
            pass
        if language == '' or language not in language_list:
            language = default_language
        if language == 'EN':
            str_lbl1 = 'Press Buttons to start or stop Telegram service!'
            str_lbl2 = 'Info will follow!'
        elif language == 'DE':
            str_lbl1 = 'Druecke den entsprechenden Knopf, um den Telegram Dienst zu starten oder zu stoppen!'
            str_lbl2 = 'Info kommt noch!'
        w = TxtWindow('Telegram')
        self.vbox = QVBoxLayout()
        self.vbox.addStretch()
        self.lbl1 = QLabel(str_lbl1)
        self.lbl1.setObjectName("smalllabel")
        self.lbl1.setWordWrap(True)
        self.lbl1.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.lbl1)
        self.lbl2 = QLabel(str_lbl2)
        self.lbl2.setObjectName("smalllabel")
        self.lbl2.setWordWrap(True)
        self.lbl2.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.lbl2)
        btn_start = QPushButton('Language: EN')
        btn_start.clicked.connect(self.on_button_clicked_start)
        self.vbox.addWidget(btn_start)
        btn_stop = QPushButton('Sprache: DE')
        btn_stop.clicked.connect(self.on_button_clicked_stop)
        self.vbox.addWidget(btn_stop)
        w.centralWidget.setLayout(self.vbox)
        w.show()
        self.exec_()

    def on_button_clicked_start(self):
        print('start')

    def on_button_clicked_stop(self):
        print('stop')
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
