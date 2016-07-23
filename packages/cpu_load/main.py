#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys
import os
import time
from TxtStyle import *



class FtcGuiApplication(TxtApplication):
	def __init__(self, args):
		TxtApplication.__init__(self, args)

		###################### Input
		#Get CPU-Load
		temp = os.popen("cat /proc/loadavg").read().split(" ")
		ram = os.popen("cat /proc/meminfo").read().split("\n")
		top = os.popen(" top -b -n1 | head -n 11 | tail -n 4").read()

		#Reform the Values and write them to Variables
		temp_1 = int(float(temp[0]) * 100)

		ram_total = ram[0].split(" ")
		ram_total = int(ram_total[len(ram_total)-2])

		ram_free = ram[1].split(" ")
		ram_free = int(ram_free[len(ram_free)-2])

		top_process = top.split("\n")
		top_process = top_process[2]
		top_process = " ".join(top_process.split()).split(" ")
		top_name = top_process[7]
		top_percent = top_process[5]

		###################### Output

		# create the empty main window
		w = TxtWindow("System Load")

		self.vbox = QVBoxLayout()

		#Create Label and ProgressBar for the one-minute-Graph
		self.msg_1 = QLabel("CPU-Load (1 min)")
		self.msg_1.setWordWrap(True)
		self.msg_1.setAlignment(Qt.AlignCenter)
		self.vbox.addWidget(self.msg_1)

		self.msg_1_B = QProgressBar()
		self.msg_1_B.setRange(0,100)
		self.msg_1_B.setValue(temp_1)
		self.vbox.addWidget(self.msg_1_B)

		self.msg_RAM_total = QLabel("Available RAM")
		self.msg_RAM_total.setWordWrap(True)
		self.msg_RAM_total.setAlignment(Qt.AlignCenter)
		self.vbox.addWidget(self.msg_RAM_total)

		self.msg_RAM_bar = QProgressBar()
		self.msg_RAM_bar.setRange(0,ram_total)
		self.msg_RAM_bar.setValue(ram_total - ram_free)
		self.vbox.addWidget(self.msg_RAM_bar)

		self.msg_TOP = QLabel("Loady Process")
		self.msg_TOP.setWordWrap(True)
		self.msg_TOP.setAlignment(Qt.AlignCenter)
		self.vbox.addWidget(self.msg_TOP)

		self.msg_TOP_C = QTextEdit(top_name[-12:] + "  " + top_percent)
		self.vbox.addWidget(self.msg_TOP_C)

		w.centralWidget.setLayout(self.vbox)

		w.show()

		self.timer = QTimer(self)
		self.timer.timeout.connect(self.refresh)
		self.timer.start(1000)
		self.exec_()

	def refresh(self):
		# Refresh all values every second
		#Get all values
		temp = os.popen("cat /proc/loadavg").read().split(" ")
		ram = os.popen("cat /proc/meminfo").read().split("\n")
		top = os.popen(" top -b -n1 | head -n 11 | tail -n 4").read()

		temp_1 = int(float(temp[0]) * 100)

		ram_total = ram[0].split(" ")
		ram_total = int(ram_total[len(ram_total)-2])

		ram_free = ram[1].split(" ")
		ram_free = int(ram_free[len(ram_free)-2])

		top_process = top.split("\n")
		top_process = top_process[0]
		top_process = " ".join(top_process.split()).split(" ")
		top_name = top_process[7]
		top_percent = top_process[5]

		self.msg_1_B.setValue(temp_1);
		self.msg_RAM_bar.setValue(ram_total - ram_free)
		self.msg_TOP_C.setText(top_name[-12:] + "  " + top_percent)

if __name__ == "__main__":
	FtcGuiApplication(sys.argv)
