#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys, os
from TouchStyle import *

import smbus
#import struct, array, math

bus = smbus.SMBus(1) #1 indicates /dev/i2c-1


        
class TouchGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)

        translator = QTranslator()
        path = os.path.dirname(os.path.realpath(__file__))
        translator.load(QLocale.system(), os.path.join(path, "I2C_"))
        self.installTranslator(translator)

        
        Adresse = 1
        I2C=[]
   
        for Adresse in range(128):

            try:
                bus.read_byte(Adresse)
                I2C.append(Adresse) #list concatenation
            except: # exception if read_byte fails
                pass
            
       
        i2c = [hex(n) for n in I2C]
        #print(i2c)
        i2c = str(i2c)
            

        
        # create the empty main window
        self.win = TouchWindow("I2C Scanner")

        self.vbox = QVBoxLayout()
        self.vbox.addStretch()
        
 
        L1 = QLabel("I2C bus scanner.           Following I2C addresses found:"+"                "+ i2c)
        L1.setObjectName("smalllabel")
        L1.setWordWrap(True)
        L1.setAlignment(Qt.AlignCenter)
        
        #L2 = QListWidget()
        #L2.addItem(i2c)
        #L2.setWordWrap(True)
        
        
        self.vbox.addWidget(L1)
        #self.vbox.addWidget(L2)
        self.vbox.addStretch()
      
        self.win.centralWidget.setLayout(self.vbox)
        self.win.show()    
      
        
        self.exec_()        


if __name__ == "__main__":
    TouchGuiApplication(sys.argv)
