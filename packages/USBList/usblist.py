#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess

from TouchStyle import *

class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)
        
        # main window
        win = TouchWindow("USBList")
        
        widg = QWidget()
        
        box=QVBoxLayout()
        
        output=QTextEdit()
        output.setStyleSheet("QTextEdit { font-size: 16px; color: white; background-color: black; font-family: monospace; }")
        output.setReadOnly(True)
        output.setLineWrapMode(2)
        output.setLineWrapColumnOrWidth(1024)
        
        self.target=output
        
        self.usbscan()
        
        box.addWidget(output)
        
        box.addStretch()
        
        button =  QPushButton("Rescan")
        button.clicked.connect(self.usbscan)
        
        box.addWidget(button)
        
        widg.setLayout(box)
        
        win.setCentralWidget(widg)
        
        win.show()
        self.exec_()        

    def usbscan(self):
        textfield=[]
        p = subprocess.Popen('lsusb', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        for line in p.stdout.readlines():
            textfield.append(line.decode("utf-8"))
        retval = p.wait()
        
        text=""
        for line in textfield:
            text=text+line
            
        if retval==0:
            self.target.setText(text)
        else:
            self.target.setText("USB scan failed")
        
        return
        
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)

