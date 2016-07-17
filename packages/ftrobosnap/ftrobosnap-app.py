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
        pid_path = '/tmp/ftrobosnap.pid'
        pid = ''
        if os.path.exists(pid_path) == True:
            pid = os.popen('cat ' + pid_path).read()
        try:
            config = configparser.SafeConfigParser()
            config.read(global_config)
            language = config.get('general', 'language')
        except:
            pass
        if language == '' or language not in language_list:
            language = default_language
        if language == 'EN':
            if pid == '':
                str_lbl1 = 'ftrobosnap stopped'
            else:
                str_lbl1 = 'ftrobosnap is ready'
        elif language == 'DE':
            if pid == '':
                str_lbl1 = 'ftrobosnap ist gestoppt'
            else:
                str_lbl1 = 'ftrobosnap ist bereit'
        w = TxtWindow('Telegram')
        self.vbox = QVBoxLayout()
        self.vbox.addStretch()
        self.lbl1 = QLabel(str_lbl1)
        self.lbl1.setWordWrap(True)
        self.lbl1.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.lbl1)
        btn_start = QPushButton('START')
        btn_start.clicked.connect(self.on_button_clicked_start)
        self.vbox.addWidget(btn_start)
        btn_stop = QPushButton('STOP')
        btn_stop.clicked.connect(self.on_button_clicked_stop)
        self.vbox.addWidget(btn_stop)
        w.centralWidget.setLayout(self.vbox)
        w.show()
        self.exec_()

    def on_button_clicked_start(self):
        print('start')
        pid_path = '/tmp/ftrobosnap.pid'
        pid = ''
        if os.path.exists(pid_path) == True:
            pid = os.popen('cat ' + pid_path).read()
        if pid == '':
            print('START')
            os.system('sh /media/sdcard/apps/599047da-5f01-4a15-a94f-0fc14cc4a88b/ftrobosnap-start.sh')
        else:
            print('ALREADY STARTED')

    def on_button_clicked_stop(self):
        print('stop')
        pid_path = '/tmp/ftrobosnap.pid'
        pid = ''
        if os.path.exists(pid_path) == True:
            pid = os.popen('cat ' + pid_path).read()
        if pid != '':
            print('KILLED')
            os.system('kill ' + pid)
            os.system('rm /tmp/ftrobosnap.pid')
        else:
            print('ALREDY KILLED')
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
