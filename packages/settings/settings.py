#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys, configparser, os
from TxtStyle import *
global configpath
configpath = '/media/sdcard/data/config.conf'
class FtcGuiApplication(TxtApplication):
	def __init__(self, args):
		TxtApplication.__init__(self, args)

		w = TxtWindow("Settings")
		self.vbox = QVBoxLayout()
		self.vbox.addStretch()
		self.lbl = QLabel("Select your language:")
		self.lbl.setObjectName("smalllabel")
		self.lbl.setWordWrap(True)
		self.lbl.setAlignment(Qt.AlignCenter)
		self.vbox.addWidget(self.lbl)
		btn_lang_EN = QPushButton('Language: EN')
		btn_lang_EN.clicked.connect(self.on_button_clicked_EN)
		self.vbox.addWidget(btn_lang_EN)
		btn_lang_DE = QPushButton('Sprache: DE')
		btn_lang_DE.clicked.connect(self.on_button_clicked_DE)
		self.vbox.addWidget(btn_lang_DE)
		w.centralWidget.setLayout(self.vbox)
		w.show()
		self.exec_()
	def set_lang(self,lang):
		Config = configparser.ConfigParser()
		cfgfile = open(configpath,'w')
		Config.add_section('general')
		Config.set('general','language',lang)
		Config.write(cfgfile)
		cfgfile.close()
	def on_button_clicked_DE(self):
		self.set_lang('DE')
	def on_button_clicked_EN(self):
		self.set_lang('EN')

if __name__ == "__main__":
	FtcGuiApplication(sys.argv)
