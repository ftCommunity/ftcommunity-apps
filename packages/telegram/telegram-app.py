#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys
import configparser
import os
from TxtStyle import *
global configpath
configpath = '/media/sdcard/data/config.conf'


class SmallLabel(QLabel):

    def __init__(self, str, parent=None):
        super(SmallLabel, self).__init__(str, parent)
        self.setObjectName("smalllabel")
        self.setAlignment(Qt.AlignLeft)


class StateWidget(QWidget):

    def __init__(self, title, val, parent=None):
        super(StateWidget, self).__init__(parent)
        hbox = QHBoxLayout()
        title_lbl = SmallLabel(title + ":")
        hbox.addWidget(title_lbl)
        self.val = QLabel(val)
        self.val.setAlignment(Qt.AlignRight)
        hbox.addWidget(self.val)
        self.setLayout(hbox)

    def set(self, val):
        self.val.setText(val)

    def get(self):
        return self.val.text()


class FtcGuiApplication(TxtApplication):
    global str_lbl1_start
    global str_lbl1_stop
    def __init__(self, args):
        global str_lbl1_start
        global str_lbl1_stop
        TxtApplication.__init__(self, args)
        global_config = '/media/sdcard/data/config.conf'
        language = ''
        default_language = 'EN'
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
            str_lbl1_stop = 'stopped'
            str_lbl1_start = 'ready'
        elif language == 'DE':
            str_lbl1_stop = 'gestoppt'
            str_lbl1_start = 'bereit'
        w = TxtWindow('Telegram')
        configfile_path = '/media/sdcard/apps/6026c098-cb9b-45da-9c8c-9d05eb44a4fd/config'
        if os.path.exists(configfile_path) != True:
            print('API KEY MISSING')
            if language == 'EN':
                str_lbl1 = 'Configure Telegram API-Key described on the TXT website! '
            elif language == 'DE':
                str_lbl1 = 'Konfiguriere den  Telegram API-Key, wie auf der Webseite des TXT beschrieben! '
        else:
            try:
                configfile = configparser.RawConfigParser()
                configfile.read(configfile_path)
                api_key = configfile.get('config', 'key')
            except:
                print('API KEY MISSING')
                if language == 'EN':
                    str_lbl1 = 'Configure Telegram API-Key described on the TXT website!'
                elif language == 'DE':
                    str_lbl1 = 'Konfiguriere den  Telegram API-Key, wie auf der Webseite des TXT beschrieben!'
        self.vbox = QVBoxLayout()
        self.vbox.addStretch()
        if pid == '':
            self.lbl1 = StateWidget("Status", str_lbl1_stop)
        else:
            self.lbl1 = StateWidget("Status", str_lbl1_start)
        self.vbox.addWidget(self.lbl1)
        # self.lbl1.setObjectName("smalllabel")
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
        global str_lbl1_start
        global str_lbl1_stop
        print('start')
        pid_path = '/tmp/telegram.pid'
        pid = ''
        if os.path.exists(pid_path) == True:
            pid = os.popen('cat ' + pid_path).read()
        if pid == '':
            print('START')
            print(str_lbl1_start)
            os.system('sh /media/sdcard/apps/6026c098-cb9b-45da-9c8c-9d05eb44a4fd/telegram-start.sh')
            self.lbl1 = StateWidget("Status", "str_lbl1_start")
        else:
            print('ALREADY STARTED')

    def on_button_clicked_stop(self):
        global str_lbl1_start
        global str_lbl1_stop
        print('stop')
        pid_path = '/tmp/telegram.pid'
        pid = ''
        if os.path.exists(pid_path) == True:
            pid = os.popen('cat ' + pid_path).read()
        if pid != '':
            print('KILLED')
            os.system('kill ' + pid)
            os.system('rm /tmp/telegram.pid')
            self.lbl1 = StateWidget("Status", str_lbl1_stop)
        else:
            print('ALREDY KILLED')
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
