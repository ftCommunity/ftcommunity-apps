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
        pid_path = '/tmp/telegram.pid'
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
                str_lbl1 = 'Telegram stopped'
            else:
                str_lbl1 = 'Telegram is ready'
        elif language == 'DE':
            if pid == '':
                str_lbl1 = 'Telegram ist gestoppt'
            else:
                str_lbl1 = 'Telegram ist bereit'
        w = TxtWindow('Telegram')
        self.vbox = QVBoxLayout()
        self.vbox.addStretch()
        self.lbl1 = QLabel(str_lbl1)
        #self.lbl1.setObjectName("smalllabel")
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
        pid_path = '/tmp/telegram.pid'
        pid = ''
        if os.path.exists(pid_path) == True:
            pid = os.popen('cat ' + pid_path).read()
        if pid == '':
            print('START')
            os.system('sh /media/sdcard/apps/6026c098-cb9b-45da-9c8c-9d05eb44a4fd/telegram-start.sh')
        else:
            print('ALREADY STARTED')

    def on_button_clicked_stop(self):
        print('stop')
        pid_path = '/tmp/telegram.pid'
        pid = ''
        if os.path.exists(pid_path) == True:
            pid = os.popen('cat ' + pid_path).read()
        if pid != '':
            print('KILLED')
            os.system('kill ' + pid)
            os.system('rm /tmp/telegram.pid')
        else:
            print('ALREDY KILLED')
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
