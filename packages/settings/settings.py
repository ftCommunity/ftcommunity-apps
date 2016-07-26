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
        default_language = 'EN'
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
            str_lbl1 = 'Select your language:'
            str_lbl2 = 'Current language: EN'
            str_w = 'Settings'
        elif language == 'DE':
            str_lbl1 = 'Waehle deine Sprache:'
            str_lbl2 = 'Aktuelle Sprache: DE'
            str_w = 'Einstellungen'
        w = TxtWindow(str_w)
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
        btn_lang_EN = QPushButton('Language: EN')
        btn_lang_EN.clicked.connect(self.on_button_clicked_EN)
        self.vbox.addWidget(btn_lang_EN)
        btn_lang_DE = QPushButton('Sprache: DE')
        btn_lang_DE.clicked.connect(self.on_button_clicked_DE)
        self.vbox.addWidget(btn_lang_DE)
        w.centralWidget.setLayout(self.vbox)
        w.show()
        self.exec_()

    def set_language(self, language):
        Config = configparser.ConfigParser()
        cfgfile = open(configpath, 'w')
        Config.add_section('general')
        Config.set('general', 'language', language)
        Config.write(cfgfile)
        cfgfile.close()

    def on_button_clicked_DE(self):
        self.set_language('DE')

    def on_button_clicked_EN(self):
        self.set_language('EN')

if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
