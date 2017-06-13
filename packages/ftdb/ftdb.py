#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import sys
from ftDBpy import ftDB
from TouchStyle import *
from style import *
from windows import *
from keyboard import *
from threading import Thread
import time
import os.path

global default_url
default_url = 'https://ftdb.baubadil.de/'
temp_folder = '/tmp/ftdb/'
image_temp = 'images/'
image_size = 150
ticket_info_order = ['title', 'image', 'description', 'article_nos']


class FtcGuiApplication(TouchApplication):

    def __init__(self, args):
        url_base = default_url
        for arg in args:
            if '--url=' in arg:
                url_base = arg.split('--url=')[1]
        global db
        db = ftDB(url_base)
        print('Base URL:', db.base_url)
        if not os.path.isdir(temp_folder):
            os.mkdir(temp_folder)
        if not os.path.isdir(temp_folder + image_temp):
            os.mkdir(temp_folder + image_temp)
        TouchApplication.__init__(self, args)
        if not TouchInputContext.keyboard_present():
            # disabled while not finished
            self.setInputContext(TouchInputContext(self))
            pass
        self.w = TouchWindow('ft:Datenbank')
        self.vbox = QVBoxLayout()
        self.vbox.addStretch()
        self.search_label = QLabel('Search:')
        self.vbox.addWidget(self.search_label)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText('Search')
        self.vbox.addWidget(self.edit)
        self.vbox.addStretch()
        self.search_but = ShadowButton('search')
        self.search_but.setText('Search')
        self.search_but.clicked.connect(self.search)
        self.vbox.addWidget(self.search_but)
        self.vbox.addStretch()
        self.w.centralWidget.setLayout(self.vbox)
        self.w.show()
        self.exec_()

    def search(self):
        search_str = self.edit.text()
        print('Searching:' + search_str)
        dialog = SearchResultDialog(self.w, search_str)
        dialog.exec_()
        # self.sender().setDisabled(False)

if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
