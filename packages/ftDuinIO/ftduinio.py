#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys, time, serial
import ftduino_direct as ftd
from PyQt4 import QtCore
from TouchStyle import *
from TouchAuxiliary import *
from PyQt4.QtCore import QTimer
import queue, pty, subprocess, select, os
import urllib.request, urllib.parse, urllib.error

MAX_TEXT_LINES=50

STORE= "https://raw.githubusercontent.com/harbaum/ftduino/master/bin/"
STD_STYLE="QPlainTextEdit { font-size: 12px; color: white; background-color: black; font-family: monospace; }"
EXT_STYLE="QPlainTextEdit { font-size: 8px; color: #c9ff74; background-color: #184d00; font-family: monospace; }"

FTDUINO_VIRGIN_VIDPID="1c40:0537"
FTDUINO_VIDPID="1c40:0538"

TST=False

try:
    with open(os.path.dirname(os.path.realpath(__file__)) + "/manifest","r", encoding="utf-8") as f:
        r=f.readline()
        while not "version" in r:
          r=f.readline()
        
        if "version" in r:
          VSTRING = "v" + r[ r.index(":")+2 : ]
        else: VSTRING=""
        f.close()
except:
    VSTRING="n/a" 
    

class TextWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        self.setMaximumBlockCount(MAX_TEXT_LINES)
        self.setReadOnly(True)
        style = STD_STYLE
        self.setStyleSheet(style)
    
        # a timer to read the ui output queue and to update
        # the screen
        self.ui_queue = queue.Queue()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(10)

    def append_str(self, text, color=None):
        self.moveCursor(QTextCursor.End)
        if not hasattr(self, 'tf') or not self.tf:
            self.tf = self.currentCharFormat()
            self.tf.setFontWeight(QFont.Bold);
        if color:
            tf = self.currentCharFormat()
            tf.setForeground(QBrush(QColor(color)))
            self.textCursor().insertText(text, tf);
        else:
            self.textCursor().insertText(text, self.tf);
            
    def delete(self):
        self.textCursor().deletePreviousChar()
        
    def append(self, text, color=None):
        pstr = ""
        for c in text:
            # special char!
            if c in "\b\a":
                if pstr != "":
                    self.append_str(pstr, color)
                    pstr = ""
        
                if c == '\b':
                    self.delete()
            else:
                pstr = pstr + c

        if pstr != "":
            self.append_str(pstr, color)

        # put something into output queue
    def write(self, str):
        self.ui_queue.put( str )
    
    def clear(self):
        self.setPlainText("")
    
        # regular timer to check for messages in the queue
        # and to output them locally
    def on_timer(self):
        while not self.ui_queue.empty():
            # get from queue
            e = self.ui_queue.get()

            # strings are just sent
            if type(e) is str:
                self.append(e)

class FtcGuiApplication(TouchApplication):
    sigExecFinished=pyqtSignal(int)
    
    def __init__(self, args):
        TouchApplication.__init__(self, args)
        
        self.sigExecFinished.connect(self.execFinished)
        
        self.duinos=[]
        self.act_duino=None
        self.flashType=0
        
        self.window = TouchWindow("ftDuinIO")       
        self.window.titlebar.close.clicked.connect(self.end)

        
        self.setMainWidget()
        
        self.menu=self.window.addMenu()
        self.menu.setStyleSheet("font-size: 24px;")
                
        self.m_cache = self.menu.addAction(QCoreApplication.translate("mmain","Cache"))
        self.m_cache.triggered.connect(self.on_menu_cache) 
        
        #self.menu.addSeparator()
        
        self.m_bootloader = self.menu.addAction(QCoreApplication.translate("mmain","Flash Bootloader"))
        self.m_bootloader.triggered.connect(self.on_menu_bootloader)
        
        self.m_about = self.menu.addAction(QCoreApplication.translate("mmain","About"))
        self.m_about.triggered.connect(self.on_menu_about)
        
        self.window.setCentralWidget(self.mainWidget)
        
        self.window.show()
        
        self.ftdscan()
        
        self.checker=QTimer()
        self.checker.timeout.connect(self.checkFtdComm)
        self.checker.start(250)
        
        self.app_process = None
        self.flashfile = None
        
        self.exec_()        
        
    def end(self):
        self.out=False
        self.on_close()
        if self.act_duino!=None:
            try:
                self.act_duino.close()
            except:
                pass
            
    def on_menu_bootloader(self):
        self.dFlash_clicked()
        self.fSelect.hide()
        self.menu.setDisabled(True)
        
        path = os.path.dirname(os.path.realpath(__file__))

        files = [f for f in os.listdir(os.path.join(path,"bootloader")) if os.path.isfile(os.path.join(path, "bootloader", f))]
        self.flashType=2
        self.fFlash.setStyleSheet("font-size: 20px; color: white; background-color: qlineargradient( x1:0 y1:0, x2:0 y2:1, stop:0 yellow, stop:1 red);")
            
        if len(files)>1:
            (s,r)=TouchAuxListRequester(QCoreApplication.translate("fSelect","Binary"),QCoreApplication.translate("fSelect","Select binary to be flashed:"),files,files[0],"Okay").exec_()

            if s: # flash file selected
                self.flashFile=r
                self.fBinary.setText(self.flashFile)
                self.fFlash.setDisabled(False)
        elif len(files)==1:
                self.flashFile=files[0]
                self.fBinary.setText(self.flashFile)
                self.fFlash.setDisabled(False)        
    
    def on_menu_about(self):
        t=TouchMessageBox(QCoreApplication.translate("about","About"), self.window)
        t.setCancelButton()
        t.addPixmap(QPixmap("icon.png"))
        text=QCoreApplication.translate("about","<font size='2'>ftDuinIO<br><font size='1'>Version ")
        text=text+VSTRING
        text=text+QCoreApplication.translate("about","<center>(c) 2018 Peter Habermehl<br>for the ft community")
        t.setText(text)
        t.setPosButton(QCoreApplication.translate("about","Okay"))
        t.exec_()   
        
    def on_menu_cache(self):
        path = os.path.dirname(os.path.realpath(__file__))
        files = [f[:-8] for f in os.listdir(os.path.join(path,"binaries")) if os.path.isfile(os.path.join(path, "binaries", f))]
        s=False
        if len(files)>0:
            (s,r)=TouchAuxListRequester(QCoreApplication.translate("cache","Cache"),QCoreApplication.translate("cache","Select binary"),files,files[0],"Okay").exec_()
            if s:
                t=TouchMessageBox(QCoreApplication.translate("cache","Download"), self.window)
                t.setText( QCoreApplication.translate("cache","File:") + "<br>"+ r + "<br><br>" +
                           QCoreApplication.translate("cache","stored in cache."))
                t.setPosButton(QCoreApplication.translate("cache","Delete!"))
                t.setNegButton(QCoreApplication.translate("cache","Okay"))
                (c,v)=t.exec_() 
                if v==QCoreApplication.translate("cache","Delete!"):
                    os.remove(os.path.join(path,"binaries",r+".ino.hex"))
                
    def checkFtdComm(self):
        if self.act_duino!=None:
            n=self.act_duino.comm("ftduino_id_get")
            if n=="Fail":
                self.act_duino=None
                self.ftdcomm()    
        
    def ftdscan(self):
        duinos=ftd.ftduino_scan()
        self.duinos=[]
        self.device=[]
        for d in duinos:
            if d[1]!="":
                self.duinos.append(d[1])
                self.device.append(d[0])
            else:
                self.duinos.append(d[0])
                self.device.append(d[0])
        self.dList.clear()

        if len(self.duinos)>0:
            self.ftdcomm()
            self.dList.addItems(self.duinos)
        else:
            self.dFlash.setDisabled(True)
            self.dRename.setDisabled(True)
            self.dIO.setDisabled(True)
            self.dList.addItem(QCoreApplication.translate("comm","none found"))
            self.dComm.setStyleSheet("font-size: 20px;")
            self.dComm.setText(QCoreApplication.translate("comm","none"))
            self.act_duino=None
            
        self.dComm.repaint()
        self.processEvents()
                
    def ftdcomm(self):
        if self.act_duino!=None:
            try:
                self.act_duino.close()
            except:
                pass
        
        if len(self.device)>0:
            duino=self.device[self.dList.currentIndex()]    
            self.act_duino=ftd.ftduino(duino)
        
        time.sleep(0.25)
        
        if self.act_duino!=None: n=self.act_duino.comm("ftduino_id_get")
        else: n="Fail"
        
        if n!="Fail" and n!="":
            self.dComm.setStyleSheet("font-size: 20px; background-color: darkgreen;")
            self.dComm.setText(QCoreApplication.translate("comm","SW: v")+self.act_duino.comm("ftduino_direct_get_version"))
            self.dRename.setDisabled(False)
            self.dFlash.setDisabled(False)
            self.dIO.setDisabled(False)
            
        elif len(self.device)>0:
            self.dComm.setStyleSheet("font-size: 20px; background-color: darkred;")
            self.dComm.setText(QCoreApplication.translate("comm","failed"))
            self.dRename.setDisabled(True)
            self.dFlash.setDisabled(False)
            self.dIO.setDisabled(True)
            self.act_duino=None
        else:
            self.dComm.setStyleSheet("font-size: 20px;")
            self.dComm.setText(QCoreApplication.translate("comm","none"))
            self.dRename.setDisabled(True)
            self.dFlash.setDisabled(True)
            self.dIO.setDisabled(True)
            self.act_duino=None            
            
    def rename_clicked(self):
        n=self.act_duino.comm("ftduino_id_get")
        if n!="" and n!="Fail":
            (res,st)=TouchAuxRequestText(QCoreApplication.translate("rename","Rename"),
                    QCoreApplication.translate("rename","Enter new ftDuino ID for device '") + n +"':",
                    n,
                    QCoreApplication.translate("rename","Okay"), self.window
                    ).exec_()
            if ((st!="") and res):
                res=self.act_duino.comm("ftduino_id_set "+st)
        self.rescan_clicked()
        
    def rescan_clicked(self):
        if TST:
            self.dFlash_clicked()
        else:
            self.dComm.setStyleSheet("font-size: 20px; background-color: darkorange;")
            self.dComm.setText(QCoreApplication.translate("comm","scanning"))
            self.dComm.repaint()
            self.processEvents()
            self.ftdscan()
    
    def fSelect_clicked(self):
        self.flashFile=""
        ftb=TouchAuxMultibutton(QCoreApplication.translate("fSelect","Flash"), self.window)
        ftb.setText(QCoreApplication.translate("fSelect","Please select the source of the binary to flash:"))
        ftb.setButtons([ QCoreApplication.translate("fSelect","Local Cache"),
                        QCoreApplication.translate("fSelect","Download"),
                        #QCoreApplication.translate("fSelect","Bootloader")
                        ] )
        ftb.setTextSize(3)
        ftb.setBtnTextSize(3)
        (t,p)=ftb.exec_()
        
        if not t: return
        
        path = os.path.dirname(os.path.realpath(__file__))
        
        if p == QCoreApplication.translate("fSelect","Local Cache"):
            files = [f[:-8] for f in os.listdir(os.path.join(path,"binaries")) if os.path.isfile(os.path.join(path, "binaries", f))]
            self.flashType=1
            self.fFlash.setStyleSheet("font-size: 20px; color: white; background-color: darkred;")
        if p == QCoreApplication.translate("fSelect","Download"):
            self.flashType=1
            files = self.dlBinary()
        if p == QCoreApplication.translate("fSelect","Bootloader"):
            files = [f for f in os.listdir(os.path.join(path,"bootloader")) if os.path.isfile(os.path.join(path, "bootloader", f))]
            self.flashType=2
            self.fFlash.setStyleSheet("font-size: 20px; color: white; background-color: qlineargradient( x1:0 y1:0, x2:0 y2:1, stop:0 yellow, stop:1 red);")
            
        s=False
        if len(files)>1:
            (s,r)=TouchAuxListRequester(QCoreApplication.translate("fSelect","Binary"),QCoreApplication.translate("fSelect","Select binary to be flashed:"),files,files[0],"Okay").exec_()
        elif len(files)==1:
            s=True
            r=files[0]
            
        if s: # flash file selected
            self.flashFile=r
            self.fBinary.setText(self.flashFile)
            self.fFlash.setDisabled(False)
        else:
            self.flashType=0
            
            
    def dlBinary(self):
        self.window.hide()
        food=[]
        select=[]
        try:
            file=urllib.request.urlopen(STORE+"00index.txt", timeout=1)
            food=file.read().decode('utf-8').split("\n")
            file.close()
        except:
            self.window.show()
            t=TouchMessageBox(QCoreApplication.translate("flash","Store"), self.window)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("flash","Store not accessible."))
            t.setPosButton(QCoreApplication.translate("flash","Okay"))
            t.exec_()
            
        if food !=[]:
            menu=[]
            for line in food:
                if line[0:6]=="name: ": menu.append(line[6:])

            (s,r)=TouchAuxListRequester(QCoreApplication.translate("flash","Store"),QCoreApplication.translate("ecl","Select binary:"),menu,menu[0],"Okay",self.window).exec_()
            
            if s:
                a=False
                b=False
                for line in food:
                    if b:
                        version=line[9:]
                        break
                    if a and not b:
                        filename=line[6:]
                        b=True
                    if line[6:]==r: a=True
                
                v=""
                if b:
                    t=TouchMessageBox(QCoreApplication.translate("flash","Download"), self.window)
                    t.setText( QCoreApplication.translate("flash","File:") + "<br>"+ filename + "<br><br>" +
                               QCoreApplication.translate("flash","Version: v") + version)
                    t.setPosButton(QCoreApplication.translate("flash","Okay"))
                    t.setNegButton(QCoreApplication.translate("flash","Cancel"))
                    (c,v)=t.exec_()
                    
                    
                
                if v==QCoreApplication.translate("flash","Okay"):
                    try:
                        file=urllib.request.urlopen(STORE+filename, timeout=1)
                        food=file.read()
                        file.close()
                        target = os.path.dirname(os.path.realpath(__file__))
                        target = os.path.join(target, "binaries", filename)
                        v=QCoreApplication.translate("flash","Replace")
                        if os.path.exists(target):
                            t=TouchMessageBox(QCoreApplication.translate("flash","Download"), self.window)
                            t.setText( QCoreApplication.translate("flash","File:") + "<br>"+ filename + "<br><br>" +
                                QCoreApplication.translate("flash","already exists in cache!"))
                            t.setPosButton(QCoreApplication.translate("flash","Replace"))
                            t.setNegButton(QCoreApplication.translate("flash","Cancel"))
                            (c,v)=t.exec_() 
                            
                        if v==QCoreApplication.translate("flash","Replace"):
                            with open(target, 'wb') as f:
                                f.write(food)
                            f.close()
                            filename=filename[:-8]
                        else:
                            filename=""
                    except: # download failed
                        filename=""
                        t=TouchMessageBox(QCoreApplication.translate("flash","Store"), self.window)
                        t.setCancelButton()
                        t.setText(QCoreApplication.translate("flash","Download failed."))
                        t.setPosButton(QCoreApplication.translate("flash","Okay"))
                        t.exec_()

        self.window.show()
        return [filename]
        
    def fFlash_clicked(self):
        flasherror=False
        
        self.fLabel.hide()
        self.fSelect.hide()
        self.fBinary.hide()
        self.fFlash.hide()
        self.menu.setDisabled(True)
        self.fBack.setDisabled(True)
        self.fBack.setText(QCoreApplication.translate("flash","please wait"))
        self.fCon.clear()
        self.processEvents()
        self.fWidget.repaint()
        
        path = os.path.dirname(os.path.realpath(__file__))  
        
        if self.flashType==1: # binary flash
            duino=self.device[self.dList.currentIndex()]
            # activate bootloader
            if self.act_duino!="None":
                try:
                    self.act_duino.close()
                except:
                    pass
            self.act_duino=None
            
            self.fCon.write("C:> ")
            self.fWidget.repaint()
            for i in "del c:*.*":
                self.fCon.write(i)
                self.processEvents()
                self.fWidget.repaint()
                self.processEvents()
                time.sleep(0.25)
            time.sleep(2)
            self.fCon.write("\nC:> ")
            for i in "avrdude "+self.flashFile+".s19":
                self.fCon.write(i)
                self.processEvents()
                self.fWidget.repaint()
                self.processEvents()
                time.sleep(0.25)    
            self.fCon.write('\nUnknown command "avrdude.com"')
            self.processEvents()
            self.fWidget.repaint()
            self.processEvents()
            time.sleep(2) 
            self.fCon.write("\nC:> ")
            for i in "dir ":
                self.fCon.write(i)
                self.processEvents()
                self.fWidget.repaint()
                self.processEvents()
                time.sleep(0.25)                   
            self.fCon.write('\nUnknown command "dir.com"')
            self.processEvents()
            self.fWidget.repaint()
            self.processEvents()
            time.sleep(2)        
            
            try:
                ser = serial.Serial()
                ser.port = duino
                ser.baudrate = 1200
                ser.open()
                ser.setDTR(0)
                ser.close()
                time.sleep(2)
            except:
                pass
            
            devices = []
            for dev in serial.tools.list_ports.grep("vid:pid="+FTDUINO_VIDPID):
                devices.append(dev[0])
            for dev in serial.tools.list_ports.grep("vid:pid="+FTDUINO_VIRGIN_VIDPID):
                devices.append(dev[0])
                
            if len(devices)>1:
                t=TouchMessageBox(QCoreApplication.translate("flash","Error"), self.window)
                t.setText(QCoreApplication.translate("flash","More than one ftDuino connected! Please disconnect all but the device to be flashed."))
                t.setPosButton(QCoreApplication.translate("flash","Okay"))
                t.exec_() 
                return
            elif len(devices)<1:
                t=TouchMessageBox(QCoreApplication.translate("flash","Error"), self.window)
                t.setText(QCoreApplication.translate("flash","No ftDuino connected! Please connect the device to be flashed."))
                t.setPosButton(QCoreApplication.translate("flash","Okay"))
                t.exec_() 
                return
            else:            
                # prepare avrdude call
                cmd = [ "avrdude",
                    "-v",
                    "-patmega32u4",
                    "-cavr109",
                    "-P"+devices[0],
                    "-b57600",
                    "-D",
                    "-Uflash:w:"+os.path.join(path, "binaries", self.flashFile)+".ino.hex:i"]

                flasherror=self.exec_command(cmd)
        
        elif self.flashType==2: # bootloader flash
            self.fCon.write("C:> ")
            self.fWidget.repaint()
            for i in "CP/M":
                self.fCon.write(i)
                self.processEvents()
                self.fWidget.repaint()
                time.sleep(0.25)
                
            self.fCon.write("\nCP/M loading\n")
            self.processEvents()
            for i in "##########":
                self.fCon.write(i)
                self.processEvents()
                self.fWidget.repaint()
                time.sleep(0.2)
            
            time.sleep(1)
            self.fCon.setStyleSheet(EXT_STYLE)
            self.fCon.clear()
            self.processEvents()
            self.fWidget.repaint()
            time.sleep(0.5)
            self.fCon.write("CP/M 2.2 - Amstrad Consumer Electronics plc\n\n")
            self.fWidget.repaint()
            self.processEvents()            
            time.sleep(1)
            self.fCon.write("A>dir\n")
            self.fWidget.repaint()
            self.processEvents()            
            time.sleep(0.4)        
            self.fCon.write("A: AVRDUDE  COM : "+self.flashFile[:8]+" BIN\nA: STAT     COM : FILECOPY COM\n")
            self.fWidget.repaint()
            self.processEvents()
            time.sleep(0.25)
            self.fCon.write("A: DISC     BAS : SETUP    COM\nA: BOOTGEN  COM : LOAD     COM\n")
            self.fWidget.repaint()
            self.processEvents()
            time.sleep(0.25)
            self.fCon.write("A>avrdude "+self.flashFile[:8]+".bin\n")
            self.processEvents()
            self.fWidget.repaint()
            self.processEvents()
            time.sleep(2)

            cmd=["avrdude",
                 "-v",
                 "-patmega32u4",
                 "-cusbasp",
                 "-Pusb", 
                 "-Uflash:w:"+os.path.join(path, "bootloader", self.flashFile)+":i",
                 "-Ulock:w:0x2F:m" ]
            
            flasherror=self.exec_command(cmd)
        self.fWidget.repaint()
        self.fBack.setDisabled(False)
        self.fBack.setText(QCoreApplication.translate("flash","Back"))
        self.processEvents()            
        
    def xBack_clicked(self):
        self.out=False
        self.menu.setDisabled(False)
        self.dWidget.show()
        self.fWidget.hide()
        self.ioWidget.hide()
        self.processEvents()
        self.ftdcomm()
    
    def io_changed(self):
        self.doIO()
    
    def dIO_clicked(self):
        self.dWidget.hide()
        self.fWidget.hide()
        self.ioWidget.show()
        self.out=True
        self.doIO()
    
    def doIO(self):        
        outType=self.ioFun.currentIndex()
        dist=self.iDCType.currentIndex()
        

        if outType==0:
            self.iDCType.hide()
            self.iTextField.show()
            self.oOut.hide()
            self.oMot.hide()
            for n in range(1,9):
                i=self.act_duino.comm("input_set_mode I"+str(n)+" Switch")
        elif outType==1:
            self.iDCType.hide()
            self.iTextField.show()
            self.oOut.hide()
            self.oMot.hide()
            for n in range(1,9):
                i=self.act_duino.comm("input_set_mode I"+str(n)+" Voltage")
        elif outType==2:
            self.iDCType.hide()
            self.iTextField.show()
            self.oOut.hide()
            self.oMot.hide()
            for n in range(1,9):
                i=self.act_duino.comm("input_set_mode I"+str(n)+" Resistance")
        elif outType==3:
            self.iDCType.show()
            self.iTextField.show()
            self.oOut.hide()
            self.oMot.hide()
            for n in range(1,5):
                i=self.act_duino.comm("counter_set_mode C"+str(n)+" Any")
                i=self.act_duino.comm("counter_clear C"+str(n))
            if dist==0: #counters Only
                i=self.act_duino.comm("ultrasonic_enable false")
            else: # dist + counters
                i=self.act_duino.comm("ultrasonic_enable true")
        elif outType==4:
            self.iDCType.hide()
            self.iTextField.hide()
            self.oOut.show()
            self.oMot.hide()
        elif outType==5:
            self.iDCType.hide()
            self.iTextField.hide()
            self.oOut.hide()
            self.oMot.show()
        
        while self.out:
            self.processEvents()
            time.sleep(0.05)
            s=""
            if outType<3:
                for n in range(1,9):
                    s=s+"I"+str(n)+": "
                    i=self.act_duino.comm("input_get I"+str(n))
                    if outType==0:
                        if i=="1":      s=s+"True"
                        elif i=="0":    s=s+"False"
                        else:           s=s+"Fail"
                        s=s+"\n"
                    elif outType==1:
                        a="     "+i
                        s=s+a[-5:]+" mV\n"
                    elif outType==2:
                        a="     "+i
                        s=s+a[-5:]+" Ohm\n"              
                self.iTextField.setText(s)
            elif outType==3:
                if dist==0:
                    a="     "+self.act_duino.comm("counter_get C1")
                    s="C1: "+a[-5:]+"\n"
                else:
                    a=self.act_duino.comm("ultrasonic_get")
                    if a!="-1":
                        a="     "+a
                        s="D1: "+a[-5:]+" cm\n"
                    else: s="D1:  Fail\n"
                for n in range(2,5):
                    s=s+"C"+str(n)+": "
                    a="     "+self.act_duino.comm("counter_get C"+str(n))
                    s=s+a[-5:]+"\n"
                self.iTextField.setText(s)
                
            
    def dFlash_clicked(self):
        self.dWidget.hide()
        self.ioWidget.hide()
        self.fCon.clear()
        self.fCon.setStyleSheet(STD_STYLE)
        self.fFlash.setStyleSheet("font-size: 20px; color: white; background-color: darkred;")
        if self.flashType==2:
            self.flashType=0
            self.fBinary.setText("-- none --")
        self.fCon.write("C:>")
        self.fLabel.show()
        self.fSelect.show()
        self.fBinary.show()
        self.fFlash.show()
        self.fWidget.show()

    def setDWidget(self):        
        # Widget für Devices:
        
        self.dWidget=QWidget()
        
        devices=QVBoxLayout()
        
        hbox=QHBoxLayout()
        
        text=QLabel(QCoreApplication.translate("devices","Device:"))
        text.setStyleSheet("font-size: 20px;")
        hbox.addWidget(text)
        
        hbox.addStretch()
        
        self.dRescan=QPushButton(QCoreApplication.translate("devices","Rescan"))
        self.dRescan.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.dRescan)
        
        devices.addLayout(hbox)
        
        self.dList=QComboBox()
        self.dList.setStyleSheet("font-size: 20px;")
        self.dList.addItem(" --- none ---")
        devices.addWidget(self.dList)
        
        hbox=QHBoxLayout()
        
        text=QLabel(QCoreApplication.translate("devices","Connect:"))
        text.setStyleSheet("font-size: 20px;")
        hbox.addWidget(text)

        self.dComm=QLineEdit()
        self.dComm.setReadOnly(True)
        self.dComm.setStyleSheet("font-size: 20px; color: white;")
        self.dComm.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.dComm.setText(QCoreApplication.translate("flash","no device"))
        hbox.addWidget(self.dComm)
        
        devices.addLayout(hbox)
        
        devices.addStretch()
        
        self.dIO=QPushButton(QCoreApplication.translate("devices","I/O test"))
        self.dIO.setStyleSheet("font-size: 20px;")
        
        devices.addWidget(self.dIO)
        
        self.dRename=QPushButton(QCoreApplication.translate("devices","Rename"))
        self.dRename.setStyleSheet("font-size: 20px;")
        
        devices.addWidget(self.dRename)
        
        self.dFlash=QPushButton(QCoreApplication.translate("devices","Flash binary"))
        self.dFlash.setStyleSheet("font-size: 20px;")
        devices.addWidget(self.dFlash)
        
        self.dWidget.setLayout(devices)
        
        self.dRescan.clicked.connect(self.rescan_clicked)
        self.dRename.clicked.connect(self.rename_clicked)
        self.dIO.clicked.connect(self.dIO_clicked)
        self.dFlash.clicked.connect(self.dFlash_clicked)

    def setFWidget(self):       
        # widget für Flashtool:
        
        self.fWidget=QWidget()
        
        flash=QVBoxLayout()
        
        hbox=QHBoxLayout()
        
        self.fLabel=QLabel(QCoreApplication.translate("flash","Binary:"))
        self.fLabel.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.fLabel)
        
        self.fSelect=QPushButton(QCoreApplication.translate("flash","Select"))
        self.fSelect.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.fSelect)
        
        flash.addLayout(hbox)
        
        self.fBinary=QLineEdit()
        self.fBinary.setReadOnly(True)
        self.fBinary.setStyleSheet("font-size: 20px; color: white;")
        self.fBinary.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.fBinary.setText(QCoreApplication.translate("flash","-- none --"))
        flash.addWidget(self.fBinary)
        
        self.fFlash=QPushButton(QCoreApplication.translate("flash","--> Flash <--"))
        self.fFlash.setStyleSheet("font-size: 20px; color: white; background-color: darkred;")
        flash.addWidget(self.fFlash)
        self.fFlash.setDisabled(True)
                
        self.fCon=TextWidget(self.window)
        flash.addWidget(self.fCon)
        
        self.fBack=QPushButton(QCoreApplication.translate("flash","Back"))
        self.fBack.setStyleSheet("font-size: 20px; color: white;")
        flash.addWidget(self.fBack)
        
        self.fWidget.setLayout(flash)
        
        self.fSelect.clicked.connect(self.fSelect_clicked)
        self.fFlash.clicked.connect(self.fFlash_clicked)
        self.fBack.clicked.connect(self.xBack_clicked)        
    
    def setIOWidget(self):
        # widget für I/O Test
        self.ioWidget=QWidget()
        
        io=QVBoxLayout()
        
        self.ioFun=QComboBox()
        self.ioFun.setStyleSheet("font-size: 20px;")
        self.ioFun.addItems(  [ QCoreApplication.translate("io","Inp. Switch"),
                                QCoreApplication.translate("io","Inp. Voltage"),
                                QCoreApplication.translate("io","Inp. Resistance"),
                                QCoreApplication.translate("io","Inp. Dist.&Count."),
                                QCoreApplication.translate("io","Outputs"),
                                QCoreApplication.translate("io","Motors")
                               ] )
        io.addWidget(self.ioFun)
        
        # Verschiedene I/O Widgets:
        
        # Dist. und counter input
        self.iDCType=QComboBox()
        self.iDCType.setStyleSheet("font-size: 20px;")
        self.iDCType.addItems(  [   QCoreApplication.translate("io","Counters"),
                                    QCoreApplication.translate("io","Distance")
                                ] )
        io.addWidget(self.iDCType)  
        
        self.iDCType.hide()
        
        # Dig. & analog Input
        self.iTextField=QTextEdit()
        self.iTextField.setReadOnly(True)
        self.iTextField.setWordWrapMode(QTextOption.WrapAnywhere)
        self.iTextField.setStyleSheet("font-size: 15px; color: white; background-color: black; font-family: monospace;")
        self.iTextField.setText("I1: ____0\nI2: ____0\nI3: ____0\nI4: ____0\nI5: ____0\nI6: ____0\nI7: ____0\nI8: ____0")
        io.addWidget(self.iTextField)
        
        #self.iTextField.hide()
        
        # outputs:
        self.oOut=QWidget()
        oOut=QVBoxLayout()
        
        hbox=QHBoxLayout()
        
        self.oPower=QSlider()
        self.oPower.setMinimum(0)
        self.oPower.setMaximum(512)
        self.oPower.setOrientation(1)
        self.oPower.setValue(512)
        
        hbox.addWidget(self.oPower)
        
        self.oPVal=QLabel()
        self.oPVal.setStyleSheet("font-size: 20px; color: white;")
        self.oPVal.setText("512")
        hbox.addWidget(self.oPVal)
        oOut.addLayout(hbox)
        
        hbox=QHBoxLayout()
        self.oB1=QPushButton("O1")
        self.oB1.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.oB1)
        self.oB2=QPushButton("O2")
        self.oB2.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.oB2)        
        oOut.addLayout(hbox)

        hbox=QHBoxLayout()
        self.oB3=QPushButton("O3")
        self.oB3.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.oB3)
        self.oB4=QPushButton("O4")
        self.oB4.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.oB4)        
        oOut.addLayout(hbox)
        
        hbox=QHBoxLayout()
        self.oB5=QPushButton("O5")
        self.oB5.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.oB5)
        self.oB6=QPushButton("O6")
        self.oB6.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.oB6)        
        oOut.addLayout(hbox)
        
        hbox=QHBoxLayout()
        self.oB7=QPushButton("O7")
        self.oB7.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.oB7)
        self.oB8=QPushButton("O8")
        self.oB8.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.oB8)        
        oOut.addLayout(hbox)
        
        self.oOut.setLayout(oOut)
        
        io.addWidget(self.oOut)
        
        self.oOut.hide()
        
        self.oB1.pressed.connect(self.oB1_pressed)
        self.oB1.released.connect(self.oB1_released)
        self.oB2.pressed.connect(self.oB2_pressed)
        self.oB2.released.connect(self.oB2_released)
        self.oB3.pressed.connect(self.oB3_pressed)
        self.oB3.released.connect(self.oB3_released)
        self.oB4.pressed.connect(self.oB4_pressed)
        self.oB4.released.connect(self.oB4_released)
        self.oB5.pressed.connect(self.oB5_pressed)
        self.oB5.released.connect(self.oB5_released)
        self.oB6.pressed.connect(self.oB6_pressed)
        self.oB6.released.connect(self.oB6_released)
        self.oB7.pressed.connect(self.oB7_pressed)
        self.oB7.released.connect(self.oB7_released)
        self.oB8.pressed.connect(self.oB8_pressed)
        self.oB8.released.connect(self.oB8_released)
        
        self.oPower.valueChanged.connect(self.oPower_changed)
        
        # motor outputs:
        self.oMot=QWidget()
        oMot=QVBoxLayout()
        
        hbox=QHBoxLayout()
        
        self.mPower=QSlider()
        self.mPower.setMinimum(0)
        self.mPower.setMaximum(512)
        self.mPower.setOrientation(1)
        self.mPower.setValue(512)
        
        hbox.addWidget(self.mPower)
        
        self.mPVal=QLabel()
        self.mPVal.setStyleSheet("font-size: 20px; color: white;")
        self.mPVal.setText("512")
        hbox.addWidget(self.mPVal)
        oMot.addLayout(hbox)
        
        hbox=QHBoxLayout()
        self.mB1=QPushButton(QCoreApplication.translate("mout"," left "))
        self.mB1.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.mB1)
        txt=QLabel("M1")
        txt.setStyleSheet("font-size: 20px;")
        txt.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        hbox.addWidget(txt)
        self.mB2=QPushButton(QCoreApplication.translate("mout","right"))
        self.mB2.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.mB2)        
        oMot.addLayout(hbox)

        hbox=QHBoxLayout()
        self.mB3=QPushButton(QCoreApplication.translate("mout","left"))
        self.mB3.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.mB3)
        txt=QLabel("M2")
        txt.setStyleSheet("font-size: 20px;")
        txt.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        hbox.addWidget(txt)
        self.mB4=QPushButton(QCoreApplication.translate("mout","right"))
        self.mB4.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.mB4)        
        oMot.addLayout(hbox)
        
        hbox=QHBoxLayout()
        self.mB5=QPushButton(QCoreApplication.translate("mout","left"))
        self.mB5.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.mB5)
        txt=QLabel("M3")
        txt.setStyleSheet("font-size: 20px;")
        txt.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        hbox.addWidget(txt)
        self.mB6=QPushButton(QCoreApplication.translate("mout","right"))
        self.mB6.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.mB6)        
        oMot.addLayout(hbox)
        
        hbox=QHBoxLayout()
        self.mB7=QPushButton(QCoreApplication.translate("mout","left"))
        self.mB7.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.mB7)
        txt=QLabel("M4")
        txt.setStyleSheet("font-size: 20px;")
        txt.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        hbox.addWidget(txt)
        self.mB8=QPushButton(QCoreApplication.translate("mout","right"))
        self.mB8.setStyleSheet("font-size: 20px;")
        hbox.addWidget(self.mB8)        
        oMot.addLayout(hbox)
        
        self.oMot.setLayout(oMot)
        
        io.addWidget(self.oMot)
        
        self.oMot.hide()
        
        self.mB1.pressed.connect(self.mB1_pressed)
        self.mB1.released.connect(self.mB1_released)
        self.mB2.pressed.connect(self.mB2_pressed)
        self.mB2.released.connect(self.mB2_released)
        self.mB3.pressed.connect(self.mB3_pressed)
        self.mB3.released.connect(self.mB3_released)
        self.mB4.pressed.connect(self.mB4_pressed)
        self.mB4.released.connect(self.mB4_released)
        self.mB5.pressed.connect(self.mB5_pressed)
        self.mB5.released.connect(self.mB5_released)
        self.mB6.pressed.connect(self.mB6_pressed)
        self.mB6.released.connect(self.mB6_released)
        self.mB7.pressed.connect(self.mB7_pressed)
        self.mB7.released.connect(self.mB7_released)
        self.mB8.pressed.connect(self.mB8_pressed)
        self.mB8.released.connect(self.mB8_released)
        
        self.mPower.valueChanged.connect(self.mPower_changed)
        
        # Back-button!
        io.addStretch()
        self.ioBack=QPushButton(QCoreApplication.translate("io","Back"))
        self.ioBack.setStyleSheet("font-size: 20px;")
        io.addWidget(self.ioBack)
        
        self.ioWidget.setLayout(io)
        
        self.ioFun.currentIndexChanged.connect(self.io_changed)
        self.iDCType.currentIndexChanged.connect(self.io_changed)
        self.ioBack.clicked.connect(self.xBack_clicked)
        
    def setMainWidget(self):
        self.setDWidget()
        self.setFWidget()
        self.setIOWidget()
        
        self.mainWidget=QWidget()
        mL=QVBoxLayout()
        mL.addWidget(self.dWidget)
        mL.addWidget(self.fWidget)
        mL.addWidget(self.ioWidget)
        
        self.dWidget.show()
        self.fWidget.hide()
        self.ioWidget.hide()
        
        self.mainWidget.setLayout(mL)
    
    def oB1_pressed(self):
        self.act_duino.comm("output_set O1 1 "+str(self.oPower.value()))
    def oB1_released(self):
        self.act_duino.comm("output_set O1 1 0")
    def oB2_pressed(self):
        self.act_duino.comm("output_set O2 1 "+str(self.oPower.value()))
    def oB2_released(self):
        self.act_duino.comm("output_set O2 1 0")
    def oB3_pressed(self):
        self.act_duino.comm("output_set O3 1 "+str(self.oPower.value()))
    def oB3_released(self):
        self.act_duino.comm("output_set O3 1 0")
    def oB4_pressed(self):
        self.act_duino.comm("output_set O4 1 "+str(self.oPower.value()))
    def oB4_released(self):
        self.act_duino.comm("output_set O4 1 0")
    def oB5_pressed(self):
        self.act_duino.comm("output_set O5 1 "+str(self.oPower.value()))
    def oB5_released(self):
        self.act_duino.comm("output_set O5 1 0")
    def oB6_pressed(self):
        self.act_duino.comm("output_set O6 1 "+str(self.oPower.value()))
    def oB6_released(self):
        self.act_duino.comm("output_set O6 1 0")
    def oB7_pressed(self):
        self.act_duino.comm("output_set O7 1 "+str(self.oPower.value()))
    def oB7_released(self):
        self.act_duino.comm("output_set O7 1 0")
    def oB8_pressed(self):
        self.act_duino.comm("output_set O8 1 "+str(self.oPower.value()))
    def oB8_released(self):
        self.act_duino.comm("output_set O8 1 0")
    def oPower_changed(self):
        self.oPVal.setText(str(self.oPower.value()))

    def mB1_pressed(self):
        self.act_duino.comm("motor_set M1 left "+str(self.oPower.value()))
    def mB1_released(self):
        self.act_duino.comm("motor_set M1 brake 0")
    def mB2_pressed(self):
        self.act_duino.comm("motor_set M1 right "+str(self.oPower.value()))
    def mB2_released(self):
        self.act_duino.comm("motor_set M1 brake 0")
    def mB3_pressed(self):
        self.act_duino.comm("motor_set M2 left "+str(self.oPower.value()))
    def mB3_released(self):
        self.act_duino.comm("motor_set M2 brake 0")
    def mB4_pressed(self):
        self.act_duino.comm("motor_set M2 right "+str(self.oPower.value()))
    def mB4_released(self):
        self.act_duino.comm("motor_set M2 brake 0")
    def mB5_pressed(self):
        self.act_duino.comm("motor_set M3 left "+str(self.oPower.value()))
    def mB5_released(self):
        self.act_duino.comm("motor_set M3 brake 0")
    def mB6_pressed(self):
        self.act_duino.comm("motor_set M3 right "+str(self.oPower.value()))
    def mB6_released(self):
        self.act_duino.comm("motor_set M3 brake 0")
    def mB7_pressed(self):
        self.act_duino.comm("motor_set M4 left "+str(self.oPower.value()))
    def mB7_released(self):
        self.act_duino.comm("motor_set M4 brake 0")
    def mB8_pressed(self):
        self.act_duino.comm("motor_set M4 right "+str(self.oPower.value()))
    def mB8_released(self):
        self.act_duino.comm("motor_set M4 brake 0")
    def mPower_changed(self):
        self.mPVal.setText(str(self.mPower.value()))
    
    def execFinished(self,returncode):
        self.menu.setDisabled(False)
        if returncode: # Returncode, da stimmt evtl. was nicht...
            return returncode
        return
    
    def exec_command(self, commandline):
            # run subprocess
            self.log_master_fd, self.log_slave_fd = pty.openpty()
            self.app_process = subprocess.Popen(commandline, stdout=self.log_slave_fd, stderr=self.log_slave_fd)
            self.app_process.returncode=False
            self.app_process.command=commandline[0]
            
            # start a timer to monitor the ptys
            self.log_timer = QTimer()
            self.log_timer.timeout.connect(self.on_log_timer)
            self.log_timer.start(10)
            
    def app_is_running(self):
        if self.app_process == None:
            return False

        return self.app_process.poll() == None
    
    def on_close(self):
        if self.app_is_running():
            self.app_process.terminate()
            self.app_process.wait()
        
    def on_log_timer(self):
        # first read whatever the process may have written
        if select.select([self.log_master_fd], [], [], 0)[0]:
            output = os.read(self.log_master_fd, 100)
            if output: 
                self.fCon.write(str(output, "utf-8"))
        else:
            # check if process is still alive
            if not self.app_is_running():
                time.sleep(1.0)
                while select.select([self.log_master_fd], [], [], 0)[0]:
                    output = os.read(self.log_master_fd, 100)
                    if output: 
                        self.fCon.write(str(output, "utf-8"))
                    time.sleep(0.01)
                    
                    self.fWidget.repaint()
                    self.processEvents()
                    self.fWidget.repaint()  
                
                if self.app_process.returncode:
                    self.fCon.write(self.app_process.command+" ended with return value " + str(self.app_process.returncode) + "\n")

                self.fWidget.repaint()
                self.processEvents()
                self.fWidget.repaint()
                
                # close any open ptys
                os.close(self.log_master_fd)
                os.close(self.log_slave_fd)

                # remove timer
                self.log_timer = None
                self.sigExecFinished.emit(self.app_process.returncode)
                
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)


