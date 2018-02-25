#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys, time, os, json, shutil
import threading as thd
from TouchStyle import *
from TouchAuxiliary import *
from robointerface import *
import ftrobopy as txt
import random, math
from datetime import datetime

import translator
from PyQt4 import QtCore, QtGui

try:
    import ftduino_direct as ftd
    FTDUINO_DIRECT=True
except:
    FTDUINO_DIRECT=False

# set serial path for libroboint (i.e. to use Intelligent Interface on USB-Serial-Adapter)
#RIFSERIAL="/dev/ttyUSB0"
RIFSERIAL=""

# do not check for missing interfaces
IGNOREMISSING=False

#FTTXTADDRESS="192.168.178.24"
FTTXTADDRESS="auto"

hostdir = os.path.dirname(os.path.realpath(__file__)) + "/"
projdir = hostdir + "projects/"
moddir  = hostdir + "modules/"
logdir  = hostdir + "logfiles/"
pixdir  = hostdir + "pixmaps/"

if not os.path.exists(projdir):
    os.mkdir(projdir)
if not os.path.exists(moddir):
    os.mkdir(moddir)
if not os.path.exists(logdir):
    os.mkdir(logdir)
    
try:
    with open(hostdir+"manifest","r", encoding="utf-8") as f:
        r=f.readline()
        while not "version" in r:
          r=f.readline()
        
        if "version" in r:
          vstring = "v" + r[ r.index(":")+2 : ]
        else: vstring=""
        f.close()
except:
    vstring="n/a"    

#
# set fallback locale information for webinterface
#

try:
    with open(hostdir+".locale","w") as f:
        r=f.write(translator.getActiveLocale())
        f.close()
except:
    pass
    

PORTRAIT=1
LANDSCAPE=0

TXTsndStack = [ "---", "Plane", "Alarm", "Bell", "Brakes", "Horn(short)", "Horn(long)", "WoodCrack", "Excavator", "Fantasy1", "Fantasy2", "Fantasy3", "Fantasy4", "Farm", "Emergency", "Fireplace", "Racecar", "Helicopter", "Hydraulic", "Engine", "EngineStart", "PropPlane", "RollerCoaster", "ShipHorn", "Tractor", "Truck", "EyeBlink", "HeadUp", "HeadDown"]

#
# some auxiliaries
#

def clean(text,maxlen):
    res=""
    valid="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_-."
    for ch in text:
        if ch in valid: res=res+ch
    return res[:maxlen]

def queryVarName(vari, recent):        
        if len(vari)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","Variables"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No Variables defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return recent

        vari.sort()
        
        cvari=vari[0]
        for i in vari:
            if i==recent: cvari=recent
            
        (s,r)=TouchAuxListRequester(QCoreApplication.translate("ecl","Variables"),QCoreApplication.translate("ecl","Select variable"),vari,cvari,"Okay").exec_()

        if s: return r 
        else: return recent
    
class QDblPushButton(QPushButton):
    doubleClicked = pyqtSignal()
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        QPushButton.__init__(self, *args, **kwargs)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.clicked.emit)
        super().clicked.connect(self.checkDoubleClick)

    @pyqtSlot()
    def checkDoubleClick(self):
        if self.timer.isActive():
            self.doubleClicked.emit()
            self.timer.stop()
        else:
            self.timer.start(250)

#
# the exec thread incl. parsing of the code
#
            
class execThread(QThread):
    updateText=pyqtSignal(str)
    clearText=pyqtSignal()
    execThreadFinished=pyqtSignal()
    showMessage=pyqtSignal(str)
    requestKeyboard=pyqtSignal(int, str)
    requestDial=pyqtSignal(str, int, int, int, str)
    requestBtn=pyqtSignal(str, str, list)
    canvasSig=pyqtSignal(str)
    
    def __init__(self, codeList, output, starter, RIF,TXT,FTD, parent):
        QThread.__init__(self, parent)
        
        self.codeList=codeList
        
        self.output=output
        self.starter=starter
        self.msg=0 # für Messages aus dem GUI Thread
        
        self.RIF=RIF
        self.TXT=TXT
        self.FTD=FTD
        self.parent=parent
        
        self.parent.msgBack.connect(self.msgBack)
        self.parent.IMsgBack.connect(self.IMsgBack)
        self.parent.stop.connect(self.stop)
        
    def run(self):
        
        self.parent.outputClicked.connect(self.goOn)
        
        self.halt=False
        self.trace=False
        self.singlestep=False
        self.nextStep=False
        self.logging=False
        
        self.requireTXT=False
        self.requireRIF=False
        self.requireFTD=False
        
        self.jmpTable=[]
        self.LoopStack=[]
        self.modTable=[]
        self.modStack=[]
        self.modLStack=[]
        self.modMStack=[]
        self.impmod=[]
        self.memory=[]
        
        cnt=0
        mcnt=0
        
        rif_m = [False, False, False, False]
        txt_m = [False, False, False, False]
        ftd_m = [False, False, False, False]
        rif_o = [False, False, False, False, False, False, False, False]
        txt_o = [False, False, False, False, False, False, False, False]
        ftd_o = [False, False, False, False, False, False, False, False]
        rif_i = [False, False, False, False, False, False, False, False]
        txt_i = [False, False, False, False, False, False, False, False]
        ftd_i = [False, False, False, False, False, False, False, False]
        
        #input types
        txt_it = [0,0,0,0,0,0,0,0] 
        ftd_it = [0,0,0,0,0,0,0,0]  # 1=switch 2=voltage 3=resistance 4=distance
        txt_c = [0,0,0,0]
        ftd_c = [0,0,0,0]            # 1=counter 2=distance
        
        # scan code for interfaces, jump and module tags, output and motor channels
        
        txtanaloginputfailure=""
        ftdanaloginputfailure=""
        ftdcounterinputfailure=""
        extmodfailure=False
        
        for line in self.codeList:
            a=line.split()
            if len(a)<2: a.append("x")
            
            if "TXT" in a[1]:
                self.requireTXT=True
            if "RIF" in a[1]:
                self.requireRIF=True
            if "FTD" in a[1]:
                self.requireFTD=True
            if "Tag" in line[:3]: 
                self.jmpTable.append([line[4:], cnt])
            elif "Module" in line[:6]:
                self.modTable.append([line[7:], cnt])
                mcnt=mcnt+1
            elif "MEnd" in line[:4]:
                mcnt=mcnt-1
            elif a[0] == "CallExt" and not (a[1] in self.impmod):
                try:
                    with open(moddir+a[1],"r", encoding="utf-8") as f:
                        module=json.load(f)
                        f.close()
                    nmp = len(self.codeList)
                    for mline in module:
                        self.codeList.append(mline)
                    self.impmod.append(a[1])
                    
                except:
                    extmodfailure=True
                    emf=a[1]
            
            #
            # configure i/o of the devices:
            #
            
            if len(a)>2:
                if ("Output"==a[0]) or ("WaitIn" in a[0]) or ("IfIn" in a[0]) or ("Motor" in a[0]) or ("QueryIn"==a[0]) or ("FromIn"==a[0]):
                    if a[1]=="RIF": 
                        if ("Motor" in a[0]):
                            rif_m[int(a[2])-1]=True
                        elif ("Output" in a[0]):
                            rif_o[int(a[2])-1]=True
                        elif ("IfInDig"==a[0]) or ("WaitInDig"==a[0]):
                            rif_i[int(a[2])-1]=True
                        elif (("IfIn"==a[0]) or ("WaitIn"==a[0])) and a[3]=="S":
                            rif_i[int(a[2])-1]=True
                        if "MotorP"==a[0]:
                            rif_i[int(a[3])-1]=True
                            rif_i[int(a[4])-1]=True
                        if "QueryIn"==a[0]:
                            pass
                            #if a[3]=="D": rif_i[int(a[2])-1]=True
                    elif a[1]=="TXT": #TXT
                        if ("Motor" in a[0]):
                            txt_m[int(a[2])-1]=True
                        elif ("Output" in a[0]):
                            txt_o[int(a[2])-1]=True
                        elif ("IfInDig"==a[0]) or ("WaitInDig"==a[0]):
                            txt_i[int(a[2])-1]=True
                        if "MotorP"==a[0]:
                            txt_i[int(a[3])-1]=True
                            txt_i[int(a[4])-1]=True
                        if "MotorE"==a[0]:
                            txt_i[int(a[3])-1]=True
                        if "MotorES"==a[0]:
                            txt_m[int(a[3])-1]=True
                        if "QueryIn"==a[0] or "IfIn"==a[0] or "WaitIn"==a[0] or "FromIn"==a[0]:
                            if (a[3]=="S" or a[3]=="R" or a[3]=="V" or a[3]=="D"):
                                txt_i[int(a[2])-1]=True
                                if (a[3]=="S"):
                                    if (txt_it[int(a[2])-1]==0) or (txt_it[int(a[2])-1]==1):
                                        txt_it[int(a[2])-1]=1
                                    else:
                                        txtanaloginputfailure=a[2]                                    
                                elif (a[3]=="R"):
                                    if (txt_it[int(a[2])-1]==0) or (txt_it[int(a[2])-1]==2):
                                        txt_it[int(a[2])-1]=2
                                    else:
                                        txtanaloginputfailure=a[2]  
                                elif (a[3]=="V"):
                                    if (txt_it[int(a[2])-1]==0) or (txt_it[int(a[2])-1]==3):
                                        txt_it[int(a[2])-1]=3
                                    else:
                                        txtanaloginputfailure=a[2]  
                                elif (a[3]=="D"):
                                    if (txt_it[int(a[2])-1]==0) or (txt_it[int(a[2])-1]==4):
                                        txt_it[int(a[2])-1]=4
                                    else:
                                        txtanaloginputfailure=a[2]
                            elif a[3]=="C":
                                txt_c[int(a[2])-1]=True
                    elif a[1]=="FTD": # ftduino
                        if ("Motor" in a[0]):
                            ftd_m[int(a[2])-1]=True
                        elif ("Output" in a[0]):
                            ftd_o[int(a[2])-1]=True
                        elif ("IfInDig"==a[0]) or ("WaitInDig"==a[0]):
                            ftd_i[int(a[2])-1]=True
                        if "MotorP"==a[0]:
                            ftd_i[int(a[3])-1]=True
                            ftd_i[int(a[4])-1]=True
                        if "MotorE"==a[0]:
                            ftd_i[int(a[3])-1]=True
                        if "MotorES"==a[0]:
                            ftd_m[int(a[3])-1]=True
                        if "QueryIn"==a[0] or "IfIn"==a[0] or "WaitIn"==a[0] or "FromIn"==a[0]:
                            if (a[3]=="S" or a[3]=="R" or a[3]=="V"):
                                ftd_i[int(a[2])-1]=True
                                if (a[3]=="S"):
                                    if (ftd_it[int(a[2])-1]==0) or (ftd_it[int(a[2])-1]==1):
                                        ftd_it[int(a[2])-1]=1
                                    else:
                                        ftdanaloginputfailure=a[2]                                    
                                elif (a[3]=="R"):
                                    if (ftd_it[int(a[2])-1]==0) or (ftd_it[int(a[2])-1]==2):
                                        ftd_it[int(a[2])-1]=2
                                    else:
                                        ftdanaloginputfailure=a[2]  
                                elif (a[3]=="V"):
                                    if (ftd_it[int(a[2])-1]==0) or (ftd_it[int(a[2])-1]==3):
                                        ftd_it[int(a[2])-1]=3
                                    else:
                                        ftdanaloginputfailure=a[2]  
                            elif a[3]=="C":                                
                                if (ftd_c[int(a[2])-1]==1) or (ftd_c[int(a[2])-1]==0):
                                    ftd_c[int(a[2])-1]=1
                                else:
                                    ftdcounterinputfailure=a[2] 
                            elif  a[3]=="D":
                                if (ftd_c[int(a[2])-1]==2) or (ftd_c[int(a[2])-1]==0):
                                    ftd_c[int(a[2])-1]=2
                                else:
                                    ftdcounterinputfailure=a[2] 
            cnt=cnt+1
        self.clrOut()
        
        if self.requireTXT and self.TXT==None:
            self.msgOut(QCoreApplication.translate("exec","TXT not found!\nProgram terminated\n"))
            if not IGNOREMISSING: self.stop()
        elif self.requireRIF and self.RIF==None:
            self.msgOut(QCoreApplication.translate("exec","RoboIF not found!\nProgram terminated\n"))
            if not IGNOREMISSING: self.stop()
        elif self.requireFTD and self.FTD==None:
            self.msgOut(QCoreApplication.translate("exec","ftduino not found!\nProgram terminated\n"))
            if not IGNOREMISSING: self.stop()
        elif extmodfailure:
            self.msgOut(QCoreApplication.translate("exec","External Module")+ " \n'"+emf+"' "+QCoreApplication.translate("exec","not found.\nProgram terminated\n"))
            self.stop()
        elif txtanaloginputfailure!="":
            self.msgOut(QCoreApplication.translate("exec","TXT analog I")+txtanaloginputfailure+QCoreApplication.translate("exec","\ntypes inconsistent!\nProgram terminated\n"))
            self.stop()
        elif ftdanaloginputfailure!="":
            self.msgOut(QCoreApplication.translate("exec","FTD analog I")+ftdanaloginputfailure+QCoreApplication.translate("exec","\ntypes inconsistent!\nProgram terminated\n"))
            self.stop()
        elif ftdcounterinputfailure!="":
            self.msgOut(QCoreApplication.translate("exec","FTD counter C")+ftdcounterinputfailure+QCoreApplication.translate("exec","\ncounter/distance mismatch!\nProgram terminated\n"))
            self.stop()
        elif mcnt<0:
            self.msgOut(QCoreApplication.translate("exec","MEnd found with-\nout Module!\nProgram terminated\n"))
            self.stop()
        elif mcnt>0:
            self.msgOut(QCoreApplication.translate("exec","MEnd missing!\nProgram terminated\n"))
            self.stop()
        elif txt_m[0] and (txt_o[0] or txt_o[1]):
            self.msgOut(QCoreApplication.translate("exec","TXT M1 and O1/O2\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif txt_m[1] and (txt_o[2] or txt_o[3]):
            self.msgOut(QCoreApplication.translate("exec","TXT M2 and O3/O4\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif txt_m[2] and (txt_o[4] or txt_o[5]):
            self.msgOut(QCoreApplication.translate("exec","TXT M3 and O5/O6\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif txt_m[3] and (txt_o[6] or txt_o[7]):
            self.msgOut(QCoreApplication.translate("exec","TXT M4 and O7/O8\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif rif_m[0] and (rif_o[0] or rif_o[1]):
            self.msgOut(QCoreApplication.translate("exec","RIF M1 and O1/O2\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif rif_m[1] and (rif_o[2] or rif_o[3]):
            self.msgOut(QCoreApplication.translate("exec","RIF M2 and O3/O4\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif rif_m[2] and (rif_o[4] or rif_o[5]):
            self.msgOut(QCoreApplication.translate("exec","RIF M3 and O5/O6\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif rif_m[3] and (rif_o[6] or rif_o[7]):
            self.msgOut(QCoreApplication.translate("exec","RIF M4 and O7/O8\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif ftd_m[0] and (ftd_o[0] or ftd_o[1]):
            self.msgOut(QCoreApplication.translate("exec","FTD M1 and O1/O2\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif ftd_m[1] and (ftd_o[2] or ftd_o[3]):
            self.msgOut(QCoreApplication.translate("exec","FTD M2 and O3/O4\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif ftd_m[2] and (ftd_o[4] or ftd_o[5]):
            self.msgOut(QCoreApplication.translate("exec","FTD M3 and O5/O6\nused in parallel!\nProgram terminated\n"))
            self.stop()
        elif ftd_m[3] and (ftd_o[6] or ftd_o[7]):
            self.msgOut(QCoreApplication.translate("exec","FTD M4 and O7/O8\nused in parallel!\nProgram terminated\n"))
            self.stop()        
        
        if not self.halt and self.RIF!=None:
            s = self.RIF.GetDeviceTypeString()
            if s=="Robo LT Controller":
                if rif_m[2] or rif_m[3]:
                    self.msgOut(QCoreApplication.translate("exec","M3 and M4 not available\non Robo LT!\nProgram terminated\n"))
                    self.stop()
                elif rif_o[4] or rif_o[5] or rif_o[6] or rif_o[7]:
                    self.msgOut(QCoreApplication.translate("exec","O5 to O8 not available\non Robo LT!\nProgram terminated\n"))
                    self.stop()
                elif rif_i[3] or rif_i[4] or rif_i[5] or rif_i[6] or rif_i[7]:
                    self.msgOut(QCoreApplication.translate("exec","I4 to I8 not available\non Robo LT!\nProgram terminated\n"))
                    self.stop()                
                
        # TXT I/O initialisieren...
        
        if self.TXT!=None and not self.halt:
            M = [ self.TXT.C_OUTPUT, self.TXT.C_OUTPUT, self.TXT.C_OUTPUT, self.TXT.C_OUTPUT ]
            I = [ (self.TXT.C_SWITCH, self.TXT.C_DIGITAL ),
                    (self.TXT.C_SWITCH, self.TXT.C_DIGITAL ),
                    (self.TXT.C_SWITCH, self.TXT.C_DIGITAL ),
                    (self.TXT.C_SWITCH, self.TXT.C_DIGITAL ),
                    (self.TXT.C_SWITCH, self.TXT.C_DIGITAL ),
                    (self.TXT.C_SWITCH, self.TXT.C_DIGITAL ),
                    (self.TXT.C_SWITCH, self.TXT.C_DIGITAL ),
                    (self.TXT.C_SWITCH, self.TXT.C_DIGITAL ) ]
            self.TXT.setConfig(M, I)
            self.TXT.updateConfig()
            self.TXT.updateWait()
            self.txt_i=[0,0,0,0,0,0,0,0]
            self.txt_m=[0,0,0,0]
            self.txt_o=[0,0,0,0,0,0,0,0]
            
            for i in range(0,8):
                if txt_o[i]:
                    self.txt_o[i]=self.TXT.output(i+1)
                if txt_i[i]:
                    if (txt_it[i]==1) or (txt_it[i]==0): self.txt_i[i]=self.TXT.input(i+1)
                    elif txt_it[i]==2: self.txt_i[i]=self.TXT.resistor(i+1)
                    elif txt_it[i]==3: self.txt_i[i]=self.TXT.voltage(i+1)
                    elif txt_it[i]==4: self.txt_i[i]=self.TXT.ultrasonic(i+1)
                    self.TXT.updateWait()
                if i<4:
                    if txt_m[i]: self.txt_m[i]=self.TXT.motor(i+1)
                
        # FTD I/O initialisieren...
        
        if self.FTD!=None and not self.halt:
            for i in range(0,8):           
                if ftd_it[i]==2:
                    self.FTD.comm("input_set_mode I"+str(i+1)+" Resistance")
                elif ftd_it[i]==3:
                    self.FTD.comm("input_set_mode I"+str(i+1)+" Voltage")
                if i<4:
                    if ftd_c[i]==1:
                        self.FTD.comm("counter_set_mode C"+str(i+1)+" Any")
                        
            if ftd_c[0]==2:
                self.FTD.comm("ultrasonic_enable True")
            else:
                self.FTD.comm("ultrasonic_enable False")
        
        # und los gehts
        
        self.cce=False #complete confusion error
        
        if not self.halt:
            self.msgOut("<Start>")
            self.count=0
        self.parent.processEvents()        
        
        self.interrupt=-1
        self.timestamp=time.time()
        
        try:
            while not self.halt and self.count<len(self.codeList):
                line=self.codeList[self.count]
                if self.trace: self.cmdPrint(str(self.count)+":"+line)
                self.parseLine(line)
                if self.singlestep:
                    while not self.nextStep and not self.halt:
                        self.parent.processEvents()
                        time.sleep(0.005)
                    self.nextStep=False
                    
                self.count=self.count+1
                self.parent.processEvents()
        except:
            self.cce=True
            self.halt=True
        
        if not self.halt: self.msgOut("<End>")
        else: 
            if self.cce: self.msgOut("CompleteConfusionError\nin line "+str(self.count)+":\n"+self.codeList[self.count])
            self.msgOut("<Break>")
        
        try:
            if self.logging: self.logfile.close()
        except:
            pass
        
        if self.RIF!=None:
            for i in range(1,9):
                self.RIF.SetOutput(i,0)
        
        if self.TXT!=None:
            for i in range(0,8):
                self.TXT.setPwm(i,0)
        
        if self.FTD!=None:
            for i in range(1,9):
                self.FTD.comm("output_set O"+str(i)+" 1 0")
        
        self.execThreadFinished.emit()
    
    def __del__(self):
    
        self.halt = True
        self.wait()
    
    def goOn(self):
        self.nextStep=True
    
    def stop(self):
        self.halt=True
    
    def msgBack(self, num):
        self.msg=num
    
    def IMsgBack(self,var):
        self.imesg=var
        
    def parseLine(self,line):
        stack=line.split()
        if stack[0]  == "#":
            if "TRACEON" in line:    self.trace=True
            elif "TRACEOFF" in line: self.trace=False
            if "STEPON" in line:     
                self.singlestep=True
                self.cmdPrint("STEPON: tap screen!")
            elif "STEPOFF" in line:  self.singlestep=False           
            if "GETELAPSEDTIME" in line:
                self.cmdPrint("[sec]: "+str(time.time()-self.timestamp))
            if "TIMERCLEAR" in line:
                self.timestamp=time.time()
            if "MEMDUMP" in line:
                self.cmdPrint("Memory dump")
                self.cmdPrint("-----------")
                for line in self.memory: self.cmdPrint(str(line))
                    
        elif stack[0]== "Stop":     self.count=len(self.codeList)
        elif stack[0]== "Output":   self.cmdOutput(stack)
        elif stack[0]== "Motor":    self.cmdMotor(stack)
        elif stack[0]== "MotorP":   self.cmdMotorPulsewheel(stack)
        elif stack[0]== "MotorE":   self.cmdMotorEncoder(stack)
        elif stack[0]== "MotorES":  self.cmdMotorEncoderSync(stack)
        elif stack[0]== "Delay":    self.cmdDelay(stack)
        elif stack[0]== "TimerQuery": self.cmdPrint("Timer: "+str(int((time.time()-self.timestamp)*1000)))
        elif stack[0]== "TimerClear": self.timestamp=time.time()
        elif stack[0]== "IfTimer":  self.cmdIfTimer(stack)
        elif stack[0]== "IfTime":   self.cmdIfTime(stack)
        elif stack[0]== "IfDate":   self.cmdIfDate(stack)
        elif stack[0]== "QueryNow": self.cmdQueryNow(stack)
        elif stack[0]== "Interrupt": self.cmdInterrupt(stack)
        elif stack[0]== "Jump":     self.cmdJump(stack)
        elif stack[0]== "LoopTo":   self.cmdLoopTo(stack)
        elif stack[0]== "WaitInDig": self.cmdWaitForInputDig(stack)
        elif stack[0]== "IfInDig":  self.cmdIfInputDig(stack)
        elif stack[0]== "WaitIn":   self.cmdWaitForInput(stack)
        elif stack[0]== "IfIn":     self.cmdIfInput(stack)
        elif stack[0]== "Print":    self.cmdPrint(line[6:])
        elif stack[0]== "QueryIn":  self.cmdQueryIn(stack)
        elif stack[0]== "Clear":    self.clrOut()
        elif stack[0]== "Message":  self.cmdMessage(line[8:])
        elif stack[0]== "Log":      self.cmdLog(stack)
        elif stack[0]== "Sound":    self.cmdSound(stack)
        elif stack[0]== "Module":   self.count=len(self.codeList)
        elif stack[0]== "Call":     self.cmdCall(stack)
        elif stack[0]== "CallExt":  self.cmdCall(stack)
        elif stack[0]== "Return":   self.cmdReturn()
        elif stack[0]== "MEnd":     self.cmdMEnd()
        elif stack[0]== "Init":     self.cmdInit(stack)
        elif stack[0]== "FromIn":   self.cmdFromIn(stack)
        elif stack[0]== "FromKeypad": self.cmdFromKeypad(stack)
        elif stack[0]== "FromDial": self.cmdFromDial(stack)
        elif stack[0]== "FromButtons": self.cmdFromButtons(stack)
        elif stack[0]== "FromRIIR": self.cmdFromRIIR(stack)
        elif stack[0]== "FromPoly": self.cmdFromPoly(stack) 
        elif stack[0]== "QueryVar": self.cmdQueryVar(stack)
        elif stack[0]== "Calc":     self.cmdCalc(stack)
        elif stack[0]== "IfVar":    self.cmdIfVar(stack)
        elif stack[0]== "Tag":      pass
        elif stack[0]== "Canvas":   self.cmdCanvas(stack)
        elif stack[0]== "CounterClear": self.cmdCounterClear(stack)
        
        else:
            self.cmdPrint("DontKnowWhatToDo\nin line:\n"+line)
            self.halt=True
        
        if time.time()>self.interrupt and self.interrupt>0:
            self.interruptExec()
    
    def interruptExec(self):
        self.cmdCall(self.interruptCommand.split())
        if self.interruptTime==0:
            self.interrupt=-1
            return
        else:
            self.interrupt=time.time()+self.interruptTime
            
    def getVal(self,var):
        try:
            return int(var)
        except:
            for i in self.memory:
                if i[0]==var: return int(i[1])
        self.halt=True
        self.cmdPrint("Variable '"+var+"'\nreferenced without\nInit!\nProgram terminated")
        return 0
    
    def cmdInterrupt(self,stack):
        if stack[1]=="Off":
            self.interrupt=-1
            self.interruptTime=0
        elif stack[1]=="After":
            self.interruptTime=0
            self.interrupt=time.time()+float(stack[2])/1000
            self.interruptCommand="Call "+stack[3]+" 1"
        elif stack[1]=="Every":
            self.interruptTime=float(stack[2])/1000
            self.interrupt=time.time()+self.interruptTime
            self.interruptCommand="Call "+stack[3]+" 1"
             
    def cmdCanvas(self, stack):
       self.canvasSig.emit(stack[1]) 
    
    def cmdInit(self,a):
        if len(a)<3: a.append("0")
        cc=0
        for i in self.memory:
            if i[0]==a[1]:
                self.memory[cc][1] = self.getVal(a[2])
                break
            cc=cc+1
        if cc==len(self.memory):
            self.memory.append([a[1], self.getVal(a[2])])
            
    def cmdFromKeypad(self, stack):
        v=self.getVal(stack[1])   # Variable
        v1=min(self.getVal(stack[2]),self.getVal(stack[3]) )  # min-wert
        v2=max(self.getVal(stack[2]),self.getVal(stack[3]) )  # max-wert
        
        if self.halt: return
        
        self.msg=0
        self.requestKeyboard.emit(v, stack[1])
        while self.msg==0:
            time.sleep(0.01)
        
        try:
            t=int(max(min(int(self.imesg),v2),v1))
        except:
            t=int(v)
        
        cc=0
        for i in self.memory:
            if i[0]==stack[1]:
                self.memory[cc][1] = t
                break
            cc=cc+1
        if cc==len(self.memory):        
            self.halt=True
            self.cmdPrint("Variable '"+stack[1]+"'\nreferenced without\nInit!\nProgram terminated")                 

    def cmdFromDial(self, stack):
        v=self.getVal(stack[1])   # Variable
        v1=min(self.getVal(stack[2]),self.getVal(stack[3]) )  # min-wert
        v2=max(self.getVal(stack[2]),self.getVal(stack[3]) )  # max-wert
        v3=""
        for a in range(4,len(stack)):
            v3=v3+stack[a]+" "
        v3=v3.strip()
        
        if self.halt: return
        
        self.msg=0
        self.requestDial.emit(v3,v,v1,v2, stack[1])
        while self.msg==0:
            time.sleep(0.01)
        
        try:
            t=max(min(int(self.imesg),v2),v1)
        except:
            t=v
        
        cc=0
        for i in self.memory:
            if i[0]==stack[1]:
                self.memory[cc][1] = t
                break
            cc=cc+1
        if cc==len(self.memory):        
            self.halt=True
            self.cmdPrint("Variable '"+stack[1]+"'\nreferenced without\nInit!\nProgram terminated")  
        
    def cmdFromRIIR(self, stack):        
        try:
            t=self.RIF.GetIR()
        except:
            t=-1
        
        cc=0
        for i in self.memory:
            if i[0]==stack[1]:
                self.memory[cc][1] = t
                break
            cc=cc+1
        if cc==len(self.memory):        
            self.halt=True
            self.cmdPrint("Variable '"+stack[1]+"'\nreferenced without\nInit!\nProgram terminated")      

    def cmdFromPoly(self, stack):
        a=float(stack[3])
        b=float(stack[4])
        c=float(stack[5])
        d=float(stack[6])
        
        x=self.getVal(stack[2])

        if self.halt: return
        
        y=(a*(x*x*x)) + (b*(x*x)) + (c*x) + d
        
        cc=0
        for i in self.memory:
            if i[0]==stack[1]:
                self.memory[cc][1] = y
                break
            cc=cc+1
        if cc==len(self.memory):        
            self.halt=True
            self.cmdPrint("Variable '"+stack[1]+"'\nreferenced without\nInit!\nProgram terminated")        
        
    def cmdCounterClear(self, stack):
        if stack[1]=="TXT":
            self.TXT.incrCounterCmdId(int(stack[2])-1)
        elif stack[1]=="FTD":
            a=self.FTD.comm("counter_clear C"+stack[2])
            
            
    def cmdQueryVar(self, stack):
        v=self.getVal(stack[1])
        if not self.halt:
            self.cmdPrint(stack[1]+": "+str(v))
            
    def cmdCalc(self, stack):
        v1=float(self.getVal(stack[2]))
        v2=float(self.getVal(stack[4]))
        if self.halt: return
    
        op=stack[3]
        res=0
        if op=="+": res=int(v1+v2)
        elif op=="-": res=int(v1-v2)
        elif op=="*": res=int(v1*v2)
        elif op=="/": res=int(round(v1/v2))
        elif op=="div": res=int(v1/v2)
        elif op=="digit":
            a=str(int(v2))
            b=len(a)
            if v1<=b:
                res=int(a[(b-int(v1)):((b-int(v1))+1)])
            else:
                res=-1
        elif op=="mod": res=int(v1 % v2)
        elif op=="exp": res=int(v1 ** v2)
        elif op=="root": res=int(v2 ** (1/v1))
        elif op=="min": res=int(min(v1,v2))
        elif op=="max": res=int(max(v1,v2))
        elif op=="sin": res=int(v1*math.sin(math.radians(v2)))
        elif op=="cos": res=int(v1*math.cos(math.radians(v2)))  
        elif op=="random": res=random.randint(min(v1,v2),max(v1,v2))
        elif op=="mean":
            res=(float(v1)+float(v2))/2
            if res > 0: res = int(res+0.5)
            elif res < 0: res = int(res-0.5)
            else: res =0
        elif op=="&&" and (v1!=0) and (v2!=0): res=1 
        elif op=="||" and ((v1!=0) or (v2!=0)): res=1
        elif op=="<"  and (v1<v2): res=1  
        elif op=="==" and (v1==v2): res=1 
        elif op=="!=" and (v1!=v2): res=1 
        elif op==">"  and (v1>v2): res=1 
        elif op==">=" and (v1>=v2): res=1 
        elif op=="<=" and (v1<=v2): res=1
        elif op=="tempMeingast":
            a=2.15992060279525E-07
            b=-0.007569625106584
            c=77.2415400995752
            res=int(v1/1000*(a*v2*v2+b*v2+c))
        
        cc=0
        for i in self.memory:
            if i[0]==stack[1]:
                self.memory[cc][1] = res
                break
            cc=cc+1
        if cc==len(self.memory):        
            self.halt=True
            self.cmdPrint("Variable '"+stack[1]+"'\nreferenced without\nInit!\nProgram terminated") 

    def cmdFromButtons(self, stack):
        v=stack[1]  # Variable

        if self.halt: return
      
        self.msg=0
        self.requestBtn.emit(v,"",stack[2:])
        while self.msg==0:
            time.sleep(0.01)
        
        try:
            t=int(self.imesg)
        except:
            t=-1
        
        cc=0
        for i in self.memory:
            if i[0]==stack[1]:
                self.memory[cc][1] = t
                break
            cc=cc+1
        if cc==len(self.memory):        
            self.halt=True
            self.cmdPrint("Variable '"+stack[1]+"'\nreferenced without\nInit!\nProgram terminated") 
    
    def cmdIfVar(self,stack):
        v1=self.getVal(stack[1])
        v2=self.getVal(stack[3])
        if self.halt: return
        
        res=False
        op=stack[2]
        if      (op=="<") and (v1<v2): res=True
        elif    (op==">") and (v1>v2): res=True
        elif    (op=="==") and (v1==v2): res=True
        elif    (op=="!=") and (v1!=v2): res=True
        elif    (op=="<=") and (v1<=v2): res=True
        elif    (op==">=") and (v1>=v2): res=True
        
        if res:
            n=-1
            for line in self.jmpTable:
                if stack[4]==line[0]: n=line[1]-1

            if n==-1:
                self.msgOut("IfVar jump tag not found!")
                self.halt=True
            else:
                self.count=n             
    
    def cmdFromIn(self, stack):
        v = ""
        var=stack[4]
        
        if stack[1] == "RIF":
            if stack[3]=="S":
                v=str(self.RIF.Digital(int(stack[2])))
            elif stack[3]=="V":
                if stack[2]=="1":
                    v=str(self.RIF.GetA1()*10)
                elif stack[2]=="2":
                    v=str(self.RIF.GetA2()*10)
            elif stack[3]=="R":
                if stack[2]=="X":
                    v=str(self.RIF.GetAX())
                elif stack[2]=="Y":
                    v=str(self.RIF.GetAY())
            elif stack[3]=="D":
                if stack[2]=="1":
                    v=str(self.RIF.GetD1())
                elif stack[2]=="2":
                    v=str(self.RIF.GetD2())
            elif stack[3]=="C":
                tx="Not yet implemented"                
        elif stack[1]== "TXT":
            self.TXT.updateWait()
            if stack[3]=="S":
                v=str(self.txt_i[int(stack[2])-1].state())
            elif stack[3]=="V":
                v=str(self.txt_i[int(stack[2])-1].voltage())
            elif stack[3]=="R":
                v=str(self.txt_i[int(stack[2])-1].value())
            elif stack[3]=="D":
                v=str(self.txt_i[int(stack[2])-1].distance())
            elif stack[3]=="C":
                v=str(self.TXT.getCurrentCounterValue(int(stack[2])-1))
        elif stack[1]== "FTD":
            if stack[3]=="S":
                v=self.FTD.comm("input_get i"+stack[2])
            elif stack[3]=="V":
                v=self.FTD.comm("input_get i"+stack[2])
            elif stack[3]=="R":
                v=self.FTD.comm("input_get i"+stack[2])
            elif stack[3]=="D":
                v=self.FTD.comm("ultrasonic_get")
            elif stack[3]=="C":
                v=self.FTD.comm("counter_get c"+stack[2])
        ### und noch der variable zuweisen...         
        cc=0
        for i in self.memory:
            if i[0]==stack[4]:
                self.memory[cc][1] = v
                break
            cc=cc+1
        if cc==len(self.memory):        
            self.halt=True
            self.cmdPrint("Variable '"+stack[4]+"'\nreferenced without\nInit!\nProgram terminated") 
            
    def cmdLog(self, stack):
        if stack[1]=="1" and not self.logging:
            self.logging=True
            try:
                self.logfile.close()
            except:
                pass
            
            try:
                lfn=logdir+"log"+time.strftime("%Y%m%d-%H%M%S")+".txt"
                while os.path.exists(lfn):
                    lfn=lfn+"-"
                self.logfile=open(lfn,"w",encoding="utf-8")
            except:
                self.cmdPrint("Could not write logfile.")
                self.logging=False
                
        elif stack[1]=="0":
            self.logging=False
            try:
                self.logfile.close()
            except:
                pass
        elif stack[1][0]=="C":
            try:
                shutil.rmtree(logdir, ignore_errors=True)
                if not os.path.exists(logdir):
                    os.mkdir(logdir)
            except:
                self.cmdPrint("Failed to remove\nall logfiles.")
                
    def cmdSound(self, stack):
        snd=TXTsndStack.index(stack[1])
        loop=min(max(self.getVal(stack[2]),1),29)
        vol= min(max(self.getVal(stack[3]),0),100)       
        if self.TXT:
            self.TXT.play_sound(snd,loop,vol)

    def cmdQueryIn(self, stack):
        tx = "" 
        v = ""
        
        for a in range(4,len(stack)):
            tx=tx+(stack[a])+" "
        tx=tx[:-1]
        
        if stack[1] == "RIF":
            if stack[3]=="S":
                v=str(self.RIF.Digital(int(stack[2])))
            elif stack[3]=="V":
                if stack[2]=="1":
                    v=str(self.RIF.GetA1()*10)
                elif stack[2]=="2":
                    v=str(self.RIF.GetA2()*10)
            elif stack[3]=="R":
                if stack[2]=="X":
                    v=str(self.RIF.GetAX())
                elif stack[2]=="Y":
                    v=str(self.RIF.GetAY())
            elif stack[3]=="D":
                if stack[2]=="1":
                    v=str(self.RIF.GetD1())
                elif stack[2]=="2":
                    v=str(self.RIF.GetD2())
            elif stack[3]=="C":
                tx="Not yet implemented"                
        elif stack[1]== "TXT":
            self.TXT.updateWait()
            if stack[3]=="S":
                v=str(self.txt_i[int(stack[2])-1].state())
            elif stack[3]=="V":
                v=str(self.txt_i[int(stack[2])-1].voltage())
            elif stack[3]=="R":
                v=str(self.txt_i[int(stack[2])-1].value())
            elif stack[3]=="D":
                v=str(self.txt_i[int(stack[2])-1].distance())
            elif stack[3]=="C":
                v=str(self.TXT.getCurrentCounterValue(int(stack[2])-1))
        elif stack[1]== "FTD":
            if stack[3]=="S":
                v=self.FTD.comm("input_get i"+stack[2])
            elif stack[3]=="V":
                v=self.FTD.comm("input_get i"+stack[2])
            elif stack[3]=="R":
                v=self.FTD.comm("input_get i"+stack[2])
            elif stack[3]=="D":
                v=self.FTD.comm("ultrasonic_get")
            elif stack[3]=="C":
                v=self.FTD.comm("counter_get c"+stack[2])
        
        self.cmdPrint(tx+" "+v)
    
    def cmdOutput(self, stack):
        v=self.getVal(stack[3])
        if self.halt: return
        
        if stack[1]=="RIF":
            self.RIF.SetOutput(int(stack[2]),v)
        elif stack[1]=="TXT":
            self.txt_o[int(stack[2])-1].setLevel(v)
        elif stack[1]=="FTD":
                self.FTD.comm("output_set O"+stack[2]+" 1 "+str(v)) 
            
    def cmdMotor(self, stack):
        v=self.getVal(stack[4])
        if self.halt: return
        
        if stack[1]=="RIF":
            self.RIF.SetMotor(int(stack[2]),stack[3], v)
        elif stack[1]=="TXT": # TXT
            if stack[3]=="s":
                self.txt_m[int(stack[2])-1].stop()
            elif stack[3]=="l":
                self.txt_m[int(stack[2])-1].setSpeed(v)
            elif stack[3]=="r":
                self.txt_m[int(stack[2])-1].setSpeed(0-v)
        elif stack[1]=="FTD": # FTD
            if stack[3]=="s":
                self.FTD.comm("motor_set M"+stack[2]+" brake 0")
            elif stack[3]=="l":
                self.FTD.comm("motor_set M"+stack[2]+" left "+str(v))
            elif stack[3]=="r":
                self.FTD.comm("motor_set M"+stack[2]+" right "+str(v))             
            
    def cmdMotorEncoderSync(self, stack):
        m=int(stack[2])      # Output No.
        o=int(stack[3])   # Sync output
        d=stack[4]      # Direction
        s=self.getVal(stack[5]) # speed
        n=self.getVal(stack[6]) # pulses
        
        if self.halt: return

        if d=="r":
            s=0-s
        
        self.txt_m[m-1].setDistance(n, syncto=self.txt_m[o-1])
        self.txt_m[o-1].setDistance(n, syncto=self.txt_m[m-1])
            
        self.txt_m[o-1].setSpeed(s)
        self.txt_m[m-1].setSpeed(s)

        if d!="s":
            while not ((self.txt_m[m-1].finished() and self.txt_m[o-1].finished()) or self.halt):
                self.TXT.updateWait()
        
        if n>0 or d=="s":
            self.txt_m[m-1].stop()     
            self.txt_m[o-1].stop()
            
    def cmdMotorEncoder(self, stack):
        m=int(stack[2])      # Output No.
        if stack[3] == "None": e = -1
        else: e = int(stack[3])   # End switch input
        d=stack[4]      # Direction
        s=self.getVal(stack[5]) # speed
        n=self.getVal(stack[6]) # pulses
        
        if self.halt: return        
        
        if e >-1:
            self.TXT.updateWait()
            if d=="l" and self.txt_i[e-1].state(): return

        if d=="r":
            s=0-s

        self.txt_m[m-1].setDistance(n)
        self.txt_m[m-1].setSpeed(s)

        while not (self.txt_m[m-1].finished() or self.halt):
            self.TXT.updateWait()
            if e>-1:
                if d=="l" and self.txt_i[e-1].state(): break
        
        self.txt_m[int(stack[2])-1].stop()  
    
    def cmdMotorPulsewheel(self, stack):
        m=int(stack[2])      # Output No.
        if stack[3] == "None": e = -1
        else: e = int(stack[3])   # End switch input
        p=int(stack[4]) # Pulse input
        d=stack[5]      # Direction
        s=self.getVal(stack[6]) # speed
        n=self.getVal(stack[7]) # pulses
        
        if self.halt: return
        
        if stack[1]=="RIF":
            if e>-1:
                if d=="l" and self.RIF.Digital(e): return
            
            a=self.RIF.Digital(p)
            self.RIF.SetMotor(m,d,s)
            c=0
            while c<n and not self.halt:
                if e>-1:
                    if d=="l" and self.RIF.Digital(e): break
                b=a
                a=self.RIF.Digital(p)
                if not a==b: c=c+1
            
            self.RIF.SetMotor(m,"s",0)
        elif stack[1]=="TXT": # TXT
            if e>-1:
                self.TXT.updateWait()
                if d=="l" and self.txt_i[e-1].state(): return
            
            self.TXT.updateWait()
            a=self.txt_i[p-1].state()

            if d=="r":
                s=0-s
                
            self.txt_m[m-1].setSpeed(s)
            c=0
            while c<n and not self.halt:
                if e>-1:
                    self.TXT.updateWait()
                    if d=="l" and self.txt_i[e-1].state(): break
                b=a
                self.TXT.updateWait()
                a=self.txt_i[p-1].state()
                if not a==b: c=c+1
            
            self.txt_m[int(stack[2])-1].stop()  
        elif stack[1]=="FTD": # FTD
            if e>-1:
                if d=="l" and (self.FTD.comm("input_get i"+str(e))=="1"): return
            
            a=int(self.FTD.comm("input_get i"+str(p)))

            if d=="r":
                self.FTD.comm("motor_set M"+str(m)+" right "+str(s)) 
            else:
                self.FTD.comm("motor_set M"+str(m)+" left "+str(s))             
            
            c=0
            while c<n and not self.halt:
                if e>-1:
                    if d=="l" and (self.FTD.comm("input_get i"+str(e))=="1"): break
                b=a
                a=int(self.FTD.comm("input_get i"+str(p)))
                if not a==b: c=c+1
            
            self.FTD.comm("motor_set M"+str(m)+" brake 0")
            
    def cmdDelay(self, stack):
        v=self.getVal(stack[1])
        if self.halt: return
        
        try:
            if stack[2]=="R":
                v=random.randint(0,v)
        except:
            pass
            
        self.sleeping=True
        self.sleeper=thd.Timer(float(v)/1000, self.wake)
        self.sleeper.start()
        
        while self.sleeping and not self.halt:
            time.sleep(0.001)
        
        self.sleeper.cancel()
        if self.halt:
            self.count=len(self.codeList)
            

    def wake(self):
        self.sleeping=False
        
    def cmdIfTimer(self, stack):
        v=float(self.getVal(stack[2]))
        if self.halt: return
        
        diff=(time.time()-self.timestamp)*1000
        
        if (stack[1]=="<" and diff<v) or (stack[1]==">" and diff>v):
            n=-1
            for line in self.jmpTable:
                if stack[3]==line[0]: n=line[1]-1

            if n==-1:
                self.msgOut("IfTimer jump tag not found!")
                self.halt=True
            else:
                self.count=n
            
    def cmdIfTime(self, stack):
        day=time.strftime("%H %M %S").split()
        
        for i in range(3):
            day[i]=int(day[i])
        
        yy=0
        mm=0
        dd=0
        
        if stack[2]!="-": yy=self.getVal(stack[2])
        else: day[0]=0
        if stack[3]!="-": mm=self.getVal(stack[3])
        else: day[1]=0
        if stack[4]!="-": dd=self.getVal(stack[4])
        else: day[2]=0
        
        if self.halt: return
        
        now=day[0]*10000+day[1]*100+day[2]
        then=yy*10000+mm*100+dd
        
        res=False
        op=stack[1]
        if now!=0:
            if      (op=="<") and (now<then): res=True
            elif    (op==">") and (now>then): res=True
            elif    (op=="==") and (now==then): res=True
            elif    (op=="!=") and (now!=then): res=True
        else:
            res=True
        
        if res:
            n=-1
            for line in self.jmpTable:
                if stack[5]==line[0]: n=line[1]-1

            if n==-1:
                self.msgOut("IfTime jump tag not found!")
                self.halt=True
            else:
                self.count=n   

    
    def cmdIfDate(self, stack):
        day=time.strftime("%Y %m %d %w").split()
        for i in range(4):
            day[i]=int(day[i])
        
        yy=0
        mm=0
        dd=0
        
        if stack[2]!="-": yy=self.getVal(stack[2])
        else: day[0]=0
        if stack[3]!="-": mm=self.getVal(stack[3])
        else: day[1]=0
        if stack[4]!="-": dd=self.getVal(stack[4])
        else: day[2]=0
        if stack[5]!="-": wd=self.getVal(stack[5])
        else: wd=day[3]=-1
        
        if self.halt: return
        
        now=day[0]*10000+day[1]*100+day[2]
        then=yy*10000+mm*100+dd
        
        res=False
        op=stack[1]
        if now!=0:
            if      (op=="<") and (now<then): res=True
            elif    (op==">") and (now>then): res=True
            elif    (op=="==") and (now==then): res=True
            elif    (op=="!=") and (now!=then): res=True
        else:
            res=True
            
        if (wd!=-1) and res:#
            res=False
            now=day[3]
            then=wd
            if      (op=="<") and (now<wd): res=True
            elif    (op==">") and (now>then): res=True
            elif    (op=="==") and (now==then): res=True
            elif    (op=="!=") and (now!=then): res=True
        
        if res:
            n=-1
            for line in self.jmpTable:
                if stack[6]==line[0]: n=line[1]-1

            if n==-1:
                self.msgOut("IfDate jump tag not found!")
                self.halt=True
            else:
                self.count=n 
                
    def cmdQueryNow(self, stack):
        self.cmdPrint("Now: "+time.strftime("%Y-%m-%d_%H:%M:%S"))
                
    def cmdJump(self,stack):
        n=-1
        for line in self.jmpTable:
            if stack[1]==line[0]: n=line[1]
        if n==-1:
            self.msgOut("Jump tag not found!")
            self.halt=True
        else:
            self.count=n
            
    def cmdLoopTo(self,stack):
        v=self.getVal(stack[2])
        if self.halt: return
    
        found=False
        for n in range(0,len(self.LoopStack)):
            if self.count==self.LoopStack[n][0]:
                self.LoopStack[n][1]=self.LoopStack[n][1]-1
                if self.LoopStack[n][1]>0:
                    self.count=self.LoopStack[n][2]
                else:
                    if self.LoopStack[n][2]<self.count:
                        self.LoopStack.pop(n)
                found=True
                break
        if not found:
            tgt=-1
            for line in self.jmpTable:
                if stack[1]==line[0]: tgt=line[1]-1
            if tgt==-1:
                self.msgOut("LoopTo tag not found!")
                self.halt=True
            else:
                if v>1:
                    if tgt>self.count:
                        self.LoopStack.append([self.count, v, tgt])
                    else:
                        self.LoopStack.append([self.count, v-1, tgt])
                    self.count=tgt
        
    def cmdWaitForInputDig(self,stack):
        self.tOut=False
        self.tAct=False
        
        if len(stack)>4:
            v=self.getVal(stack[4])
            if self.halt: return
            if v>0:
                self.timer = QTimer()
                self.timer.setSingleShot(True)
                self.timer.timeout.connect(self.timerstop)
                self.timer.start(v)  
                self.tAct=True

        if stack[1]=="RIF":
            if stack[3]=="Raising":
                a=self.RIF.Digital(int(stack[2]))
                b=a
                while not (b<a or self.halt or self.tOut ): 
                    b=a
                    a=self.RIF.Digital(int(stack[2]))
                    self.parent.processEvents()
                    time.sleep(0.001)
            elif stack[3]=="Falling":
                a=self.RIF.Digital(int(stack[2]))
                b=a
                while not (b>a or self.halt or self.tOut ): 
                    b=a
                    a=self.RIF.Digital(int(stack[2]))
                    self.parent.processEvents()
                    time.sleep(0.001)
        elif stack[1]=="TXT": # TXT
            if stack[3]=="Raising":
                self.TXT.updateWait()
                a=self.txt_i[int(stack[2])-1].state()
                b=a
                while not (b<a or self.halt or self.tOut ): 
                    b=a
                    self.TXT.updateWait()
                    a=self.txt_i[int(stack[2])-1].state()
                    self.parent.processEvents()
                    time.sleep(0.001)
            elif stack[3]=="Falling":
                self.TXT.updateWait()
                a=self.txt_i[int(stack[2])-1].state()
                b=a
                while not (b>a or self.halt or self.tOut ): 
                    b=a
                    self.TXT.updateWait()
                    a=self.txt_i[int(stack[2])-1].state()
                    self.parent.processEvents()
                    time.sleep(0.001)
        elif stack[1]=="FTD": # FTD
            if stack[3]=="Raising":
                a=int(self.FTD.comm("input_get i"+stack[2]))
                b=a
                while not (b<a or self.halt or self.tOut ): 
                    b=a
                    a=int(self.FTD.comm("input_get i"+stack[2]))
                    self.parent.processEvents()
                    time.sleep(0.001)
            elif stack[3]=="Falling":
                a=int(self.FTD.comm("input_get i"+stack[2]))
                b=a
                while not (b>a or self.halt or self.tOut ): 
                    b=a
                    a=int(self.FTD.comm("input_get i"+stack[2]))
                    self.parent.processEvents()
                    time.sleep(0.001)
                    
        if self.tAct:
            self.timer.stop()
        
    def timerstop(self):
        self.tOut=True            
    
    def cmdWaitForInput(self,stack):
        tx = ""
        v=-1
        
        self.tOut=False
        self.tAct=False
        
        if len(stack)>6:
            v=self.getVal(stack[6])
            if self.halt: return
            if v>0:
                self.timer = QTimer()
                self.timer.setSingleShot(True)
                self.timer.timeout.connect(self.timerstop)
                self.timer.start(v)  
                self.tAct=True

        
        j=False
        while not (j or self.halt or self.tOut):
            self.parent.processEvents()
            if stack[1] == "RIF":
                if stack[3]=="S":
                    v=float(self.RIF.Digital(int(stack[2])))
                elif stack[3]=="V":
                    if stack[2]=="1":
                        v=float(self.RIF.GetA1())*10
                    elif stack[2]=="2":
                        v=float(self.RIF.GetA2())*10
                elif stack[3]=="R":
                    if stack[2]=="X":
                        v=float(self.RIF.GetAX())
                    elif stack[2]=="Y":
                        v=float(self.RIF.GetAY())
                elif stack[3]=="D":
                    if stack[2]=="1":
                        v=float(self.RIF.GetD1())
                    elif stack[2]=="2":
                        v=float(self.RIF.GetD2())
                elif stack[3]=="C":
                    tx="Not yet implemented"                
            elif stack[1]== "TXT":
                self.TXT.updateWait()
                if stack[3]=="S":
                    v=float(self.txt_i[int(stack[2])-1].state())
                elif stack[3]=="V":
                    v=float(self.txt_i[int(stack[2])-1].voltage())
                elif stack[3]=="R":
                    v=float(self.txt_i[int(stack[2])-1].value())
                elif stack[3]=="D":
                    v=float(self.txt_i[int(stack[2])-1].distance())
                elif stack[3]=="C":
                    v=float(self.TXT.getCurrentCounterValue(int(stack[2])-1))
            elif stack[1]== "FTD":
                if stack[3]=="S":
                    v=float(self.FTD.comm("input_get i"+stack[2]))
                elif stack[3]=="V":
                    v=float(self.FTD.comm("input_get i"+stack[2]))
                elif stack[3]=="R":
                    v=float(self.FTD.comm("input_get i"+stack[2]))
                elif stack[3]=="D":
                    v=float(self.FTD.comm("ultrasonic_get"))
                elif stack[3]=="C":
                    v=self.FTD.comm("counter_get c"+stack[2])
        
            val=float(self.getVal(stack[5]))
            if self.halt: return

            j=False

            if stack[4]=="<" and (v<val): j=True
            elif stack[4]=="==" and (v==val): j=True
            elif stack[4]=="!=" and (v!=val): j=True
            elif stack[4]==">" and (v>val): j=True
            elif stack[4]==">=" and (v>=val): j=True
            elif stack[4]=="<=" and (v<=val): j=True
            self.parent.processEvents()
            time.sleep(0.001)
        # stop gedrueckt?    
        if self.tAct:
            self.timer.stop()
        self.parent.processEvents()
    
    def cmdIfInputDig(self,stack):
        if stack[1]=="RIF":
            if (stack[3]=="True" and self.RIF.Digital(int(stack[2]))) or (stack[3]=="False" and not self.RIF.Digital(int(stack[2]))):
                n=-1
                for line in self.jmpTable:
                    if stack[4]==line[0]: n=line[1]-1

                if n==-1:
                    self.msgOut("IfInputDig jump tag not found!")
                    self.halt=True
                else:
                    self.count=n        
        elif stack[1]=="TXT":
            self.TXT.updateWait()
            if (stack[3]=="True" and self.txt_i[int(stack[2])-1].state()) or (stack[3]=="False" and not self.txt_i[int(stack[2])-1].state()):
                n=-1
                for line in self.jmpTable:
                    if stack[4]==line[0]: n=line[1]-1

                if n==-1:
                    self.msgOut("IfInputDig jump tag not found!")
                    self.halt=True
                else:
                    self.count=n
        elif stack[1]=="FTD":
            v=(self.FTD.comm("input_get i"+stack[2]))
            if (stack[3]=="True" and (v=="1")) or (stack[3]=="False" and (v!="1")):
                n=-1
                for line in self.jmpTable:
                    if stack[4]==line[0]: n=line[1]-1

                if n==-1:
                    self.msgOut("IfInputDig jump tag not found!")
                    self.halt=True
                else:
                    self.count=n
            
    def cmdIfInput(self,stack):
        tx = ""
        v=-1
        
        if stack[1] == "RIF":
            if stack[3]=="S":
                v=float(self.RIF.Digital(int(stack[2])))
            elif stack[3]=="V":
                if stack[2]=="1":
                    v=float(self.RIF.GetA1())*10
                elif stack[2]=="2":
                    v=float(self.RIF.GetA2())*10
            elif stack[3]=="R":
                if stack[2]=="X":
                    v=float(self.RIF.GetAX())
                elif stack[2]=="Y":
                    v=float(self.RIF.GetAY())
            elif stack[3]=="D":
                if stack[2]=="1":
                    v=float(self.RIF.GetD1())
                elif stack[2]=="2":
                    v=float(self.RIF.GetD2())
            elif stack[3]=="C":
                tx="Not yet implemented"                
        elif stack[1]== "TXT":
            self.TXT.updateWait()
            if stack[3]=="S":
                v=float(self.txt_i[int(stack[2])-1].state())
            elif stack[3]=="V":
                v=float(self.txt_i[int(stack[2])-1].voltage())
            elif stack[3]=="R":
                v=float(self.txt_i[int(stack[2])-1].value())
            elif stack[3]=="D":
                v=float(self.txt_i[int(stack[2])-1].distance())
            elif stack[3]=="C":
                v=float(self.TXT.getCurrentCounterValue(int(stack[2])-1))
        elif stack[1]== "FTD":
            if stack[3]=="S":
                v=float(self.FTD.comm("input_get i"+stack[2]))
            elif stack[3]=="V":
                v=float(self.FTD.comm("input_get i"+stack[2]))
            elif stack[3]=="R":
                v=float(self.FTD.comm("input_get i"+stack[2]))
            elif stack[3]=="D":
                v=float(self.FTD.comm("ultrasonic_get"))
            elif stack[3]=="C":
                v=self.FTD.comm("counter_get c"+stack[2])
    
        val=float(self.getVal(stack[5]))
        if self.halt: return

        j=False

        if stack[4]=="<" and (v<val): j=True
        elif stack[4]=="==" and (v==val): j=True
        elif stack[4]=="!=" and (v!=val): j=True
        elif stack[4]==">" and (v>val): j=True
        elif stack[4]==">=" and (v>=val): j=True
        elif stack[4]=="<=" and (v<=val): j=True
        
        if j:
            n=-1
            for line in self.jmpTable:
                if stack[6]==line[0]: n=line[1]-1

            if n==-1:
                self.msgOut("IfInput jump tag not found!")
                self.halt=True
            else:
                self.count=n        
                
    def cmdCall(self, stack):
        n=-1
        for line in self.modTable:
            if stack[1]==line[0]: n=line[1]
        
        if n==-1:
            self.msgOut("Call module "+stack[1]+" not found!")
            self.halt=True
        else:
            self.modStack.append(self.count)
            self.modMStack.append(n)

            if len(stack)>2:
                self.modLStack.append(self.getVal(stack[2])-1)
            else:
                self.modLStack.append(0)
            self.count=n
        
    def cmdReturn(self):
        if self.modLStack[len(self.modLStack)-1]==0:
            self.modLStack.pop()
            self.modMStack.pop()
            self.count=self.modStack.pop()#[1]
        else:
            self.count=self.modMStack[len(self.modLStack)-1]
            self.modLStack[len(self.modLStack)-1]=self.modLStack[len(self.modLStack)-1]-1

    def cmdMEnd(self):
        try:
            if self.modLStack[len(self.modLStack)-1]==0:
                self.modLStack.pop()
                self.modMStack.pop()
                self.count=self.modStack.pop()#[1]
            else:
                self.count=self.modMStack[len(self.modLStack)-1]
                self.modLStack[len(self.modLStack)-1]=self.modLStack[len(self.modLStack)-1]-1
        except:
            self.msgOut("Unexpected MEnd!")
            self.halt=True
    
    
    def cmdPrint(self, message):
        self.msgOut(message)
        if self.logging:
            self.logfile.write(message+"\n")
         
    def cmdMessage(self, rawline):
        self.msg=0
        self.showMessage.emit(rawline)
        while self.msg==0:
            time.sleep(0.001)
        self.msg=0
    
    def msgOut(self,message):
        self.msg=0
        self.updateText.emit(message)
        while self.msg==0:
            pass
        self.msg=0
        
    def clrOut(self):
        self.msg=0
        self.clearText.emit()
        while self.msg==0:
            pass
        self.msg=0
#
#
# GUI classes for editing command lines
#
#

class editWaitForInputDig(TouchDialog):
    def __init__(self, cmdline, vari, parent):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","WaitInDig"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["RIF","TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(1)
        if self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(2)
        
        k1.addWidget(self.interface)
        
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)
        
        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])

        self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        k2.addWidget(self.port)
        
        k9=QHBoxLayout()
        k9.addLayout(k1)
        k9.addStretch()
        k9.addLayout(k2)
        
        self.layout.addLayout(k9)
        
        l=QLabel(QCoreApplication.translate("ecl","Condition"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)     
        
        self.thd=QComboBox()
        self.thd.setStyleSheet("font-size: 20px;")
        self.thd.addItems(["Raising","Falling"])
        if self.cmdline.split()[3]=="Falling": self.thd.setCurrentIndex(1)
        self.layout.addWidget(self.thd)
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl","Timeout"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        self.value.setText(self.cmdline.split()[4])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        self.layout.addWidget(self.value)
        
        self.layout.addStretch()
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="WaitInDig " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " " + self.thd.currentText() + " " + self.value.text()
        self.close()

    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        self.value.setText(queryVarName(self.variables,self.value.text()))  
    
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","TOut"),a,None).exec_()
        try:
            t=str(max(min(int(t),99999),0))
        except:
            t=a
        self.value.setText(t)

class editIfInputDig(TouchDialog):
    def __init__(self, cmdline, taglist, vari, parent):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","IfInDig"), parent)
        
        self.cmdline=cmdline
        self.taglist=taglist
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["RIF","TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(1)
        if self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(2)

        k1.addWidget(self.interface)
        
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)
        
        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])

        self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        k2.addWidget(self.port)
        
        k9=QHBoxLayout()
        k9.addLayout(k1)
        k9.addStretch()
        k9.addLayout(k2)
        
        self.layout.addLayout(k9)
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl","Condition"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)     
        
        self.thd=QComboBox()
        self.thd.setStyleSheet("font-size: 20px;")
        self.thd.addItems(["True","False"])
        if self.cmdline.split()[3]=="False": self.thd.setCurrentIndex(1)
        self.layout.addWidget(self.thd)
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl","Target"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)
        
        self.tags=QComboBox()
        self.tags.setStyleSheet("font-size: 20px;")
        self.tags.addItems(self.taglist)
        
        try:
            t=0
            for tag in self.taglist:
               if self.taglist[t]==self.cmdline.split()[4]: self.tags.setCurrentIndex(t)
               t=t+1
        except:
            self.tags.setCurrentIndex(0)

            
        self.layout.addWidget(self.tags)
        self.layout.addStretch()
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="IfInDig " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " " + self.thd.currentText() + " " + self.tags.itemText(self.tags.currentIndex())
        self.close()

class editCounterClear(TouchDialog):
    def __init__(self, cmdline, parent):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","CounterClear"), parent)
        
        self.cmdline=cmdline
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(0)
        if self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(1)

        k1.addWidget(self.interface)
        
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)
        
        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItems(["C 1","C 2","C 3","C 4"])

        self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        k2.addWidget(self.port)
        
        k9=QHBoxLayout()
        k9.addLayout(k1)
        k9.addStretch()
        k9.addLayout(k2)
        
        self.layout.addLayout(k9)
        self.layout.addStretch()
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="CounterClear " +self.interface.currentText()+ " " + self.port.currentText()[2:]
        self.close()

class editOutput(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","Output"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["RIF","TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(1)
        if self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(2)
        self.interface.currentIndexChanged.connect(self.ifChanged)
        k1.addWidget(self.interface)
        
        #self.layout.addStretch()
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)
        
        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItems(["O 1","O 2","O 3","O 4","O 5","O 6","O 7","O 8"])

        self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        k2.addWidget(self.port)
        
        k9=QHBoxLayout()
        k9.addLayout(k1)
        k9.addStretch()
        k9.addLayout(k2)
        
        self.layout.addLayout(k9)
        
        l=QLabel(QCoreApplication.translate("ecl","Value"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        self.value.setText(self.cmdline.split()[3])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        self.layout.addWidget(self.value)
        
        self.layout.addStretch()
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="Output " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " " + self.value.text()
        self.close()
    
    def ifChanged(self):
        self.valueChanged()

    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        self.value.setText(queryVarName(self.variables,self.value.text()))  
    
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Value"),a,self).exec_()
        try:
            self.value.setText(str(int(t)))
        except:
            
            self.value.setText(a)
            
        self.valueChanged()
        
    def valueChanged(self):
        try:            
            if self.interface.currentIndex()==0: self.value.setText(str(max(0,min(7,int(self.value.text())))))
            else: self.value.setText(str(max(0,min(512,int(self.value.text())))))
        except:
            pass

class editMotor(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","Motor"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
        
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["RIF","TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(1)
        if self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(2)
        self.interface.currentIndexChanged.connect(self.ifChanged)
        k1.addWidget(self.interface)
        
        #self.layout.addStretch()
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)
        
        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItems(["M 1","M 2","M 3","M 4"])

        self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        k2.addWidget(self.port)
        
        k8=QHBoxLayout()
        k8.addLayout(k1)
        k8.addStretch()
        k8.addLayout(k2)
        
        self.layout.addLayout(k8)        
        
        k3=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Value"))
        l.setStyleSheet("font-size: 20px;")
        k3.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        self.value.setText(self.cmdline.split()[4])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        k3.addWidget(self.value)
        
        k4=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Direction"))
        l.setStyleSheet("font-size: 20px;")
        k4.addWidget(l)
        
        self.direction=QComboBox()
        self.direction.setStyleSheet("font-size: 20px;")
        self.direction.addItems([QCoreApplication.translate("ecl","right"),QCoreApplication.translate("ecl","left"),QCoreApplication.translate("ecl","stop")])
        if self.cmdline.split()[3][:1]=="r": self.direction.setCurrentIndex(0)
        elif self.cmdline.split()[3][:1]=="l": self.direction.setCurrentIndex(1)
        elif self.cmdline.split()[3][:1]=="s": self.direction.setCurrentIndex(2)
        k4.addWidget(self.direction)
        
        k9=QHBoxLayout()
        k9.addLayout(k3)
        k9.addStretch()
        k9.addLayout(k4)
        
        self.layout.addLayout(k9)
        
        
        self.layout.addStretch()
        
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="Motor " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " "
        if self.direction.currentIndex()==0: d="r"
        elif self.direction.currentIndex()==1: d="l"
        elif self.direction.currentIndex()==2:
            d="s"
            self.value.setText("0")
            
        self.cmdline=self.cmdline + d + " " + self.value.text()
        self.close()
    
    def ifChanged(self):
        self.valueChanged()
        
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        self.value.setText(queryVarName(self.variables,self.value.text()))  
    
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Value"),a,self).exec_()
        try:
            self.value.setText(str(int(t)))
        except:
            
            self.value.setText(a)
            
        self.valueChanged()
        
    def valueChanged(self):
        try:            
            if self.interface.currentIndex()==0: self.value.setText(str(max(0,min(7,int(self.value.text())))))
            else: self.value.setText(str(max(0,min(512,int(self.value.text())))))
        except:
            pass
        
class editMotorPulsewheel(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","MotorP"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["RIF","TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(1)
        if self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(2)
        
        self.interface.currentIndexChanged.connect(self.ifChanged)
        k1.addWidget(self.interface)
        
        #self.layout.addStretch()
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)
        
        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItems(["M 1","M 2","M 3","M 4"])

        self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        k2.addWidget(self.port)
        
        k8=QHBoxLayout()
        k8.addLayout(k1)
        k8.addStretch()
        k8.addLayout(k2)
        
        self.layout.addLayout(k8)        
        
        k3=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Value"))
        l.setStyleSheet("font-size: 20px;")
        k3.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        self.value.setText(self.cmdline.split()[6])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        k3.addWidget(self.value)
        
        k4=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Direction"))
        l.setStyleSheet("font-size: 20px;")
        k4.addWidget(l)
        
        self.direction=QComboBox()
        self.direction.setStyleSheet("font-size: 20px;")
        self.direction.addItems([QCoreApplication.translate("ecl","right"),QCoreApplication.translate("ecl","left"),QCoreApplication.translate("ecl","stop")])
        if self.cmdline.split()[5][:1]=="r": self.direction.setCurrentIndex(0)
        elif self.cmdline.split()[5][:1]=="l": self.direction.setCurrentIndex(1)
        elif self.cmdline.split()[5][:1]=="s": self.direction.setCurrentIndex(2)
        k4.addWidget(self.direction)
        
        k9=QHBoxLayout()
        k9.addLayout(k3)
        k9.addStretch()
        k9.addLayout(k4)
        
        self.layout.addLayout(k9)
    
        self.layout.addStretch()
        
        k5=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "End Sw."))
        l.setStyleSheet("font-size: 20px;")
        
        k5.addWidget(l)
        
        self.endSw=QComboBox()
        self.endSw.setStyleSheet("font-size: 20px;")
        self.endSw.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
        self.endSw.setCurrentIndex(int(self.cmdline.split()[3])-1)

        k5.addWidget(self.endSw)
        
        #self.layout.addStretch()
        
        k6=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Pulse Inp."))
        l.setStyleSheet("font-size: 20px;")
        k6.addWidget(l)
        
        self.pulseSw=QComboBox()
        self.pulseSw.setStyleSheet("font-size: 20px;")
        self.pulseSw.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])

        self.pulseSw.setCurrentIndex(int(self.cmdline.split()[4])-1)
        k6.addWidget(self.pulseSw)
        
        k10=QHBoxLayout()
        k10.addLayout(k5)
        k10.addStretch()
        k10.addLayout(k6)
        
        self.layout.addLayout(k10)
        self.layout.addStretch()
        
        k13=QHBoxLayout()
        
        k11=QLabel("Pulses")
        k11.setStyleSheet("font-size: 20px;")
        
        k13.addWidget(k11)
        k13.addStretch()
        
        self.pulses=QLineEdit(self.cmdline.split()[7])
        self.pulses.setReadOnly(True)
        self.pulses.setStyleSheet("font-size: 20px;")
        self.pulses.mousePressEvent=self.plsPress
        self.pulses.mouseReleaseEvent=self.plsRelease
        k13.addWidget(self.pulses)
        
        self.layout.addLayout(k13)
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="MotorP " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " "
        self.cmdline=self.cmdline + self.endSw.currentText()[2:] + " " + self.pulseSw.currentText()[2:] + " "
        
        if self.direction.currentIndex()==0: d="r"
        elif self.direction.currentIndex()==1: d="l"
        elif self.direction.currentIndex()==2:
            d="s"
            self.value.setText("0")
            
        self.cmdline=self.cmdline + d + " " + self.value.text()
        self.cmdline=self.cmdline + " " + self.pulses.text()
        self.close()
    
    def ifChanged(self):
        self.valueChanged()
    
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btn=1
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        if self.btn==1: self.value.setText(queryVarName(self.variables,self.value.text()))  
        else:           self.pulses.setText(queryVarName(self.variables,self.pulses.text())) 
            
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Value"),a,self).exec_()
        try:
            self.value.setText(str(int(t)))
        except:
            self.value.setText(a)
            
        self.valueChanged()
        
    def valueChanged(self):
        try:            
            if self.interface.currentIndex()==0: self.value.setText(str(max(0,min(7,int(self.value.text())))))
            else: self.value.setText(str(max(0,min(512,int(self.value.text())))))
        except:
            pass
        
    def plsPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.btn=2
        self.timer.start(500)
     
    def plsRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.pulses.text())
            except:
                self.pulses.setText("0")  
            self.getPulses(1)
            
    def getPulses(self,m):
        a=self.pulses.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Pulses"),a,self).exec_()
        try:
            if int(t)<0: t=str(0)
            if int(t)>9999: t=str(9999)
            t=str(int(t))
        except:
            t=a
        self.pulses.setText(t)
      
class editMotorEncoder(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","MotorE"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["TXT"])

        self.interface.currentIndexChanged.connect(self.ifChanged)
        k1.addWidget(self.interface)
        
        #self.layout.addStretch()
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)
        
        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItems(["M 1","M 2","M 3","M 4"])

        self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        k2.addWidget(self.port)
        
        k8=QHBoxLayout()
        k8.addLayout(k1)
        k8.addStretch()
        k8.addLayout(k2)
        
        self.layout.addLayout(k8)        
        
        k3=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Value"))
        l.setStyleSheet("font-size: 20px;")
        k3.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        self.value.setText(self.cmdline.split()[5])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        k3.addWidget(self.value)
        
        k4=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Direction"))
        l.setStyleSheet("font-size: 20px;")
        k4.addWidget(l)
        
        self.direction=QComboBox()
        self.direction.setStyleSheet("font-size: 20px;")
        self.direction.addItems([QCoreApplication.translate("ecl","right"),QCoreApplication.translate("ecl","left"),QCoreApplication.translate("ecl","stop")])
        if self.cmdline.split()[4][:1]=="r": self.direction.setCurrentIndex(0)
        elif self.cmdline.split()[4][:1]=="l": self.direction.setCurrentIndex(1)
        elif self.cmdline.split()[4][:1]=="s": self.direction.setCurrentIndex(2)
        k4.addWidget(self.direction)
        
        k9=QHBoxLayout()
        k9.addLayout(k3)
        k9.addStretch()
        k9.addLayout(k4)
        
        self.layout.addLayout(k9)
    
        self.layout.addStretch()
        
        k5=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "End Sw."))
        l.setStyleSheet("font-size: 20px;")
        
        k5.addWidget(l)
        
        self.endSw=QComboBox()
        self.endSw.setStyleSheet("font-size: 20px;")
        self.endSw.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
        self.endSw.setCurrentIndex(int(self.cmdline.split()[3])-1)

        k5.addWidget(self.endSw)
        
        #self.layout.addStretch()

        self.layout.addLayout(k5)
        self.layout.addStretch()
        
        k13=QHBoxLayout()
        
        k11=QLabel("Pulses")
        k11.setStyleSheet("font-size: 20px;")
        
        k13.addWidget(k11)
        k13.addStretch()
        
        self.pulses=QLineEdit(self.cmdline.split()[6])
        self.pulses.setReadOnly(True)
        self.pulses.setStyleSheet("font-size: 20px;")
        self.pulses.mousePressEvent=self.plsPress
        self.pulses.mouseReleaseEvent=self.plsRelease
        k13.addWidget(self.pulses)
        
        self.layout.addLayout(k13)
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="MotorE " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " "
        self.cmdline=self.cmdline + self.endSw.currentText()[2:] + " "
        
        if self.direction.currentIndex()==0: d="r"
        elif self.direction.currentIndex()==1: d="l"
        elif self.direction.currentIndex()==2:
            d="s"
            self.value.setText("0")
            
        self.cmdline=self.cmdline + d + " " + self.value.text()
        self.cmdline=self.cmdline + " " + self.pulses.text()
        self.close()
    
    def ifChanged(self):
        self.valueChanged()
        
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btn=1
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        if self.btn==1: self.value.setText(queryVarName(self.variables,self.value.text()))  
        else:           self.pulses.setText(queryVarName(self.variables,self.pulses.text())) 
            
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Value"),a,self).exec_()
        try:
            self.value.setText(str(int(t)))
        except:
            self.value.setText(a)
            
        self.valueChanged()
        
    def valueChanged(self):
        try:            
            if self.interface.currentIndex()==0: self.value.setText(str(max(0,min(7,int(self.value.text())))))
            else: self.value.setText(str(max(0,min(512,int(self.value.text())))))
        except:
            pass
        
    def plsPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.btn=2
        self.timer.start(500)
     
    def plsRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.pulses.text())
            except:
                self.pulses.setText("0")  
            self.getPulses(1)
            
    def getPulses(self,m):
        a=self.pulses.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Pulses"),a,self).exec_()
        try:
            if int(t)<0: t=str(0)
            if int(t)>9999: t=str(9999)
            t=str(int(t))
        except:
            t=a
        self.pulses.setText(t) 

class editMotorEncoderSync(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","MotorES"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["TXT"])

        self.interface.currentIndexChanged.connect(self.ifChanged)
        k1.addWidget(self.interface)
        
        #self.layout.addStretch()
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)
        
        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItems(["M 1","M 2","M 3","M 4"])

        self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        k2.addWidget(self.port)
        
        k8=QHBoxLayout()
        k8.addLayout(k1)
        k8.addStretch()
        k8.addLayout(k2)
        
        self.layout.addLayout(k8)        
        
        k3=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Value"))
        l.setStyleSheet("font-size: 20px;")
        k3.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        self.value.setText(self.cmdline.split()[5])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        k3.addWidget(self.value)
        
        k4=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Direction"))
        l.setStyleSheet("font-size: 20px;")
        k4.addWidget(l)
        
        self.direction=QComboBox()
        self.direction.setStyleSheet("font-size: 20px;")
        self.direction.addItems([QCoreApplication.translate("ecl","right"),QCoreApplication.translate("ecl","left"),QCoreApplication.translate("ecl","stop")])
        if self.cmdline.split()[4][:1]=="r": self.direction.setCurrentIndex(0)
        elif self.cmdline.split()[4][:1]=="l": self.direction.setCurrentIndex(1)
        elif self.cmdline.split()[4][:1]=="s": self.direction.setCurrentIndex(2)
        k4.addWidget(self.direction)
        
        k9=QHBoxLayout()
        k9.addLayout(k3)
        k9.addStretch()
        k9.addLayout(k4)
        
        self.layout.addLayout(k9)
    
        self.layout.addStretch()
        
        k5=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Sync to"))
        l.setStyleSheet("font-size: 20px;")
        
        k5.addWidget(l)
        
        self.syncTo=QComboBox()
        self.syncTo.setStyleSheet("font-size: 20px;")
        self.syncTo.addItems(["M 1","M 2","M 3","M 4"])
        self.syncTo.setCurrentIndex(int(self.cmdline.split()[3])-1)

        k5.addWidget(self.syncTo)
        
        #self.layout.addStretch()

        self.layout.addLayout(k5)
        self.layout.addStretch()
        
        k13=QHBoxLayout()
        
        k11=QLabel("Pulses")
        k11.setStyleSheet("font-size: 20px;")
        
        k13.addWidget(k11)
        k13.addStretch()
        
        self.pulses=QLineEdit(self.cmdline.split()[6])
        self.pulses.setReadOnly(True)
        self.pulses.setStyleSheet("font-size: 20px;")
        self.pulses.mousePressEvent=self.plsPress
        self.pulses.mouseReleaseEvent=self.plsRelease
        k13.addWidget(self.pulses)
        
        self.layout.addLayout(k13)
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="MotorES " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " "
        self.cmdline=self.cmdline + self.syncTo.currentText()[2:] + " "
        
        if self.direction.currentIndex()==0: d="r"
        elif self.direction.currentIndex()==1: d="l"
        elif self.direction.currentIndex()==2:
            d="s"
            self.value.setText("0")
            self.pulses.setText("0")
            
        self.cmdline=self.cmdline + d + " " + self.value.text()
        self.cmdline=self.cmdline + " " + self.pulses.text()
        self.close()
    
    def ifChanged(self):
        self.valueChanged()
        
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btn=1
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        if self.btn==1: self.value.setText(queryVarName(self.variables,self.value.text()))  
        else:           self.pulses.setText(queryVarName(self.variables,self.pulses.text())) 
            
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Value"),a,self).exec_()
        try:
            self.value.setText(str(int(t)))
        except:
            self.value.setText(a)
            
        self.valueChanged()
        
    def valueChanged(self):
        try:            
            if self.interface.currentIndex()==0: self.value.setText(str(max(0,min(7,int(self.value.text())))))
            else: self.value.setText(str(max(0,min(512,int(self.value.text())))))
        except:
            pass
        
    def plsPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.btn=2
        self.timer.start(500)
     
    def plsRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.pulses.text())
            except:
                self.pulses.setText("0")  
            self.getPulses(1)
            
    def getPulses(self,m):
        a=self.pulses.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Pulses"),a,self).exec_()
        try:
            if int(t)<0: t=str(0)
            if int(t)>9999: t=str(9999)
            t=str(int(t))
        except:
            t=a
        self.pulses.setText(t)
              
class editLoopTo(TouchDialog):
    def __init__(self, cmdline, taglist, vari, parent):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","LoopTo"), parent)
        
        self.cmdline=cmdline
        self.taglist=taglist
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        

        l=QLabel(QCoreApplication.translate("ecl", "Loop target"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)
        
        self.tags=QListWidget()
        self.tags.setStyleSheet("font-size: 20px;")
        self.tags.addItems(self.taglist)
        try:
            t=0
            for tag in self.taglist:
               if self.taglist[t]==self.cmdline.split()[1]: self.tags.setCurrentRow(t)
               t=t+1
        except:
            self.tags.setCurrentRow(0)
            
        self.layout.addWidget(self.tags)
        
        self.layout.addStretch()

        l=QLabel(QCoreApplication.translate("ecl", "Count"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        self.value.setText(self.cmdline.split()[2])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        self.layout.addWidget(self.value)
        
        self.layout.addStretch()
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="LoopTo " +self.tags.item(self.tags.currentRow()).text()+ " " + self.value.text()
        self.close()
        
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        self.value.setText(queryVarName(self.variables,self.value.text()))  
    
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Number"),a,None).exec_()
        try:
            t=str(max(min(int(t),99999),1))
        except:
            t=a
        self.value.setText(t)

class editCall(TouchDialog):
    def __init__(self, cmdline, taglist, vari, parent):
        TouchDialog.__init__(self, cmdline.split()[0], parent)
        
        self.command=cmdline.split()[0]
        self.cmdline=cmdline
        self.taglist=taglist
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
    
        self.titlebar.setCancelButton()
        
        self.layout=QVBoxLayout()
        

        l=QLabel(QCoreApplication.translate("ecl", "Module"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)
        
        self.tags=QListWidget()
        self.tags.setStyleSheet("font-size: 20px;")
        self.tags.addItems(self.taglist)
        self.tags.setCurrentRow(0)
        try:
            t=0
            for tag in self.taglist:
               if self.taglist[t]==self.cmdline.split()[1]: self.tags.setCurrentRow(t)
               t=t+1
        except:
            pass
            
        self.layout.addWidget(self.tags)
        
        self.layout.addStretch()

        l=QLabel(QCoreApplication.translate("ecl", "Count"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)
        
        if len(self.cmdline.split())<3: self.cmdline=self.cmdline+" 1"
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        self.value.setText(self.cmdline.split()[2])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        self.layout.addWidget(self.value)
        
        self.layout.addStretch()
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline=self.command + " " +self.tags.item(self.tags.currentRow()).text()+ " " + self.value.text()
        self.close()
        
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        self.value.setText(queryVarName(self.variables,self.value.text()))  
    
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Number"),a,None).exec_()
        try:
            t=str(max(min(int(t),99999),0))
        except:
            t=a
        self.value.setText(t)
        
class editQueryIn(TouchDialog):
    def __init__(self, cmdline, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","QueryIn"), parent)
        
        self.cmdline=cmdline
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["RIF","TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(1)
        elif self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(2)
        
        self.interface.activated.connect(self.ifChanged)
        k1.addWidget(self.interface)
        
        #self.layout.addStretch()
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)

        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItem("d")
        
        k2.addWidget(self.port)
        
        k8=QHBoxLayout()
        k8.addLayout(k1)
        #k8.addStretch()
        k8.addLayout(k2)
        
        self.layout.addLayout(k8)        
        
        
        k4=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Inp. type"))
        l.setStyleSheet("font-size: 20px;")
        k4.addWidget(l)
        
        self.iType=QComboBox()
        self.iType.setStyleSheet("font-size: 20px;")
            
        self.iType.activated.connect(self.ifChanged)

        k4.addWidget(self.iType)
                
        k3=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Text"))
        l.setStyleSheet("font-size: 20px;")
        k3.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        tx=""
        for a in range(4,len(self.cmdline.split())):
            tx=tx+(self.cmdline.split()[a])+" "
        tx=tx[:-1]
            
        self.value.setText(tx)
        self.value.mousePressEvent=self.getValue
        k3.addWidget(self.value)
        
        k9=QVBoxLayout()
        k9.addLayout(k4)
        k9.addStretch()
        k9.addLayout(k3)
        
        self.layout.addLayout(k9)
        
        
        self.layout.addStretch()                
        
        self.centralWidget.setLayout(self.layout)
        
        self.ifChanged()
        
        p=self.cmdline.split()[2]
        if p=="X":self.port.setCurrentIndex(0)
        elif p=="Y":self.port.setCurrentIndex(1)
        else: self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        
        if self.cmdline.split()[3][:1]=="S": self.iType.setCurrentIndex(0)
        elif self.cmdline.split()[3][:1]=="V": self.iType.setCurrentIndex(1)
        elif self.cmdline.split()[3][:1]=="R": self.iType.setCurrentIndex(2)
        elif self.cmdline.split()[3][:1]=="D": self.iType.setCurrentIndex(3)
        elif self.cmdline.split()[3][:1]=="C": self.iType.setCurrentIndex(4)
        
        self.ifChanged()
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="QueryIn " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " "
        d="S"
        if self.iType.currentIndex()==0: d="S"
        elif self.iType.currentIndex()==1: d="V"
        elif self.iType.currentIndex()==2: d="R"
        elif self.iType.currentIndex()==3: d="D"               
        elif self.iType.currentIndex()==4: d="C"
        self.cmdline=self.cmdline + d + " " + self.value.text()
        self.close()
    
    def ifChanged(self):
        m=max(self.iType.currentIndex(),0)
        self.iType.clear()
        if self.interface.currentIndex()==0:
            self.iType.addItems([QCoreApplication.translate("ecl","switch"),
                                QCoreApplication.translate("ecl","voltage"),
                                QCoreApplication.translate("ecl","resistance"),
                                QCoreApplication.translate("ecl","distance")])
        else:
            self.iType.addItems([QCoreApplication.translate("ecl","switch"),
                                QCoreApplication.translate("ecl","voltage"),
                                QCoreApplication.translate("ecl","resistance"),
                                QCoreApplication.translate("ecl","distance"),
                                QCoreApplication.translate("ecl","counter")])
        self.iType.setCurrentIndex(m)

        m=self.port.currentIndex()
        self.port.clear()
        if self.interface.currentText()=="RIF":
            if self.iType.currentIndex()==0:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==1:
                self.port.addItems(["A 1","A 2"])
            elif self.iType.currentIndex()==2:
                self.port.addItems(["A X","A Y"])
            elif self.iType.currentIndex()==3:
                self.port.addItems(["D 1","D 2"])
        elif self.interface.currentText()=="TXT":
            if self.iType.currentIndex()>=0 and self.iType.currentIndex()<=3:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==4:
                self.port.addItems(["C 1","C 2","C 3","C 4"]) 
        elif self.interface.currentText()=="FTD":
            if self.iType.currentIndex()>=0 and self.iType.currentIndex()<=2:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==3:
                self.port.addItems(["C 1"]) 
            elif self.iType.currentIndex()==4:
                self.port.addItems(["C 1","C 2","C 3","C 4"]) 
        self.port.setCurrentIndex(min(max(0,m),self.port.count()-1))
        
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Value"),a,self).exec_()
        self.value.setText(t)

class editIfInput(TouchDialog):
    def __init__(self, cmdline, taglist, varlist, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","IfInput"), parent)
        
        self.cmdline=cmdline
        self.taglist=taglist
        self.variables=varlist
        self.parent=parent
        
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        # Aussenrahmen
        self.layout=QVBoxLayout()
        
        # VBox
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 18px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 18px;")
        self.interface.addItems(["RIF","TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(1)
        elif self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(2)
        
        self.interface.activated.connect(self.ifChanged)
        k1.addWidget(self.interface)
        
        self.layout.addStretch()
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 18px;")
        k2.addWidget(l)

        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 18px;")
        self.port.addItem("d")
        
        k2.addWidget(self.port)
        
        k8=QHBoxLayout()
        k8.addLayout(k1)
        #k8.addStretch()
        k8.addLayout(k2)
        
        self.layout.addLayout(k8)        
        
        
        k4=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Inp. type"))
        l.setStyleSheet("font-size: 18px;")
        k4.addWidget(l)
        
        self.iType=QComboBox()
        self.iType.setStyleSheet("font-size: 18px;")
            
        self.iType.activated.connect(self.ifChanged)

        k4.addWidget(self.iType)
                
        k5=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Operator"))
        l.setStyleSheet("font-size: 18px;")
        k5.addWidget(l)
        
        self.operator=QComboBox()
        self.operator.setStyleSheet("font-size: 18px;")
        self.operator.addItems(["  <", " <=", " ==", " !=", " >=", "  >"])

        x=self.cmdline.split()[4]
        
        if x=="<":    self.operator.setCurrentIndex(0)
        elif x=="<=": self.operator.setCurrentIndex(1)
        elif x=="==": self.operator.setCurrentIndex(2)
        elif x=="!=": self.operator.setCurrentIndex(3)
        elif x==">=": self.operator.setCurrentIndex(4)
        elif x==">":  self.operator.setCurrentIndex(5)
        
        k5.addWidget(self.operator)

        k9=QHBoxLayout()
        k9.addLayout(k4)
        k9.addStretch()
        k9.addLayout(k5)
        
        self.layout.addLayout(k9)
        
        
        k3=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Value"))
        l.setStyleSheet("font-size: 18px;")
        k3.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 18px;")
            
        self.value.setText(self.cmdline.split()[5])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        k3.addWidget(self.value)
        
        self.layout.addLayout(k3)
        self.layout.addStretch()
        
        
        kb=QVBoxLayout()
        
        l=QLabel(QCoreApplication.translate("ecl","Target"))
        l.setStyleSheet("font-size: 18px;")
        kb.addWidget(l)
        
        self.tags=QComboBox()
        self.tags.setStyleSheet("font-size: 18px;")
        self.tags.addItems(self.taglist)
        self.tags.setCurrentIndex(0)
        if len(self.cmdline.split())>6:
            cc=0
            for i in self.taglist:
                if self.cmdline.split()[6]==i: self.tags.setCurrentIndex(cc)
                cc=cc+1
        

        
        kb.addWidget(self.tags)
        
        self.layout.addLayout(kb)
        self.layout.addStretch()                
        
        self.centralWidget.setLayout(self.layout)
        
        self.ifChanged()
        
        p=self.cmdline.split()[2]
        if p=="X":self.port.setCurrentIndex(0)
        elif p=="Y":self.port.setCurrentIndex(1)
        else: self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        
        if self.cmdline.split()[3][:1]=="S": self.iType.setCurrentIndex(0)
        elif self.cmdline.split()[3][:1]=="V": self.iType.setCurrentIndex(1)
        elif self.cmdline.split()[3][:1]=="R": self.iType.setCurrentIndex(2)
        elif self.cmdline.split()[3][:1]=="D": self.iType.setCurrentIndex(3)
        elif self.cmdline.split()[3][:1]=="C": self.iType.setCurrentIndex(4)
        
        self.ifChanged()
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        self.value.setText(queryVarName(self.variables,self.value.text()))  
    
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
        
    def on_confirm(self):
        self.cmdline="IfIn " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " "
        if self.iType.currentIndex()==0:   d="S"
        elif self.iType.currentIndex()==1: d="V"
        elif self.iType.currentIndex()==2: d="R"
        elif self.iType.currentIndex()==3: d="D"               
        elif self.iType.currentIndex()==4: d="C"
        
        self.cmdline=self.cmdline + d + " " + self.operator.itemText(self.operator.currentIndex()).strip()
        self.cmdline=self.cmdline + " " + self.value.text()
        self.cmdline=self.cmdline + " " + self.tags.itemText(self.tags.currentIndex())
        
        self.close()
    
    def ifChanged(self):
        m=max(self.iType.currentIndex(),0)
        self.iType.clear()
        if self.interface.currentIndex()==0:
            self.iType.addItems([QCoreApplication.translate("ecl","switch"),
                                QCoreApplication.translate("ecl","voltage"),
                                QCoreApplication.translate("ecl","resistance"),
                                QCoreApplication.translate("ecl","distance")])
        else:
            self.iType.addItems([QCoreApplication.translate("ecl","switch"),
                                QCoreApplication.translate("ecl","voltage"),
                                QCoreApplication.translate("ecl","resistance"),
                                QCoreApplication.translate("ecl","distance"),
                                QCoreApplication.translate("ecl","counter")])
        self.iType.setCurrentIndex(m)

        m=self.port.currentIndex()
        self.port.clear()
        if self.interface.currentText()=="RIF":
            if self.iType.currentIndex()==0:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==1:
                self.port.addItems(["A 1","A 2"])
            elif self.iType.currentIndex()==2:
                self.port.addItems(["A X","A Y"])
            elif self.iType.currentIndex()==3:
                self.port.addItems(["D 1","D 2"])
        elif self.interface.currentText()=="TXT":
            if self.iType.currentIndex()>=0 and self.iType.currentIndex()<=3:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==4:
                self.port.addItems(["C 1","C 2","C 3","C 4"]) 
        elif self.interface.currentText()=="FTD":
            if self.iType.currentIndex()>=0 and self.iType.currentIndex()<=2:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==3:
                self.port.addItems(["C 1"]) 
            elif self.iType.currentIndex()==4:
                self.port.addItems(["C 1","C 2","C 3","C 4"]) 
        self.port.setCurrentIndex(min(max(0,m),self.port.count()-1))
        
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Value"),a,self).exec_()
        try:
            int(t)
        except:
            t=a
        self.value.setText(str(int(t)))
    
class editWaitForInput(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","WaitIn"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
        
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        # Aussenrahmen
        self.layout=QVBoxLayout()
        
        # VBox
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 18px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 18px;")
        self.interface.addItems(["RIF","TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(1)
        elif self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(2)
        
        self.interface.activated.connect(self.ifChanged)
        k1.addWidget(self.interface)
        
        self.layout.addStretch()
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 18px;")
        k2.addWidget(l)

        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 18px;")
        self.port.addItem("d")
        
        k2.addWidget(self.port)
        
        k8=QHBoxLayout()
        k8.addLayout(k1)
        #k8.addStretch()
        k8.addLayout(k2)
        
        self.layout.addLayout(k8)        
        
        
        k4=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Inp. type"))
        l.setStyleSheet("font-size: 18px;")
        k4.addWidget(l)
        
        self.iType=QComboBox()
        self.iType.setStyleSheet("font-size: 18px;")
            
        self.iType.activated.connect(self.ifChanged)

        k4.addWidget(self.iType)
                
        k5=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Operator"))
        l.setStyleSheet("font-size: 18px;")
        k5.addWidget(l)
        
        self.operator=QComboBox()
        self.operator.setStyleSheet("font-size: 18px;")
        self.operator.addItems(["  <"," <=", " ==", " !=", " >=", "  >"])

        x=self.cmdline.split()[4]
        
        if x=="<":    self.operator.setCurrentIndex(0)
        elif x=="<=": self.operator.setCurrentIndex(1)
        elif x=="==": self.operator.setCurrentIndex(2)
        elif x=="!=": self.operator.setCurrentIndex(3)
        elif x==">=": self.operator.setCurrentIndex(4)
        elif x==">":  self.operator.setCurrentIndex(5)
        
        k5.addWidget(self.operator)

        k9=QHBoxLayout()
        k9.addLayout(k4)
        k9.addStretch()
        k9.addLayout(k5)
        
        self.layout.addLayout(k9)
        
        
        k3=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Value"))
        l.setStyleSheet("font-size: 18px;")
        k3.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 18px;")
            
        self.value.setText(self.cmdline.split()[5])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        
        k3.addWidget(self.value)
        
        self.layout.addLayout(k3)
        self.layout.addStretch()
        
        
        kb=QVBoxLayout()
        
        l=QLabel(QCoreApplication.translate("ecl","Timeout"))
        l.setStyleSheet("font-size: 18px;")
        kb.addWidget(l)
        
        self.timeout=QLineEdit()
        self.timeout.setReadOnly(True)
        self.timeout.setStyleSheet("font-size: 18px;")
        self.timeout.setText(self.cmdline.split()[6])
        self.timeout.mousePressEvent=self.tvalPress
        self.timeout.mouseReleaseEvent=self.tvalRelease
        
        kb.addWidget(self.timeout)
        
        self.layout.addLayout(kb)
        self.layout.addStretch()                
        
        self.centralWidget.setLayout(self.layout)
        
        self.ifChanged()
        
        p=self.cmdline.split()[2]
        if p=="X":self.port.setCurrentIndex(0)
        elif p=="Y":self.port.setCurrentIndex(1)
        else: self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        
        if self.cmdline.split()[3][:1]=="S": self.iType.setCurrentIndex(0)
        elif self.cmdline.split()[3][:1]=="V": self.iType.setCurrentIndex(1)
        elif self.cmdline.split()[3][:1]=="R": self.iType.setCurrentIndex(2)
        elif self.cmdline.split()[3][:1]=="D": self.iType.setCurrentIndex(3)
        elif self.cmdline.split()[3][:1]=="C": self.iType.setCurrentIndex(4)
        
        self.ifChanged()
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="WaitIn " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " "
        if self.iType.currentIndex()==0:   d="S"
        elif self.iType.currentIndex()==1: d="V"
        elif self.iType.currentIndex()==2: d="R"
        elif self.iType.currentIndex()==3: d="D"               
        elif self.iType.currentIndex()==4: d="C"
        
        self.cmdline=self.cmdline + d + " " + self.operator.itemText(self.operator.currentIndex()).strip()
        self.cmdline=self.cmdline + " " + self.value.text()
        self.cmdline=self.cmdline + " " + self.timeout.text()
        
        self.close()
    
    def ifChanged(self):
        m=max(self.iType.currentIndex(),0)
        self.iType.clear()
        if self.interface.currentIndex()==0:
            self.iType.addItems([QCoreApplication.translate("ecl","switch"),
                                QCoreApplication.translate("ecl","voltage"),
                                QCoreApplication.translate("ecl","resistance"),
                                QCoreApplication.translate("ecl","distance")])
        else:
            self.iType.addItems([QCoreApplication.translate("ecl","switch"),
                                QCoreApplication.translate("ecl","voltage"),
                                QCoreApplication.translate("ecl","resistance"),
                                QCoreApplication.translate("ecl","distance"),
                                QCoreApplication.translate("ecl","counter")])
        self.iType.setCurrentIndex(m)

        m=self.port.currentIndex()
        self.port.clear()
        if self.interface.currentText()=="RIF":
            if self.iType.currentIndex()==0:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==1:
                self.port.addItems(["A 1","A 2"])
            elif self.iType.currentIndex()==2:
                self.port.addItems(["A X","A Y"])
            elif self.iType.currentIndex()==3:
                self.port.addItems(["D 1","D 2"])
        elif self.interface.currentText()=="TXT":
            if self.iType.currentIndex()>=0 and self.iType.currentIndex()<=3:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==4:
                self.port.addItems(["C 1","C 2","C 3","C 4"]) 
        elif self.interface.currentText()=="FTD":
            if self.iType.currentIndex()>=0 and self.iType.currentIndex()<=2:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==3:
                self.port.addItems(["C 1"]) 
            elif self.iType.currentIndex()==4:
                self.port.addItems(["C 1","C 2","C 3","C 4"]) 
        self.port.setCurrentIndex(min(max(0,m),self.port.count()-1))
        
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btn=1
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        if self.btn==1:
            self.value.setText(queryVarName(self.variables,self.value.text()))  
        else:
            self.timeout.setText(queryVarName(self.variables,self.timeout.text())) 
    
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Number"),a,None).exec_()
        try:
            t=str(max(min(int(t),99999),0))
        except:
            t=a
        self.value.setText(t)
        
    def tvalPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btn=2
        self.btnTimedOut=False
        self.timer.start(500)
    
    def tvalRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.timeout.text())
            except:
                self.timeout.setText("0")  
            self.getTValue(1)

    def getTValue(self,m):
        a=self.timeout.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Timeout"),a,self).exec_()
        try:
            t=str(max(min(int(t),99999),0))
        except:
            t=a
        self.timeout.setText(t)

class editIfTimer(TouchDialog):
    def __init__(self, cmdline, taglist, vari, parent):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","IfTimer"), parent)
        
        self.cmdline=cmdline
        self.taglist=taglist
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        l=QLabel(QCoreApplication.translate("ecl", "Operator"))
        l.setStyleSheet("font-size: 20px;")
        
        self.layout.addWidget(l)
        
        self.operator=QComboBox()
        self.operator.setStyleSheet("font-size: 20px;")
        self.operator.addItems(["  <  ","  >  "])

        if self.cmdline.split()[1]=="<": self.operator.setCurrentIndex(0)
        if self.cmdline.split()[1]==">": self.operator.setCurrentIndex(1)

        self.layout.addWidget(self.operator)
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl","Value"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)     
        
        self.thd=QLineEdit()
        self.thd.setReadOnly(True)
        self.thd.setStyleSheet("font-size: 20px;")
        self.thd.setText(self.cmdline.split()[2])
        self.thd.mousePressEvent=self.valPress
        self.thd.mouseReleaseEvent=self.valRelease
        self.layout.addWidget(self.thd)
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl","Target"))
        l.setStyleSheet("font-size: 20px;")
        self.layout.addWidget(l)
        
        self.tags=QComboBox()
        self.tags.setStyleSheet("font-size: 20px;")
        self.tags.addItems(self.taglist)

        self.tags.setCurrentIndex(0)
        if len(self.cmdline.split())>3:
            cc=0
            for i in self.taglist:
                if self.cmdline.split()[3]==i: self.tags.setCurrentIndex(cc)
                cc=cc+1

        self.layout.addWidget(self.tags)
        self.layout.addStretch() 
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="IfTimer " +self.operator.currentText().strip()+ " " + self.thd.text() + " " + self.tags.itemText(self.tags.currentIndex())
        self.close()
        
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        self.thd.setText(queryVarName(self.variables,self.thd.text()))  
    
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.thd.text())
            except:
                self.thd.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.thd.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Timeout"),a,None).exec_()
        try:
            t=str(max(min(int(t),99999),0))
        except:
            t=a
        self.thd.setText(t)

class editInterrupt(TouchDialog):
    def __init__(self, cmdline, modlist, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","Interrupt"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
        self.modlist=modlist
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.layout=QVBoxLayout()
        
        l=QLabel(QCoreApplication.translate("ecl", "Interrupt"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.interrupt=QComboBox()
        self.interrupt.setStyleSheet("font-size: 18px;")
            
        oplist=["After","Every","Off"]
        self.interrupt.addItems(oplist)
        
        if self.cmdline.split()[1] in oplist:
            self.interrupt.setCurrentIndex(oplist.index(self.cmdline.split()[1]))
        else:
            self.interrupt.setCurrentIndex(0)
        
        self.layout.addWidget(self.interrupt)
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Time"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 18px;")
            
        try:
            self.value.setText(self.cmdline.split()[2])
        except:
            self.value.setText("500")
            
        self.value.mousePressEvent=self.getValue
        self.layout.addWidget(self.value)        
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Target module"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.target=QComboBox()
        self.target.setStyleSheet("font-size: 18px;")
        self.target.addItems(self.modlist)

        try:
            self.target.setCurrentIndex(self.modlist.index(self.cmdline.split()[3]))
        except:
            self.target.setCurrentIndex(0)

        self.layout.addWidget(self.target)
        
        self.layout.addStretch()

        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="Interrupt " + self.interrupt.itemText(self.interrupt.currentIndex())
        if not "Off" in self.cmdline:
            self.cmdline=self.cmdline + " " + self.value.text() + " "
            self.cmdline=self.cmdline + self.target.itemText(self.target.currentIndex())
        self.close()
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Time"),a,self).exec_()
        try:
            v=str(max(min(int(t),99999),0))
            self.value.setText(v)
        except:
            self.value.setText(a)

class editInit(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","Variable"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
        self.parent=parent
        
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        k3=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Variable name"))
        l.setStyleSheet("font-size: 20px;")
        k3.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")
        self.value.setText(self.cmdline.split()[1])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        k3.addWidget(self.value)
                
        self.layout.addLayout(k3)
    
        self.layout.addStretch()
        
        k13=QVBoxLayout()
        
        k11=QLabel("Init value")
        k11.setStyleSheet("font-size: 20px;")
        
        k13.addWidget(k11)
        k13.addStretch()
        
        self.pulses=QLineEdit(self.cmdline.split()[2])
        self.pulses.setReadOnly(True)
        self.pulses.setStyleSheet("font-size: 20px;")
        self.pulses.mousePressEvent=self.plsPress
        self.pulses.mouseReleaseEvent=self.plsRelease
        k13.addWidget(self.pulses)
        
        self.layout.addLayout(k13)
        
        self.layout.addStretch()
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="Init "
        self.cmdline=self.cmdline + self.value.text()
        self.cmdline=self.cmdline + " " + self.pulses.text()
        self.close()
    
    def ifChanged(self):
        pass
    
    def valPress(self,sender):
        #self.value.setText(queryVarName(self.variables,self.value.text()))
        
        if self.timer.isActive(): self.timer.stop()
        self.btn=1
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        if self.btn==1: self.value.setText(queryVarName(self.variables,self.value.text()))  
        else:           self.pulses.setText(queryVarName(self.variables,self.pulses.text())) 
            
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Name"),a,self.parent).exec_()
        if t[0] in "0123456789": t="i"+t
        self.value.setText(t)
        
    def plsPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.btn=2
        self.timer.start(500)
     
    def plsRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.pulses.text())
            except:
                self.pulses.setText("0")  
            self.getPulses(1)
            
    def getPulses(self,m):
        a=self.pulses.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Value"),a,self.parent).exec_()
        try:
            if int(t)<0: t=str(0)
            if int(t)>9999: t=str(9999)
            t=str(int(t))
        except:
            t=a
        self.pulses.setText(t)

class editFromIn(TouchDialog):
    def __init__(self, cmdline, varlist, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","FromIn"), parent)
        
        self.cmdline=cmdline
        self.varlist=varlist
        self.parent=parent
        
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.layout=QVBoxLayout()
        
        k1=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Device"))
        l.setStyleSheet("font-size: 20px;")
        
        k1.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 20px;")
        self.interface.addItems(["RIF","TXT","FTD"])

        if self.cmdline.split()[1]=="TXT": self.interface.setCurrentIndex(1)
        elif self.cmdline.split()[1]=="FTD": self.interface.setCurrentIndex(2)
        
        self.interface.activated.connect(self.ifChanged)
        k1.addWidget(self.interface)
        
        #self.layout.addStretch()
        
        k2=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Port"))
        l.setStyleSheet("font-size: 20px;")
        k2.addWidget(l)

        self.port=QComboBox()
        self.port.setStyleSheet("font-size: 20px;")
        self.port.addItem("d")
        
        k2.addWidget(self.port)
        
        k8=QHBoxLayout()
        k8.addLayout(k1)
        #k8.addStretch()
        k8.addLayout(k2)
        
        self.layout.addLayout(k8)        
        
        
        k4=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Inp. type"))
        l.setStyleSheet("font-size: 20px;")
        k4.addWidget(l)
        
        self.iType=QComboBox()
        self.iType.setStyleSheet("font-size: 20px;")
            
        self.iType.activated.connect(self.ifChanged)

        k4.addWidget(self.iType)
                
        k3=QVBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl","Variable"))
        l.setStyleSheet("font-size: 20px;")
        k3.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 20px;")

        self.value.setText(self.cmdline.split()[4])
        self.value.mousePressEvent=self.getValue
        k3.addWidget(self.value)
        
        k9=QVBoxLayout()
        k9.addLayout(k4)
        k9.addStretch()
        k9.addLayout(k3)
        
        self.layout.addLayout(k9)
        
        
        self.layout.addStretch()                
        
        self.centralWidget.setLayout(self.layout)
        
        self.ifChanged()
        
        p=self.cmdline.split()[2]
        if p=="X":self.port.setCurrentIndex(0)
        elif p=="Y":self.port.setCurrentIndex(1)
        else: self.port.setCurrentIndex(int(self.cmdline.split()[2])-1)
        
        if self.cmdline.split()[3][:1]=="S": self.iType.setCurrentIndex(0)
        elif self.cmdline.split()[3][:1]=="V": self.iType.setCurrentIndex(1)
        elif self.cmdline.split()[3][:1]=="R": self.iType.setCurrentIndex(2)
        elif self.cmdline.split()[3][:1]=="D": self.iType.setCurrentIndex(3)
        elif self.cmdline.split()[3][:1]=="C": self.iType.setCurrentIndex(4)
        
        self.ifChanged()
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="FromIn " +self.interface.currentText()+ " " + self.port.currentText()[2:] + " "
        d="S"
        if self.iType.currentIndex()==0: d="S"
        elif self.iType.currentIndex()==1: d="V"
        elif self.iType.currentIndex()==2: d="R"
        elif self.iType.currentIndex()==3: d="D"               
        elif self.iType.currentIndex()==4: d="C"
        self.cmdline=self.cmdline + d + " " + self.value.text()
        self.close()
    
    def ifChanged(self):
        m=max(self.iType.currentIndex(),0)
        self.iType.clear()
        if self.interface.currentIndex()==0:
            self.iType.addItems([QCoreApplication.translate("ecl","switch"),
                                QCoreApplication.translate("ecl","voltage"),
                                QCoreApplication.translate("ecl","resistance"),
                                QCoreApplication.translate("ecl","distance")])
        else:
            self.iType.addItems([QCoreApplication.translate("ecl","switch"),
                                QCoreApplication.translate("ecl","voltage"),
                                QCoreApplication.translate("ecl","resistance"),
                                QCoreApplication.translate("ecl","distance"),
                                QCoreApplication.translate("ecl","counter")])
        self.iType.setCurrentIndex(m)

        m=self.port.currentIndex()
        self.port.clear()
        if self.interface.currentText()=="RIF":
            if self.iType.currentIndex()==0:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==1:
                self.port.addItems(["A 1","A 2"])
            elif self.iType.currentIndex()==2:
                self.port.addItems(["A X","A Y"])
            elif self.iType.currentIndex()==3:
                self.port.addItems(["D 1","D 2"])
        elif self.interface.currentText()=="TXT":
            if self.iType.currentIndex()>=0 and self.iType.currentIndex()<=3:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==4:
                self.port.addItems(["C 1","C 2","C 3","C 4"]) 
        elif self.interface.currentText()=="FTD":
            if self.iType.currentIndex()>=0 and self.iType.currentIndex()<=2:
                self.port.addItems(["I 1","I 2","I 3","I 4","I 5","I 6","I 7","I 8"])
            elif self.iType.currentIndex()==3:
                self.port.addItems(["C 1"]) 
            elif self.iType.currentIndex()==4:
                self.port.addItems(["C 1","C 2","C 3","C 4"]) 
        self.port.setCurrentIndex(min(max(0,m),self.port.count()-1))
        
    
    def getValue(self,m):
        a=self.value.text()
        t=queryVarName(self.varlist, a)
        self.value.setText(t)

class editIfVar(TouchDialog):
    def __init__(self, cmdline, taglist, varlist, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","IfVar"), parent)
        
        self.cmdline=cmdline
        self.taglist=taglist
        self.variables=varlist
        
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        # Aussenrahmen
        self.layout=QVBoxLayout()
        
        # VBox
        l=QLabel(QCoreApplication.translate("ecl", "Variable"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.interface=QComboBox()
        self.interface.setStyleSheet("font-size: 18px;")
        self.interface.addItems(self.variables)

        if self.cmdline.split()[1] in self.variables:
            self.interface.setCurrentIndex(self.variables.index(self.cmdline.split()[1]))
        else: self.interface.setCurrentIndex(0)
        
        self.layout.addWidget(self.interface)
        
        self.layout.addStretch()
                
        l=QLabel(QCoreApplication.translate("ecl","Operator"))
        l.setStyleSheet("font-size: 18px;")
        self.layout.addWidget(l)
        
        self.operator=QComboBox()
        self.operator.setStyleSheet("font-size: 18px;")
        self.operator.addItems(["  <", " <=", " ==", " !=", " >=", "  >"])

        x=self.cmdline.split()[2]
        
        if x=="<":    self.operator.setCurrentIndex(0)
        elif x=="<=": self.operator.setCurrentIndex(1)
        elif x=="==": self.operator.setCurrentIndex(2)
        elif x=="!=": self.operator.setCurrentIndex(3)
        elif x==">=": self.operator.setCurrentIndex(4)
        elif x==">":  self.operator.setCurrentIndex(5)
        
        self.layout.addWidget(self.operator)

        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl","Value"))
        l.setStyleSheet("font-size: 18px;")
        self.layout.addWidget(l)     
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 18px;")
            
        self.value.setText(self.cmdline.split()[3])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        self.layout.addWidget(self.value)
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl","Target"))
        l.setStyleSheet("font-size: 18px;")
        self.layout.addWidget(l)
        
        self.tags=QComboBox()
        self.tags.setStyleSheet("font-size: 18px;")
        self.tags.addItems(self.taglist)
        self.tags.setCurrentIndex(0)
        if len(self.cmdline.split())>4:
            cc=0
            for i in self.taglist:
                if self.cmdline.split()[4]==i: self.tags.setCurrentIndex(cc)
                cc=cc+1
        
        self.layout.addWidget(self.tags)
        
        self.layout.addStretch()                
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        self.value.setText(queryVarName(self.variables,self.value.text()))  
    
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
        
    def on_confirm(self):
        self.cmdline="IfVar " +self.interface.currentText() + " " + self.operator.itemText(self.operator.currentIndex()).strip()

        self.cmdline=self.cmdline + " " + self.value.text()
        self.cmdline=self.cmdline + " " + self.tags.itemText(self.tags.currentIndex())
        
        self.close()
    
    def ifChanged(self):
        pass        
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Value"),a,self).exec_()
        try:
            int(t)
        except:
            t=a
        self.value.setText(str(int(t))) 

class editCalc(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","Calc"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        l=QLabel(QCoreApplication.translate("ecl", "First Operand"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 18px;")
            
        self.value.setText(self.cmdline.split()[2])
        
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        self.layout.addWidget(self.value)
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Operator"))
        l.setStyleSheet("font-size: 18px;")
        self.layout.addWidget(l)
        
        self.operator=QComboBox()
        self.operator.setStyleSheet("font-size: 18px;")
        oplist=["+", "-", "*", "/", "div", "digit", "mod", "exp", "root", "min", "max", "sin", "cos", "random", "mean", "&&","||","<","<=","==","!=",">=",">"]
        self.operator.addItems(oplist)
        if self.cmdline.split()[3] in oplist:
            self.operator.setCurrentIndex(oplist.index(self.cmdline.split()[3]))
        else:
            self.operator.setCurrentIndex(0)
        
        self.layout.addWidget(self.operator)
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Second Operand"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.value2=QLineEdit()
        self.value2.setReadOnly(True)
        self.value2.setStyleSheet("font-size: 18px;")
            
        self.value2.setText(self.cmdline.split()[4])
        self.value2.mousePressEvent=self.val2Press
        self.value2.mouseReleaseEvent=self.val2Release
        self.layout.addWidget(self.value2)        
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Target variable"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.target=QComboBox()
        self.target.setStyleSheet("font-size: 18px;")
        self.target.addItems(self.variables)

        if self.cmdline.split()[1] in self.variables:
            self.target.setCurrentIndex(self.variables.index(self.cmdline.split()[1]))
        else:
            self.operator.setCurrentIndex(0)

        self.layout.addWidget(self.target)

        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="Calc " +self.target.itemText(self.target.currentIndex())+ " " + self.value.text() + " "
        self.cmdline=self.cmdline + self.operator.itemText(self.operator.currentIndex()) + " " + self.value2.text()
        
        self.close()
    
    def ifChanged(self):
        self.valueChanged()
    
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btn=1
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        if self.btn==1: self.value.setText(queryVarName(self.variables,self.value.text()))  
        else:           self.value2.setText(queryVarName(self.variables,self.value2.text())) 
            
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","1st Op."),a,self).exec_()
        try:
            self.value.setText(str(int(t)))
        except:
            self.value.setText(a)
        
    def val2Press(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.btn=2
        self.timer.start(500)
     
    def val2Release(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value2.text())
            except:
                self.value2.setText("0")  
            self.getValue2(1)
            
    def getValue2(self,m):
        a=self.value2.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","2nd Op."),a,self).exec_()
        try:
            t=str(int(t))
        except:
            t=a
        self.value2.setText(t)

class editFromPoly(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","FromPoly"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        #
        h=QHBoxLayout()
        l=QLabel("A:")
        l.setStyleSheet("font-size: 18px;")
        
        h.addWidget(l)
        
        self.A=QLineEdit()
        self.A.setReadOnly(True)
        self.A.setStyleSheet("font-size: 18px;")
        self.A.mousePressEvent=self.getA
        
        self.A.setText(self.cmdline.split()[3])
        #self.A.textChanged.connect(self.AChanged)
        
        h.addWidget(self.A)
        self.layout.addLayout(h)
        
        
        h=QHBoxLayout()
        l=QLabel("B:")
        l.setStyleSheet("font-size: 18px;")
        
        h.addWidget(l)
        
        self.B=QLineEdit()
        self.B.setReadOnly(True)
        self.B.setStyleSheet("font-size: 18px;")
        
        self.B.setText(self.cmdline.split()[4])
        #self.B.textChanged.connect(self.BChanged)
        self.B.mousePressEvent=self.getB
        
        h.addWidget(self.B)      
        self.layout.addLayout(h)
        
        h=QHBoxLayout()
        l=QLabel("C:")
        l.setStyleSheet("font-size: 18px;")
        
        h.addWidget(l)
        
        self.C=QLineEdit()
        self.C.setReadOnly(True)
        self.C.setStyleSheet("font-size: 18px;")
        
        self.C.setText(self.cmdline.split()[5])
        #self.C.textChanged.connect(self.CChanged)
        self.C.mousePressEvent=self.getC
        
        h.addWidget(self.C)      
        self.layout.addLayout(h)
        
        h=QHBoxLayout()
        l=QLabel("D:")
        l.setStyleSheet("font-size: 18px;")
        
        h.addWidget(l)
        
        self.D=QLineEdit()
        self.D.setReadOnly(True)
        self.D.setStyleSheet("font-size: 18px;")
        
        self.D.setText(self.cmdline.split()[6])
        #self.D.textChanged.connect(self.DChanged)
        self.D.mousePressEvent=self.getD
        
        h.addWidget(self.D)      
        self.layout.addLayout(h)
        self.layout.addStretch()
    
        
        h=QHBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Input:"))
        l.setStyleSheet("font-size: 18px;")
        
        h.addWidget(l)
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 18px;")
            
        self.value.setText(self.cmdline.split()[2])
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        h.addWidget(self.value)        
        
        self.layout.addLayout(h)
        
        h=QHBoxLayout()
        l=QLabel(QCoreApplication.translate("ecl", "Target:"))
        l.setStyleSheet("font-size: 18px;")
        
        h.addWidget(l)
        
        self.target=QComboBox()
        self.target.setStyleSheet("font-size: 18px;")
        self.target.addItems(self.variables)

        if self.cmdline.split()[1] in self.variables:
            self.target.setCurrentIndex(self.variables.index(self.cmdline.split()[1]))
        else:
            self.target.setCurrentIndex(0)

        h.addWidget(self.target)

        self.layout.addLayout(h)
        
        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def getA(self,b): #AChanged(self):
        a=self.A.text()
        try:
            dummy=TouchAuxKeyboard(QCoreApplication.translate("ecl","A"),a,self).exec_()
            dummy=str(float(dummy))
            self.A.setText(dummy)
        except:
            self.A.setText("0.0")

    def getB(self,b): #AChanged(self):
        a=self.B.text()
        try:
            dummy=TouchAuxKeyboard(QCoreApplication.translate("ecl","B"),a,self).exec_()
            dummy=str(float(dummy))
            self.B.setText(dummy)
        except:
            self.B.setText("0.0")

    def getC(self,b): #AChanged(self):
        a=self.C.text()
        try:
            dummy=TouchAuxKeyboard(QCoreApplication.translate("ecl","C"),a,self).exec_()
            dummy=str(float(dummy))
            self.C.setText(dummy)
        except:
            self.C.setText("0.0")
    
    def getD(self,b): #AChanged(self):
        a=self.D.text()
        try:
            dummy=TouchAuxKeyboard(QCoreApplication.translate("ecl","D"),a,self).exec_()
            dummy=str(float(dummy))
            self.D.setText(dummy)
        except:
            self.D.setText("0.0")


    def on_confirm(self):
        self.cmdline="FromPoly " +self.target.itemText(self.target.currentIndex())
        self.cmdline=self.cmdline + " " + self.value.text()
        self.cmdline=self.cmdline + " " + str(float(self.A.text()))
        self.cmdline=self.cmdline + " " + str(float(self.B.text()))
        self.cmdline=self.cmdline + " " + str(float(self.C.text()))
        self.cmdline=self.cmdline + " " + str(float(self.D.text()))
        self.close()
    
    def ifChanged(self):
        self.valueChanged()
    
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btn=1
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        if self.btn==1: self.value.setText(queryVarName(self.variables,self.value.text()))  
        else:           self.value2.setText(queryVarName(self.variables,self.value2.text())) 
            
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Input"),a,self).exec_()
        try:
            self.value.setText(str(int(t)))
        except:
            self.value.setText(a)


class editFromKeypad(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","FromKeypad"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        l=QLabel(QCoreApplication.translate("ecl", "Min value"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 18px;")
            
        self.value.setText(self.cmdline.split()[2])
        
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        self.layout.addWidget(self.value)
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Max value"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.value2=QLineEdit()
        self.value2.setReadOnly(True)
        self.value2.setStyleSheet("font-size: 18px;")
            
        self.value2.setText(self.cmdline.split()[3])
        self.value2.mousePressEvent=self.val2Press
        self.value2.mouseReleaseEvent=self.val2Release
        self.layout.addWidget(self.value2)        
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Variable"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.target=QComboBox()
        self.target.setStyleSheet("font-size: 18px;")
        self.target.addItems(self.variables)

        if self.cmdline.split()[1] in self.variables:
            self.target.setCurrentIndex(self.variables.index(self.cmdline.split()[1]))
        else:
            self.target.setCurrentIndex(0)

        self.layout.addWidget(self.target)
        
        self.layout.addStretch()

        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="FromKeypad " +self.target.itemText(self.target.currentIndex())+ " " + self.value.text()
        self.cmdline=self.cmdline + " " + self.value2.text()
        
        self.close()
    
    def ifChanged(self):
        self.valueChanged()
    
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btn=1
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        if self.btn==1: self.value.setText(queryVarName(self.variables,self.value.text()))  
        else:           self.value2.setText(queryVarName(self.variables,self.value2.text())) 
            
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Min"),a,self).exec_()
        try:
            self.value.setText(str(int(t)))
        except:
            self.value.setText(a)
        
    def val2Press(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.btn=2
        self.timer.start(500)
     
    def val2Release(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value2.text())
            except:
                self.value2.setText("0")  
            self.getValue2(1)
            
    def getValue2(self,m):
        a=self.value2.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Max"),a,self).exec_()
        try:
            t=str(int(t))
        except:
            t=a
        self.value2.setText(t)

class editFromDial(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","FromDial"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
        
        inittext=""
        for v in self.cmdline.split()[4:]:
            inittext=inittext+" "+v
        
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedOut)
        
        self.layout=QVBoxLayout()
        
        l=QLabel(QCoreApplication.translate("ecl", "Message"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.text=QLineEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet("font-size: 18px;")
            
        self.text.setText(inittext)
        self.text.mousePressEvent=self.getText 
        
        self.layout.addWidget(self.text)
        
        l=QLabel(QCoreApplication.translate("ecl", "Min value"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.value=QLineEdit()
        self.value.setReadOnly(True)
        self.value.setStyleSheet("font-size: 18px;")
            
        self.value.setText(self.cmdline.split()[2])
        
        self.value.mousePressEvent=self.valPress
        self.value.mouseReleaseEvent=self.valRelease
        self.layout.addWidget(self.value)
        
        #self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Max value"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.value2=QLineEdit()
        self.value2.setReadOnly(True)
        self.value2.setStyleSheet("font-size: 18px;")
            
        self.value2.setText(self.cmdline.split()[3])
        self.value2.mousePressEvent=self.val2Press
        self.value2.mouseReleaseEvent=self.val2Release
        self.layout.addWidget(self.value2)        
        
        #self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Variable"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.target=QComboBox()
        self.target.setStyleSheet("font-size: 18px;")
        self.target.addItems(self.variables)

        if self.cmdline.split()[1] in self.variables:
            self.target.setCurrentIndex(self.variables.index(self.cmdline.split()[1]))
        else:
            self.target.setCurrentIndex(0)

        self.layout.addWidget(self.target)
        
        self.layout.addStretch()

        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline
    
    def on_confirm(self):
        self.cmdline="FromDial " +self.target.itemText(self.target.currentIndex())+ " " + self.value.text()
        self.cmdline=self.cmdline + " " + self.value2.text() + " " + self.text.text()
        
        self.close()
    
    def ifChanged(self):
        self.valueChanged()
    
    def valPress(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btn=1
        self.btnTimedOut=False
        self.timer.start(500)
    
    def timedOut(self):
        self.btnTimedOut=True
        self.timer.stop()
        if self.btn==1: self.value.setText(queryVarName(self.variables,self.value.text()))  
        else:           self.value2.setText(queryVarName(self.variables,self.value2.text())) 
            
    def valRelease(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value.text())
            except:
                self.value.setText("0")  
            self.getValue(1)
    
    def getValue(self,m):
        a=self.value.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Min"),a,self).exec_()
        try:
            self.value.setText(str(int(t)))
        except:
            self.value.setText(a)
        
    def val2Press(self,sender):
        if self.timer.isActive(): self.timer.stop()
        self.btnTimedOut=False
        self.btn=2
        self.timer.start(500)
     
    def val2Release(self,sender):
        self.timer.stop()
        if not self.btnTimedOut:
            try:
                int(self.value2.text())
            except:
                self.value2.setText("0")  
            self.getValue2(1)
            
    def getValue2(self,m):
        a=self.value2.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Max"),a,self).exec_()
        try:
            t=str(int(t))
        except:
            t=a
        self.value2.setText(t)
    
    def getText(self,m):
        a=self.text.text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Max"),a,self).exec_()
        self.text.setText(t)

class editFromButtons(TouchDialog):
    def __init__(self, cmdline, vari, parent=None):
        TouchDialog.__init__(self, QCoreApplication.translate("ecl","FromButtons"), parent)
        
        self.cmdline=cmdline
        self.variables=vari
    
    def exec_(self):
    
        self.confirm = self.titlebar.addConfirm()
        self.confirm.clicked.connect(self.on_confirm)
    
        self.titlebar.setCancelButton()
        
        self.layout=QVBoxLayout()

        l=QLabel(QCoreApplication.translate("ecl", "Buttons"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.buttons=QListWidget()
        self.buttons.setStyleSheet("font-size: 18px;")
        for x in self.cmdline.split()[2:]:
            self.buttons.addItem(x)
        self.buttons.itemDoubleClicked.connect(self.btnDblClick)
        
        self.layout.addWidget(self.buttons)
        
        h=QHBoxLayout()
        
        self.plus=QPushButton()
        self.plus.setText(" + ")
        self.plus.setStyleSheet("font-size: 18px;")
        self.plus.clicked.connect(self.plusBtn)
        
        h.addWidget(self.plus)
        
        self.minus=QPushButton()
        self.minus.setText(" - ")
        self.minus.setStyleSheet("font-size: 18px;")
        self.minus.clicked.connect(self.minusBtn)
        
        h.addWidget(self.minus)
        
        self.up=QPushButton()
        self.up.setText(QCoreApplication.translate("ecl","Up"))
        self.up.setStyleSheet("font-size: 18px;")
        self.up.clicked.connect(self.upBtn)
        
        h.addWidget(self.up)        
        
        self.down=QPushButton()
        self.down.setText(QCoreApplication.translate("ecl","Dn"))
        self.down.setStyleSheet("font-size: 18px;")
        self.down.clicked.connect(self.downBtn)
        
        h.addWidget(self.down)       
        
        self.layout.addLayout(h)
        
        self.layout.addStretch()
        
        l=QLabel(QCoreApplication.translate("ecl", "Variable"))
        l.setStyleSheet("font-size: 18px;")
        
        self.layout.addWidget(l)
        
        self.target=QComboBox()
        self.target.setStyleSheet("font-size: 18px;")
        self.target.addItems(self.variables)

        if self.cmdline.split()[1] in self.variables:
            self.target.setCurrentIndex(self.variables.index(self.cmdline.split()[1]))
        else:
            self.target.setCurrentIndex(0)

        self.layout.addWidget(self.target)
        
        self.layout.addStretch()

        self.centralWidget.setLayout(self.layout)
        
        TouchDialog.exec_(self)
        return self.cmdline

    def plusBtn(self):
        if self.buttons.count()<7:
            t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Btn. Text"),"Btn.",self).exec_()
            t=t.replace(" ","")
            if len(t)>0:
                self.buttons.addItem(t)
    
    def minusBtn(self):
        self.buttons.takeItem(self.buttons.row(self.buttons.currentItem()))

    def upBtn(self):
        row=self.buttons.currentRow()
        if row>0:
            i=self.buttons.takeItem(row)
            self.buttons.insertItem(row-1,i)
            self.buttons.setCurrentRow(row-1)
            
    def downBtn(self):
        row=self.buttons.currentRow()
        if row<self.buttons.count()-1:
            i=self.buttons.takeItem(row)
            self.buttons.insertItem(row+1,i)
            self.buttons.setCurrentRow(row+1)
    
    def btnDblClick(self):
        t=self.buttons.currentItem().text()
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Btn. Text"),t,self).exec_()
        t=t.replace(" ","")
        if len(t)>0:
            self.buttons.currentItem().setText(t)
    
    def on_confirm(self):
        self.cmdline="FromButtons " +self.target.itemText(self.target.currentIndex())
        
        for i in range(0,self.buttons.count()):
            self.cmdline=self.cmdline + " " + self.buttons.item(i).text()
        

#
# main GUI application
#

class FtcGuiApplication(TouchApplication):
    outputClicked=pyqtSignal(int)
    msgBack=pyqtSignal(int)
    IMsgBack=pyqtSignal(str)
    stop=pyqtSignal()
    
    def __init__(self, args):
        TouchApplication.__init__(self, args)
        
        # some init
        
        self.RIF=None
        self.TXT=None
        self.FTD=None
        self.etf=False
        
        # load last project
        
        try:
            with open(hostdir+".lastproject","r", encoding="utf-8") as f:
                [self.codeName,self.codeSaved]=json.load(f)
            
            if not self.codeSaved:
                with open(hostdir+".autosave","r", encoding="utf-8") as f:
                    self.code=json.load(f)                
                os.remove(hostdir+".autosave")
            else:
                with open(projdir+self.codeName,"r", encoding="utf-8") as f:
                    self.code=json.load(f)
        except:
            self.code=["# new"]
            self.codeSaved=True
            self.codeName="startIDE"        
        
        self.n=0
        
        # init internationalisation
        translator = QTranslator()
        path = os.path.dirname(os.path.realpath(__file__))
        translator.load(QLocale.system(), os.path.join(path, "startide_"))
        self.installTranslator(translator)

        # create the empty main window
        self.mainwindow = TouchWindow("startIDE")
        
        # query screen orientation
        
        if self.mainwindow.width()>self.mainwindow.height():
            self.orientation=LANDSCAPE
        else:
            self.orientation=PORTRAIT
        
        # add a menu
        
        self.menu=self.mainwindow.addMenu()
        self.menu.setStyleSheet("font-size: 24px;")
                
        self.m_project = self.menu.addAction(QCoreApplication.translate("mmain","Project"))
        self.m_project.triggered.connect(self.on_menu_project) 
        
        self.menu.addSeparator()
        
        self.m_modules = self.menu.addAction(QCoreApplication.translate("mmain","Modules"))
        self.m_modules.triggered.connect(self.on_menu_modules)
        
        self.menu.addSeparator()
        
        self.m_interf = self.menu.addAction(QCoreApplication.translate("mmain","Interfaces"))
        self.m_interf.triggered.connect(self.on_menu_interfaces)  
        
        self.menu.addSeparator()
        
        self.m_about=self.menu.addAction(QCoreApplication.translate("mmain","About"))
        self.m_about.triggered.connect(self.on_menu_about)
        
        
        # and the central widget
        self.centralwidget=QWidget()
        
        # the main window layout
        l=QVBoxLayout() 
        
        if self.orientation==LANDSCAPE:
            l2=QHBoxLayout()
            l3=QVBoxLayout()
            
        # program list widget
        self.proglist=QListWidget()
        self.proglist.setStyleSheet("font-family: 'Monospace'; font-size: 16px;")
        self.proglist.itemDoubleClicked.connect(self.progItemDoubleClicked)
        
        c=0
        for a in self.code:
            self.proglist.addItem(a)
            c=c+1
            
        if self.orientation==PORTRAIT:
            l.addWidget(self.proglist)
        else:
            l3.addWidget(self.proglist)
            
        # alternate output text field
        
        self.output=QListWidget()
        self.output.setStyleSheet("font-family: 'Monospace'; font-size: 18px;")
        self.output.setSelectionMode(0)
        self.output.setVerticalScrollMode(1)
        self.output.setHorizontalScrollMode(1)
        self.output.mousePressEvent=self.outputClicked.emit
        
        if self.orientation==PORTRAIT:
            l.addWidget(self.output)
        else:
            l3.addWidget(self.output)
            
        self.output.hide()
        
        self.proglist.setCurrentRow(0)
        
        # and the controls
        
        if self.orientation==PORTRAIT:
            h=QHBoxLayout()
        else:
            h=QVBoxLayout()
            
        self.add = QPushButton(" + ")
        self.add.setStyleSheet("font-size: 20px;")
        self.add.clicked.connect(self.addCodeLine)
        
        self.cop = QPushButton("Cp")
        self.cop.setStyleSheet("font-size: 20px;")
        self.cop.clicked.connect(self.copyCodeLine)        
        
        self.rem = QDblPushButton(" - ")
        self.rem.setStyleSheet("font-size: 20px;")
        self.rem.doubleClicked.connect(self.remCodeLine)
        
        self.upp = QPushButton(QCoreApplication.translate("main","Up"))
        self.upp.setStyleSheet("font-size: 20px;")
        self.upp.clicked.connect(self.lineUp)
        
        self.don = QPushButton(QCoreApplication.translate("main","Dn"))
        self.don.setStyleSheet("font-size: 20px;")
        self.don.clicked.connect(self.lineDown)
        
        h.addWidget(self.add)
        h.addWidget(self.cop)
        h.addWidget(self.rem)
        h.addWidget(self.upp)
        h.addWidget(self.don)
        
        if self.orientation==PORTRAIT:
            l.addLayout(h)
        else:
            l2.addLayout(l3)
            l2.addLayout(h)
            
        

        self.starter = QPushButton(QCoreApplication.translate("main","Start"))
            
        self.starter.setStyleSheet("font-size: 20px;")
        self.starter.clicked.connect(self.startStop)
        
        self.start=False
        
        if self.orientation==PORTRAIT:
            l.addWidget(self.starter)
        else:
            l3.addWidget(self.starter)
            l.addLayout(l2)
 
            
        self.centralwidget.setLayout(l)
        self.mainwindow.setCentralWidget(self.centralwidget)
        
        self.mainwindow.titlebar.close.clicked.connect(self.closed)

        canvasSize=min(self.mainwindow.width(),self.mainwindow.height())
        self.canvas=QLabel(self.mainwindow)
        self.canvas.setGeometry(0, 0, canvasSize, canvasSize)        
        #self.canvas.setPixmap(QPixmap(pixdir+"pixmap.png"))
        self.canvas.setPixmap(QPixmap(canvasSize, canvasSize))
        self.canvas.hide()
        
        self.mainwindow.show()
        try:
            if os.path.isfile(hostdir+".01_firstrun"):
                t=TouchMessageBox("first run", self.mainwindow)
                t.setCancelButton()
                with open(hostdir+".01_firstrun", "r", encoding="utf-8") as f:
                    msg=f.read()
                    f.close()
                t.setText(msg)
                t.exec_()
                
                os.remove(hostdir+".01_firstrun")
        except:
            pass
        
        # init the interfaces
        self.initIFs()
        
        self.lastIF="TXT"
        if self.RIF != None and self.TXT==None: self.lastIF="RIF"
        
        self.exec_()
    
    def closed(self):
        if self.start==True: self.startStop()
        
        self.codeFromListWidget()
        
        if not self.codeSaved:
            with open(hostdir+".autosave","w", encoding="utf-8") as f:
                json.dump(self.code,f)
                f.close()           
        
        with open(hostdir+".lastproject", "w", encoding="utf-8") as f:
            json.dump([self.codeName, self.codeSaved],f)


    def on_menu_about(self):
        t=TouchMessageBox(QCoreApplication.translate("m_about","About"), self.mainwindow)
        t.setCancelButton()
        t.setText("<center><h2>startIDE</h2><hr>" + QCoreApplication.translate("m_about","A tiny IDE to control Robo Family Interfaces and TXT Hardware.")
                  + "<hr>" + QCoreApplication.translate("m_about","The manual is available in the TXT startIDE webinterface under 'Get more app info'.")
                  + "<hr>(c)2017 Peter Habermehl<br>Version: "+vstring)
        t.setTextSize(1)
        t.setBtnTextSize(2)
        t.setNegButton(QCoreApplication.translate("m_about","Okay"))
        t.setPosButton(QCoreApplication.translate("m_about","News"))
        (v1,v2)=t.exec_() 
        if v2==QCoreApplication.translate("m_about","News"):
            t=TouchMessageBox(QCoreApplication.translate("m_about","News"), self.mainwindow)
            t.setCancelButton()
            if os.path.isfile(hostdir+".00_news"):
                with open(hostdir+".00_news","r") as f:
                    text=f.read()
                    f.close()
            else: text="No news found."
            t.setText(text)
            t.setTextSize(1)
            t.exec_()
            
    def on_menu_project(self):
        fta=TouchAuxMultibutton(QCoreApplication.translate("m_project","Project"), self.mainwindow)
        fta.setButtons([ QCoreApplication.translate("m_project","New"),
                        "",
                         QCoreApplication.translate("m_project","Load"),
                         QCoreApplication.translate("m_project","Save"),
                        "",
                         QCoreApplication.translate("m_project","Delete")
                        ]
                      )
        fta.setTextSize(3)
        fta.setBtnTextSize(3)
        (s,r)=fta.exec_()      
        
        if   r == QCoreApplication.translate("m_project","New"):    self.project_new()
        elif r == QCoreApplication.translate("m_project","Load"):   self.project_load()
        elif r == QCoreApplication.translate("m_project","Save"):   self.project_save()
        elif r == QCoreApplication.translate("m_project","Delete"): self.project_delete()   
    
    def project_new(self):
        if not self.codeSaved:
            t=TouchMessageBox(QCoreApplication.translate("m_project","New"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_project","Current project was not saved. Do you want to discard it?"))
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_project","Yes"))
            t.setNegButton(QCoreApplication.translate("m_project","No"))
            (r,s)=t.exec_()
            
            if s !=  QCoreApplication.translate("m_project","Yes"): return
        
        self.proglist.clear()
        self.code=[]
        self.proglist.addItem("# new")
        self.proglist.setCurrentRow(0)
        
        self.codeSaved=False
        self.codeName="Unnamed"
        
    def project_load(self):
        if not self.codeSaved:
            t=TouchMessageBox(QCoreApplication.translate("m_project","Load"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_project","Current project was not saved. Do you want to discard it?"))
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_project","Yes"))
            t.setNegButton(QCoreApplication.translate("m_project","No"))
            (r,s)=t.exec_()
            
            if s !=  QCoreApplication.translate("m_project","Yes"): return
        
        # get list of projecs and query user
        filelist=os.listdir(projdir)
        filelist.sort()
        if len(filelist)>0:
            (s,r)=TouchAuxListRequester(QCoreApplication.translate("m_project","Load"),QCoreApplication.translate("ecl","Project"),filelist,filelist[0],"Okay",self.mainwindow).exec_()
        else:
            t=TouchMessageBox(QCoreApplication.translate("m_project","Load"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_project","No saved projects found."))
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_project","Okay"))
            (v1,v2)=t.exec_()   
            s=False
            
        if not s: return
    
        with open(projdir+r,"r", encoding="utf-8") as f:
            self.code=json.load(f)
            f.close()
        
        self.proglist.clear()
        self.proglist.addItems(self.code)
        
        self.codeSaved=True
        self.codeName=r

    def project_save(self):
        (s,r)=TouchAuxRequestText(QCoreApplication.translate("m_project","Save"),
                            QCoreApplication.translate("m_project","Enter project file name:"),
                            self.codeName,
                            QCoreApplication.translate("m_project","Okay"), self.mainwindow
                            ).exec_()
        
        if not s: return
        pfn=r
        if os.path.isfile(projdir+pfn):
            t=TouchMessageBox(QCoreApplication.translate("m_project","Save"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_project","A file with this name already exists. Do you want to overwrite it?"))
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_project","Yes"))
            t.setNegButton(QCoreApplication.translate("m_project","No"))
            (r,s)=t.exec_()
            
            if s !=  QCoreApplication.translate("m_project","Yes"): return
        
        self.codeFromListWidget()
        
        with open(projdir+pfn,"w", encoding="utf-8") as f:
            
            json.dump(self.code,f)
            f.close()
    
        self.codeSaved=True
        self.codeName=pfn
        
    def project_delete(self):
 
        # get list of projecs and query user
        filelist=os.listdir(projdir)                          
        if len(filelist)>0:
            (s,r)=TouchAuxListRequester(QCoreApplication.translate("m_project","Delete"),QCoreApplication.translate("ecl","Project"),filelist,filelist[0],"Okay",self.mainwindow).exec_()
        else:
            t=TouchMessageBox(QCoreApplication.translate("m_project","Delete"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_project","No saved projects found."))
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_project","Okay"))
            (v1,v2)=t.exec_()   
            s=False
            
        if not s: return
        
        t=TouchMessageBox(QCoreApplication.translate("m_project","Delete"), self.mainwindow)
        t.setCancelButton()
        t.setText(QCoreApplication.translate("m_project","Do you really want to permanently delete this project?")+"<br>"+r)
        t.setBtnTextSize(2)
        t.setPosButton(QCoreApplication.translate("m_project","Yes"))
        t.setNegButton(QCoreApplication.translate("m_project","No"))
        (v1,v2)=t.exec_()
            
        if v2 !=  QCoreApplication.translate("m_project","Yes"): return
        
        os.remove(projdir+r)
        
        if self.codeName==r: self.codeSaved=False

    def on_menu_modules(self):
        fta=TouchAuxMultibutton(QCoreApplication.translate("m_project","Modules"), self.mainwindow)
        fta.setButtons([ QCoreApplication.translate("m_project","Import"),
                         QCoreApplication.translate("m_project","Export"),
                        "",
                         QCoreApplication.translate("m_project","Delete")
                        ]
                      )
        fta.setTextSize(3)
        fta.setBtnTextSize(3)
        (s,r)=fta.exec_()      
        
        if   r == QCoreApplication.translate("m_project","Import"):    self.modules_import()
        elif r == QCoreApplication.translate("m_project","Export"):    self.modules_export()
        elif r == QCoreApplication.translate("m_project","Delete"):    self.modules_delete()
    
    def modules_import(self):
        # get list of projecs and query user
        filelist=os.listdir(moddir)
        filelist.sort()
        if len(filelist)>0:
            (s,r)=TouchAuxListRequester(QCoreApplication.translate("m_modules","Import"),QCoreApplication.translate("m_modules","Module"),filelist,filelist[0],"Okay",self.mainwindow).exec_()
        else:
            t=TouchMessageBox(QCoreApplication.translate("m_modules","Import"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_modules","No saved modules found."))
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_modules","Okay"))
            (v1,v2)=t.exec_()   
            s=False
            
        if not s: return
    
        with open(moddir+r,"r", encoding="utf-8") as f:
            module=json.load(f)
        
        self.codeFromListWidget()

        m=self.proglist.currentRow()
        n=m
        
        for a in module:
            self.code.insert(m+1,a)
            m=m+1

        self.proglist.clear()
        self.proglist.addItems(self.code)
        self.proglist.setCurrentRow(n+1)
        
        self.codeSaved=False

    
    def modules_export(self):
        self.codeFromListWidget()
        modTable=[]
        modList=[]
        mcnt=0
        cnt=0
        for line in self.code:
            a=line.split()
            if "Module" in line[:6]:
                modTable.append([line[7:], cnt])
                modList.append(line[7:])
                mcnt=mcnt+1
            elif "MEnd" in line[:4]:
                mcnt=mcnt-1
            cnt=cnt+1
            
        if mcnt<0:
            t=TouchMessageBox(QCoreApplication.translate("m_modules","Modules"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_modules","MEnd found with-\nout Module!\nPlease fix before export!\n"))
            t.setTextSize(1)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_modules","Okay"))
            (v1,v2)=t.exec_() 
            return
        elif mcnt>0:
            t=TouchMessageBox(QCoreApplication.translate("m_modules","Modules"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_modules","MEnd missing!\nPlease fix before export!\n"))
            t.setTextSize(1)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_modules","Okay"))
            (v1,v2)=t.exec_() 
            return
        
        if len(modTable)>0:
            (s,r)=TouchAuxListRequester(QCoreApplication.translate("m_modules","Export"),QCoreApplication.translate("m_modules","Module"),modList,modList[0],"Okay",self.mainwindow).exec_()
        else:
            t=TouchMessageBox(QCoreApplication.translate("m_modules","Export"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_modules","No modules found."))
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_modules","Okay"))
            (v1,v2)=t.exec_()   
            s=False
            
        if not s: return
        
        cnt=0
        for a in modList:
            if r==modTable[cnt][0]:   break
            cnt=cnt+1

        pfn=r
        if os.path.isfile(moddir+pfn):
            t=TouchMessageBox(QCoreApplication.translate("m_modules","Export"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_modules","A module file with this name already exists. Do you want to overwrite it?"))
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_modules","Yes"))
            t.setNegButton(QCoreApplication.translate("m_modules","No"))
            (r,s)=t.exec_()
            
            if s !=  QCoreApplication.translate("m_modules","Yes"): return

        module=[]
        a=modTable[cnt][1]
        while self.code[a]!="MEnd":
            module.append(self.code[a])
            a=a+1
        module.append("MEnd")
        
        with open(moddir+pfn,"w", encoding="utf-8") as f:
            
            json.dump(module,f)
            f.close()
        
    def modules_delete(self):
        
        # get list of modules and query user
        filelist=os.listdir(moddir)                          
        if len(filelist)>0:
            (s,r)=TouchAuxListRequester(QCoreApplication.translate("m_modules","Delete"),QCoreApplication.translate("ecl","Module"),filelist,filelist[0],"Okay",self.mainwindow).exec_()
        else:
            t=TouchMessageBox(QCoreApplication.translate("m_modules","Delete"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("m_modules","No saved modules found."))
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_modules","Okay"))
            (v1,v2)=t.exec_()   
            s=False
            
        if not s: return
        
        t=TouchMessageBox(QCoreApplication.translate("m_modules","Delete"), self.mainwindow)
        t.setCancelButton()
        t.setText(QCoreApplication.translate("m_modules","Do you really want to permanently delete this module?")+"<br>"+r)
        t.setBtnTextSize(2)
        t.setPosButton(QCoreApplication.translate("m_modules","Yes"))
        t.setNegButton(QCoreApplication.translate("m_modules","No"))
        (v1,v2)=t.exec_()
            
        if v2 !=  QCoreApplication.translate("m_modules","Yes"): return
        
        os.remove(moddir+r)
        

    def on_menu_interfaces(self):
        global RIFSERIAL
        
        self.initIFs()
        
        if self.RIF==None: s= QCoreApplication.translate("m_interfaces","No Robo device")
        else: s = self.RIF.GetDeviceTypeString()
                
        if self.TXT==None: t = QCoreApplication.translate("m_interfaces","No TXT device")
        else: t = QCoreApplication.translate("m_interfaces","TXT found")
        
        if self.FTD==None: u = QCoreApplication.translate("m_interfaces","No ftduino device")
        else: u = "ftduino '"+self.FTD.comm("ftduino_id_get") + "' " + QCoreApplication.translate("m_interfaces","found")
        
        text="<center>" + QCoreApplication.translate("m_interfaces","Hardware found:") + "<hr><i>" + s + "<hr>" + t + "<hr>" + u
        
        t=TouchMessageBox(QCoreApplication.translate("m_interfaces","Interfaces"), self.mainwindow)
        t.setCancelButton()
        t.setText(text)
        t.setTextSize(1)
        t.setBtnTextSize(2)
        t.setNegButton(QCoreApplication.translate("m_interfaces","Okay"))
        t.setPosButton(QCoreApplication.translate("m_interfaces","Enable IIF"))
        (v1,v2)=t.exec_()  

        if v2==QCoreApplication.translate("m_interfaces","Enable IIF"):
            v2=""
            text=QCoreApplication.translate("m_interfaces","Enabling IIF with any device other than an Intelligent Interface connected to '/dev/ttyUSB0' will crash startIDE.")
            t=TouchMessageBox(QCoreApplication.translate("m_interfaces","Enable IIF"), self.mainwindow)
            t.setCancelButton()
            t.setText(text)
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("m_interfaces","Cancel"))
            t.setNegButton(QCoreApplication.translate("m_interfaces","Enable IIF"))
            (v1,v2)=t.exec_()             
            if v2==QCoreApplication.translate("m_interfaces","Enable IIF"):
                RIFSERIAL="/dev/ttyUSB0"
                self.initIFs()
                
    def initIFs(self):
        # close, if open
        if self.RIF:
            self.RIF.close()
            time.sleep(0.1)
            
        #init robo family
        if RIFSERIAL!="":
            self.RIF=RoboInterface(serialDevice=RIFSERIAL.encode(), SerialType=RoboInterface.FT_INTELLIGENT_IF)
        else:
            self.RIF=RoboInterface(bEnableDist=True)
        
        s=""
        if self.RIF.hasInterface(): s = self.RIF.GetDeviceTypeString()
        
        # print(self.RIF.IsConnected, s, len(s))
        if s=="": self.RIF=None

        self.TXT=None
        try:
            self.TXT=txt.ftrobopy(FTTXTADDRESS)
            name, version = self.TXT.queryStatus()
        except:
            self.TXT=None      
            
        if FTDUINO_DIRECT:
            self.FTD=ftd.ftduino()
            if self.FTD.getDevice()==None:
                self.FTD=None
        else:
            self.FTD=None
        
            
    def codeFromListWidget(self):
        self.code=[]
        for i in range(0,self.proglist.count()): self.code.append(self.proglist.item(i).text())
        
    def startStop(self):
        self.starter.setEnabled(False)
        self.menu.setEnabled(False)
        self.mainwindow.titlebar.menubut.hide()
        #self.mainwindow.titlebar.hide()
        self.starter.setDisabled(True)
        self.processEvents()
        
        if self.etf:
            self.canvas.hide()
            self.setMainWindow(True)
            self.mainwindow.titlebar.menubut.show()
            #self.mainwindow.titlebar.show()
            self.menu.setEnabled(True)
            self.etf=False
            self.start=False
        else:
            self.start=not self.start
            
            if self.start:
                self.codeFromListWidget()
                self.setMainWindow(False)
                self.et = execThread(self.code, self.output, self.starter, self.RIF, self.TXT, self.FTD, self)
                self.et.updateText.connect(self.updateText)
                self.et.clearText.connect(self.clearText)
                self.et.execThreadFinished.connect(self.execThreadFinished)
                self.et.showMessage.connect(self.messageBox)
                self.et.requestKeyboard.connect(self.requestKeyboard)
                self.et.requestDial.connect(self.requestDial)
                self.et.requestBtn.connect(self.requestButton)
                self.et.canvasSig.connect(self.canvasSig)
                self.et.start() 
            else:
                self.stop.emit()
            
            self.processEvents()

        self.starter.setEnabled(True)
        self.starter.setDisabled(False)

    def updateText(self, message):
        self.output.addItem(message)
        if self.output.count()>255: void=self.output.takeItem(0)
        self.output.scrollToBottom()
        self.msgBack.emit(1)
        
    def clearText(self):
        self.output.clear()
        self.output.scrollToBottom()
        self.msgBack.emit(1)
    
    def execThreadFinished(self):
        self.starter.setText(QCoreApplication.translate("main","Close log"))
        self.etf=True
        
    def canvasSig(self, stack):
        s=stack.split()
        if s[0]=="show": self.canvas.show()
        elif s[0]=="hide": self.canvas.hide()
        elif s[0]=="square":
            canvasSize=min(self.mainwindow.width(),self.mainwindow.height())
            self.canvas.setGeometry(0, 0, canvasSize, canvasSize)
            self.canvas.setPixmap(QPixmap(canvasSize, canvasSize))
        elif s[0]=="full":
            self.canvas.setGeometry(0, 0, self.mainwindow.width(), self.mainwindow.height())
            self.canvas.setPixmap(QPixmap(self.mainwindow.width(), self.mainwindow.height()))
        elif s[0]=="clear":
            self.canvas.setPixmap(QPixmap(self.mainwindow.width(), self.mainwindow.height()))
            pm=self.canvas.pixmap() #QPixmap(self.canvas.width(), self.canvas.height())
            p=QPainter()
            p.begin(pm)
            p.setPen(QtGui.QColor(255, 0, 0, 0))
            p.setBackgroundMode(0)
            p.drawRect(0,0,pm.width(),pm.height())
            p.end()
        elif s[0]=="plot":
            pm=self.canvas.pixmap()
            p=QPainter()
            p.begin(pm)
            p.setPen(QtGui.QColor(self.pred, self.pgreen, self.pblue, 255))
            self.xpos=int(s[1])
            self.ypos=int(s[2])
            p.drawPoint(self.xpos,self.ypos)
            p.end()
        elif s[0]=="lineTo":
            pm=self.canvas.pixmap()
            p=QPainter()
            p.begin(pm)
            p.setPen(QtGui.QColor(self.pred, self.pgreen, self.pblue, 255))
            ax=self.xpos
            ay=self.ypos
            self.xpos=int(s[1])
            self.ypos=int(s[2])
            p.drawLine(ax,ay,self.xpos,self.ypos)
            p.end()  
        elif s[0]=="rectTo":
            pm=self.canvas.pixmap()
            p=QPainter()
            p.begin(pm)
            p.setPen(QtGui.QColor(self.pred, self.pgreen, self.pblue, 255))
            ax=self.xpos
            ay=self.ypos
            self.xpos=int(s[1])
            self.ypos=int(s[2])
            p.drawRect(ax,ay,self.xpos-ax,self.ypos-ay)
            p.end() 
        elif s[0]=="boxTo":
            pm=self.canvas.pixmap()
            p=QPainter()
            p.begin(pm)
            p.setPen(QtGui.QColor(self.pred, self.pgreen, self.pblue, 255))
            ax=self.xpos
            ay=self.ypos
            self.xpos=int(s[1])
            self.ypos=int(s[2])
            p.fillRect(ax,ay,self.xpos-ax,self.ypos-ay)
            p.end() 
            
    def messageBox(self, stack):
        msg=stack.split("'")
        t=TouchMessageBox(QCoreApplication.translate("exec","Message"),self.mainwindow)
        t.setCancelButton()
        t.setText(msg[0])
        t.setTextSize(2)
        t.setBtnTextSize(2)
        t.setPosButton(msg[1])
        (v1,v2)=t.exec_()       
        self.msgBack.emit(1)
    
    def requestKeyboard(self, stack, title):
        t=TouchAuxKeyboard(title,str(stack), self.mainwindow).exec_()        
        self.IMsgBack.emit(t)
        self.msgBack.emit(1)
    
    def requestDial(self, msg, stack, miv, mav, title):
        s,r=TouchAuxRequestInteger(
            title,msg,
            int(stack),
            min(miv,mav),
            max(miv,mav),"Okay",self.mainwindow).exec_()   
        
        if s: self.IMsgBack.emit(str(r))
        else: self.IMsgBack.emit(str(stack))
        
        self.msgBack.emit(1)
        
    def requestButton(self, title, msg, buttons):
        fta=TouchAuxMultibutton(title, self.mainwindow)
        fta.setButtons(buttons)
        fta.setTextSize(3)
        fta.setBtnTextSize(3)
        (s,r)=fta.exec_()      
        
        if s:
            self.IMsgBack.emit(str(buttons.index(r)+1))
        else:
            self.IMsgBack.emit("-1")
        self.msgBack.emit(1)
        
    def setMainWindow(self, status):
        #true -> main window enabled 
        
        self.add.setVisible(status)
        self.cop.setVisible(status)
        self.rem.setVisible(status)
        self.upp.setVisible(status)
        self.don.setVisible(status)
        self.proglist.setVisible(status)
        
        self.output.setVisible(not status)
    
        if status:
            self.starter.setText(QCoreApplication.translate("main","Start"))
        else:
            self.starter.setText(QCoreApplication.translate("main","Stop"))

    def copyCodeLine(self):
        row=self.proglist.currentRow()
        i=self.proglist.item(row).text()
        self.proglist.insertItem(row+1,i)
        self.proglist.setCurrentRow(row+1)
        
        self.codeSaved=False
        
    def addCodeLine(self):
        fta=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","New cmd:"), self.mainwindow)
        fta.setButtons([ QCoreApplication.translate("addcodeline","Inputs"),
                         QCoreApplication.translate("addcodeline","Outputs"),
                         QCoreApplication.translate("addcodeline","Variables"),
                         QCoreApplication.translate("addcodeline","Controls"),
                         QCoreApplication.translate("addcodeline","Modules"),
                         QCoreApplication.translate("addcodeline","Interaction")
                        ]
                      )
        try:
            fta.setColumnSplit(3)
        except:
            pass
        fta.setTextSize(3)
        fta.setBtnTextSize(3)
        (s,r)=fta.exec_()
        if r==QCoreApplication.translate("addcodeline","Inputs"):
            ftb=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","Inputs"), self.mainwindow)
            ftb.setButtons([ QCoreApplication.translate("addcodeline","WaitForInputDig"),
                             QCoreApplication.translate("addcodeline","IfInputDig"),
                             QCoreApplication.translate("addcodeline","WaitForInput"),
                             QCoreApplication.translate("addcodeline","IfInput"),
                             QCoreApplication.translate("addcodeline","QueryInput"),
                             QCoreApplication.translate("addcodeline","CounterClear")
                            ]
                          )
            ftb.setTextSize(3)
            ftb.setBtnTextSize(3)
            (t,p)=ftb.exec_()
            if t:
                if   p==QCoreApplication.translate("addcodeline","WaitForInputDig"):
                    self.acl_waitForInputDig()
                elif p==QCoreApplication.translate("addcodeline","IfInputDig"):
                    self.acl_ifInputDig()
                elif p==QCoreApplication.translate("addcodeline","WaitForInput"):
                    self.acl_waitForInput()
                elif p==QCoreApplication.translate("addcodeline","IfInput"):
                    self.acl_ifInput()
                elif p==QCoreApplication.translate("addcodeline","QueryInput"):
                    self.acl_queryIn()
                elif p==QCoreApplication.translate("addcodeline","CounterClear"):
                    self.acl_counterClear()
        elif r==QCoreApplication.translate("addcodeline","Outputs"):
            ftb=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","Outputs"), self.mainwindow)
            ftb.setButtons([ QCoreApplication.translate("addcodeline","Output"),
                             QCoreApplication.translate("addcodeline","Motor"),
                             QCoreApplication.translate("addcodeline","MotorPulsew."),
                             QCoreApplication.translate("addcodeline","MotorEnc"),
                             QCoreApplication.translate("addcodeline","MotorEncSync")
                            ]
                          )
            ftb.setTextSize(3)
            try:
                ftb.setColumnSplit(3)
            except:
                pass
            ftb.setBtnTextSize(3)
            (t,p)=ftb.exec_()
            if t:
                if   p==QCoreApplication.translate("addcodeline","Output"):  self.acl_output()
                elif p==QCoreApplication.translate("addcodeline","Motor"):   self.acl_motor()
                elif p==QCoreApplication.translate("addcodeline","MotorPulsew."):   self.acl_motorPulsewheel()
                elif p==QCoreApplication.translate("addcodeline","MotorEnc"):   self.acl_motorEncoder()  
                elif p==QCoreApplication.translate("addcodeline","MotorEncSync"): self.acl_motorEncoderSync()

        elif r==QCoreApplication.translate("addcodeline","Variables"):
            ftb=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","Variables"), self.mainwindow)
            ftb.setButtons([ QCoreApplication.translate("addcodeline","Init"),
                             QCoreApplication.translate("addcodeline","From..."),
                             #QCoreApplication.translate("addcodeline","Shelf"),
                             QCoreApplication.translate("addcodeline","QueryVar"),
                             QCoreApplication.translate("addcodeline","IfVar"),
                             QCoreApplication.translate("addcodeline","Calc")
                            ]
                          )
            ftb.setTextSize(3)
            try:
                ftb.setColumnSplit(3)
            except:
                pass
            
            ftb.setBtnTextSize(3)
            (t,p)=ftb.exec_()
            if t:
                if   p==QCoreApplication.translate("addcodeline","Init"):       self.acl_init()
                if   p==QCoreApplication.translate("addcodeline","From..."):
                    ftb=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","Variables"), self.mainwindow)
                    ftb.setButtons([    QCoreApplication.translate("addcodeline","FromIn"),
                                        QCoreApplication.translate("addcodeline","FromKeypad"),
                                        QCoreApplication.translate("addcodeline","FromDial"),
                                        QCoreApplication.translate("addcodeline","FromButtons"),
                                        QCoreApplication.translate("addcodeline","FromPoly")
                                    ])
                    ftb.setTextSize(3)
                    try:
                        ftb.setColumnSplit(3)
                    except:
                        pass
                    
                    ftb.setBtnTextSize(3)
                    (t2,p2)=ftb.exec_()
                    
                    if   p2==QCoreApplication.translate("addcodeline","FromIn"):     self.acl_fromIn()
                    elif p2==QCoreApplication.translate("addcodeline","FromKeypad"): self.acl_fromKeypad()
                    elif p2==QCoreApplication.translate("addcodeline","FromDial"): self.acl_fromDial()
                    elif p2==QCoreApplication.translate("addcodeline","FromButtons"): self.acl_fromButtons()
                    elif p2==QCoreApplication.translate("addcodeline","FromPoly"): self.acl_fromPoly()
                    
                elif p==QCoreApplication.translate("addcodeline","Shelf"):      self.acl_shelf()
                elif p==QCoreApplication.translate("addcodeline","QueryVar"):   self.acl_queryVar()  
                elif p==QCoreApplication.translate("addcodeline","IfVar"):      self.acl_ifVar()                
                elif p==QCoreApplication.translate("addcodeline","Calc"):       self.acl_calc()
                
        elif r==QCoreApplication.translate("addcodeline","Controls"):
            ftb=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","Controls"), self.mainwindow)
            ftb.setButtons([ QCoreApplication.translate("addcodeline","# comment"),
                             QCoreApplication.translate("addcodeline","Tag"),
                             QCoreApplication.translate("addcodeline","Jump"),
                             QCoreApplication.translate("addcodeline","LoopTo"),
                             QCoreApplication.translate("addcodeline","Time"),
                             QCoreApplication.translate("addcodeline","Stop")
                            ]
                          )
            ftb.setTextSize(3)
            ftb.setBtnTextSize(3)
            (t,p)=ftb.exec_()
            if t:
                if   p==QCoreApplication.translate("addcodeline","# comment"):  self.acl_comment()
                elif p==QCoreApplication.translate("addcodeline","Tag"):        self.acl_tag()
                elif p==QCoreApplication.translate("addcodeline","Jump"):       self.acl_jump()
                elif p==QCoreApplication.translate("addcodeline","LoopTo"):     self.acl_loopTo()
                elif p==QCoreApplication.translate("addcodeline","Time"):
                    ftb=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","Time"), self.mainwindow)
                    ftb.setButtons([ QCoreApplication.translate("addcodeline","Delay"),
                             QCoreApplication.translate("addcodeline","TimerQuery"),
                             QCoreApplication.translate("addcodeline","TimerClear"),
                             QCoreApplication.translate("addcodeline","IfTimer"),
                             QCoreApplication.translate("addcodeline","Interrupt"),
                             QCoreApplication.translate("addcodeline","QueryNow")
                            ]
                          )
                    ftb.setTextSize(3)
                    ftb.setBtnTextSize(3)
                    (t,p)=ftb.exec_()
                    if t:
                        if p==QCoreApplication.translate("addcodeline","Delay"):        self.acl_delay()
                        elif p==QCoreApplication.translate("addcodeline","TimerQuery"):
                            self.acl_timerquery()
                        elif p==QCoreApplication.translate("addcodeline","TimerClear"): #
                            self.acl_timerclear()
                        elif p==QCoreApplication.translate("addcodeline","IfTimer"):   
                            self.acl_iftimer()
                        elif p==QCoreApplication.translate("addcodeline","Interrupt"):  
                            self.acl_interrupt()
                        elif p==QCoreApplication.translate("addcodeline","QueryNow"):
                            self.acl_queryNow()
                elif p==QCoreApplication.translate("addcodeline","Stop"):       self.acl_stop()
        
        elif r==QCoreApplication.translate("addcodeline","Modules"):
            ftb=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","Modules"), self.mainwindow)
            ftb.setButtons([ QCoreApplication.translate("addcodeline","Call"),
                             QCoreApplication.translate("addcodeline","CallExt"),
                             QCoreApplication.translate("addcodeline","Return"),
                             QCoreApplication.translate("addcodeline","Module"),
                             QCoreApplication.translate("addcodeline","MEnd")
                            ]
                          )
            ftb.setTextSize(3)
            ftb.setBtnTextSize(3)
            (t,p)=ftb.exec_()
            if t:
                if   p==QCoreApplication.translate("addcodeline","Call"):     self.acl_call()
                elif p==QCoreApplication.translate("addcodeline","CallExt"):  self.acl_callext()
                elif p==QCoreApplication.translate("addcodeline","Return"):   self.acl_return()
                elif p==QCoreApplication.translate("addcodeline","Module"):   self.acl_module()
                elif p==QCoreApplication.translate("addcodeline","MEnd"):     self.acl_mend()
                            
        elif r==QCoreApplication.translate("addcodeline","Interaction"):
            ftb=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","Interact"), self.mainwindow)
            ftb.setButtons([ QCoreApplication.translate("addcodeline","Print"),
                             QCoreApplication.translate("addcodeline","Clear"),
                             QCoreApplication.translate("addcodeline","Message"),
                             QCoreApplication.translate("addcodeline","Logfile")
                            ]
                          )
            ftb.setTextSize(3)
            ftb.setBtnTextSize(3)
            (t,p)=ftb.exec_()
            if t:
                if   p==QCoreApplication.translate("addcodeline","Print"):      self.acl_print()
                elif p==QCoreApplication.translate("addcodeline","Clear"):      self.acl_clear()
                elif p==QCoreApplication.translate("addcodeline","Message"):    self.acl_message()
                elif p==QCoreApplication.translate("addcodeline","Logfile"):    self.acl_logfile()
                
    def acl(self,code):
        self.proglist.insertItem(self.proglist.currentRow()+1,code)
        self.proglist.setCurrentRow(self.proglist.currentRow()+1)
        self.progItemDoubleClicked()
        try:
            s=self.proglist.item(self.proglist.currentRow()).text().split()[1]
            if s=="RIF" or s=="TXT" or s=="FTD": self.lastIF=s
        except:
            pass
        
    def acl_counterClear(self):
        self.acl("CounterClear " + self.lastIF + " 1")
    
    def acl_waitForInputDig(self):
        self.acl("WaitInDig " + self.lastIF + " 1 Raising 0")
    
    def acl_ifInputDig(self):
        self.acl("IfInDig " + self.lastIF + " 1 True")

    def acl_waitForInput(self):
        self.acl("WaitIn " + self.lastIF + " 1 S > 0 0")
    
    def acl_ifInput(self):
        self.acl("IfIn " + self.lastIF + " 1 S  > 1")
    
    def acl_output(self):
        self.acl("Output " + self.lastIF + " 1 0")
        
    def acl_motor(self):
        self.acl("Motor " + self.lastIF + " 1 l 0")
    
    def acl_motorPulsewheel(self):
        self.acl("MotorP " + self.lastIF + " 1 1 2 l 7 10")

    def acl_motorEncoder(self):
        self.acl("MotorE " + "TXT" + " 1 1 l 512 72")
        
    def acl_motorEncoderSync(self):
        self.acl("MotorES " + "TXT"+ " 1 1 l 512 72")
    
    def acl_init(self):
        self.acl("Init integer 0")
    
    def acl_fromIn(self):
        self.acl("FromIn " + self.lastIF + " 1 S ?")
        
    def acl_fromKeypad(self):
        self.acl("FromKeypad integer 0 32768")
        
    def acl_fromDial(self):
        self.acl("FromDial integer -10 10 Set level")
    
    def acl_fromButtons(self):
        self.acl("FromButtons integer Choice1 Choice2")
    
    def acl_fromPoly(self):
        self.acl("FromPoly integer 1 1 1 1 1")
        
    def acl_queryVar(self):
        self.acl("QueryVar x")
    
    def acl_ifVar(self):
        self.acl("IfVar x == 0 y")
    
    def acl_calc(self):
        self.acl("Calc x 1 + 1")
    
    def acl_stop(self):
        self.acl("Stop")
    
    def acl_comment(self):
        self.acl("# ")
        
    def acl_tag(self):
        self.acl("Tag ")
        
    def acl_jump(self):
        self.acl("Jump ")
    
    def acl_loopTo(self):
        self.acl("LoopTo ? 2")
    
    def acl_delay(self):
        self.acl("Delay 1000")
    
    def acl_timerquery(self):
        self.acl("TimerQuery")
        
    def acl_timerclear(self):
        self.acl("TimerClear")
    
    def acl_iftimer(self):
        self.acl("IfTimer > 1000 ")
    
    def acl_interrupt(self):
        self.acl("Interrupt After 500 ?")
    
    def acl_queryNow(self):
        self.acl("QueryNow")
        
    def acl_call(self):
        self.acl("Call ")

    def acl_callext(self):
        self.acl("CallExt ")

    def acl_return(self):
        self.acl("Return")
        
    def acl_module(self):
        self.acl("Module ")        
        
    def acl_mend(self):
        self.acl("MEnd")
    
    def acl_print(self):
        self.acl("Print ")
    
    def acl_queryIn(self):
        self.acl("QueryIn " + self.lastIF + " 1 S")

    def acl_message(self):
        self.acl("Message  'Okay")
    
    def acl_logfile(self):
        ftb=TouchAuxMultibutton(QCoreApplication.translate("addcodeline","Logfile"), self.mainwindow)
        ftb.setButtons([ QCoreApplication.translate("addcodeline","Log On"),
                            QCoreApplication.translate("addcodeline","Log Off"),
                            QCoreApplication.translate("addcodeline","Log Clear")
                        ]
                        )
        ftb.setTextSize(3)
        ftb.setBtnTextSize(3)
        (t,p)=ftb.exec_()
        if t:
            if   p == QCoreApplication.translate("addcodeline","Log On"):   self.acl("Log 1")
            elif p == QCoreApplication.translate("addcodeline","Log Off"):  self.acl("Log 0")
            elif p == QCoreApplication.translate("addcodeline","Log Clear"):self.acl("Log Clear")
    
    def acl_clear(self):
        self.acl("Clear")
    
    def remCodeLine(self):
        row=self.proglist.currentRow()
        void=self.proglist.takeItem(row)
        if self.proglist.count()==0:
            self.proglist.addItem("# new")
            self.proglist.setCurrentRow(0)
        
        self.codeSaved=False
        
    def lineUp(self):
        row=self.proglist.currentRow()
        if row>0:
            i=self.proglist.takeItem(row)
            self.proglist.insertItem(row-1,i)
            self.proglist.setCurrentRow(row-1)
            self.codeSaved=False
    
    def lineDown(self):
        row=self.proglist.currentRow()
        if row<self.proglist.count()-1:
            i=self.proglist.takeItem(row)
            self.proglist.insertItem(row+1,i)
            self.proglist.setCurrentRow(row+1)
            self.codeSaved=False
#
# code line editing 
#
    def progItemDoubleClicked(self):
        crow=self.proglist.currentRow()
        itm=self.proglist.item(crow).text()
        stack=itm.split()
        
        vari=[]
        for i in range(0,self.proglist.count()):
            s=self.proglist.item(i).text().split()
            if s[0]=="Init" and not (s[1] in vari): vari.append(s[1])
        
        if   stack[0] == "CounterClear": itm=self.ecl_counterClear(itm)
        elif stack[0] == "Output":     itm=self.ecl_output(itm, vari)
        elif stack[0] == "Motor":      itm=self.ecl_motor(itm, vari)
        elif stack[0] == "MotorP":     itm=self.ecl_motorPulsewheel(itm, vari)
        elif stack[0] == "MotorE":     itm=self.ecl_motorEncoder(itm, vari)
        elif stack[0] == "MotorES":    itm=self.ecl_motorEncoderSync(itm, vari)
        elif stack[0] == "WaitInDig":  itm=self.ecl_waitForInputDig(itm, vari)
        elif stack[0] == "IfInDig":    itm=self.ecl_ifInputDig(itm, vari)
        elif stack[0] == "WaitIn":     itm=self.ecl_waitForInput(itm, vari)
        elif stack[0] == "IfIn":       itm=self.ecl_ifInput(itm, vari)
        elif stack[0] == "Init":       itm=self.ecl_init(itm, vari)
        elif stack[0] == "FromIn":     itm=self.ecl_fromIn(itm,vari) 
        elif stack[0] == "FromKeypad": itm=self.ecl_fromKeypad(itm, vari)
        elif stack[0] == "FromDial":   itm=self.ecl_fromDial(itm, vari)
        elif stack[0] == "FromButtons": itm=self.ecl_fromButtons(itm, vari)
        elif stack[0] == "FromPoly":   itm=self.ecl_fromPoly(itm, vari)
        elif stack[0] == "QueryVar":   itm=self.ecl_queryVar(itm, vari)
        elif stack[0] == "IfVar":      itm=self.ecl_ifVar(itm, vari)
        elif stack[0] == "Calc":       itm=self.ecl_calc(itm, vari)
        elif stack[0] == "#":          itm=self.ecl_comment(itm)
        elif stack[0] == "Tag":        itm=self.ecl_tag(itm)
        elif stack[0] == "Jump":       itm=self.ecl_jump(itm)
        elif stack[0] == "LoopTo":     itm=self.ecl_loopTo(itm, vari)
        elif stack[0] == "Delay":      itm=self.ecl_delay(itm, vari)
        elif stack[0] == "IfTimer":    itm=self.ecl_iftimer(itm, vari)
        elif stack[0] == "Interrupt":  itm=self.ecl_interrupt(itm, vari)
        elif stack[0] == "Stop":       itm=self.ecl_stop(itm)
        elif stack[0] == "Call":       itm=self.ecl_call(itm, vari)
        elif stack[0] == "CallExt":    itm=self.ecl_call(itm, vari)
        elif stack[0] == "Module":     itm=self.ecl_module(itm)
        elif stack[0] == "Print":      itm=self.ecl_print(itm)
        elif stack[0] == "QueryIn" or stack[0]=="Query":    itm=self.ecl_queryIn(itm)
        elif stack[0] == "Message":    itm=self.ecl_message(itm)
        elif stack[0] == "Request":    itm=self.ecl_request(itm)
        
        self.proglist.setCurrentRow(crow)
        self.proglist.item(crow).setText(itm)
        self.codeSaved=False
        
        try:
            s=self.proglist.item(self.proglist.currentRow()).text().split()[1]
            if s=="RIF" or s=="TXT" or s=="FTD": self.lastIF=s
        except:
            pass

    def ecl_counterClear(self, itm):
        return editCounterClear(itm, self.mainwindow).exec_()
    
    def ecl_output(self, itm, vari):
        return editOutput(itm,vari, self.mainwindow).exec_()
    
    def ecl_motor(self, itm, vari):
        return editMotor(itm,vari,self.mainwindow).exec_()
    
    def ecl_motorPulsewheel(self, itm, vari):
        return editMotorPulsewheel(itm,vari,self.mainwindow).exec_()
    
    def ecl_motorEncoder(self, itm, vari):
        return editMotorEncoder(itm, vari, self.mainwindow).exec_()
    
    def ecl_motorEncoderSync(self, itm, vari):
        return editMotorEncoderSync(itm,vari,self.mainwindow).exec_()
    
    def ecl_waitForInputDig(self, itm, vari):
        return editWaitForInputDig(itm,vari,self.mainwindow).exec_()
    
    def ecl_waitForInput(self, itm, vari):
        return editWaitForInput(itm,vari,self.mainwindow).exec_()
    
    def ecl_ifInputDig(self, itm, vari):
        tagteam=[]
        for i in range(0,self.proglist.count()):
            if self.proglist.item(i).text().split()[0]=="Tag": tagteam.append(self.proglist.item(i).text()[4:])
  
        if len(tagteam)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","IfInDig"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No Tags defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editIfInputDig(itm,tagteam,vari, self.mainwindow).exec_()
    
    def ecl_ifInput(self, itm, varlist):
        tagteam=[]
        for i in range(0,self.proglist.count()):
            if self.proglist.item(i).text().split()[0]=="Tag": tagteam.append(self.proglist.item(i).text()[4:])
  
        if len(tagteam)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","IfIn"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No Tags defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editIfInput(itm,tagteam, varlist, self.mainwindow).exec_()
    
    def ecl_init(self, itm, varlist):
        return editInit(itm, varlist, self.mainwindow).exec_()
    
    def ecl_fromIn(self, itm, varlist):
        if len(varlist)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","FromIn"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No variables defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editFromIn(itm, varlist, self.mainwindow).exec_()

    def ecl_fromPoly(self, itm, varlist):
        if len(varlist)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","FromPoly"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No variables defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editFromPoly(itm, varlist, self.mainwindow).exec_()

    def ecl_fromKeypad(self, itm, varlist):
        if len(varlist)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","FromKeypad"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No variables defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editFromKeypad(itm, varlist, self.mainwindow).exec_()        
    
    def ecl_fromDial(self, itm, varlist):
        if len(varlist)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","FromKeypad"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No variables defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editFromDial(itm, varlist, self.mainwindow).exec_()  

    def ecl_fromButtons(self, itm, varlist):
        if len(varlist)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","FromButtons"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No variables defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editFromButtons(itm, varlist, self.mainwindow).exec_()  

    def ecl_queryVar(self, itm, varlist):
        if len(varlist)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","QueryVar"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No variables defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        r=varlist[0]
        if itm.split()[1] in varlist:
            r=itm.split()[1]
        (s,r)=TouchAuxListRequester(QCoreApplication.translate("ecl","QueryVar"),QCoreApplication.translate("ecl","Variable"),varlist,r,"Okay", self.mainwindow).exec_()
    
        if s: return "QueryVar "+r
        return itm
    
    def ecl_ifVar(self, itm, varlist):
        tagteam=[]
        for i in range(0,self.proglist.count()):
            if self.proglist.item(i).text().split()[0]=="Tag": tagteam.append(self.proglist.item(i).text()[4:])
  
        if len(tagteam)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","IfVar"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No Tags defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm

        if len(varlist)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","IfVar"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No variables defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editIfVar(itm,tagteam, varlist, self.mainwindow).exec_()

    def ecl_calc(self, itm, varlist):
        if len(varlist)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","Calc"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No variables defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editCalc(itm, varlist, self.mainwindow).exec_()
        
    def ecl_comment(self, itm):
        return "# "+TouchAuxKeyboard(QCoreApplication.translate("ecl","Comment"),itm[2:],self.mainwindow).exec_()
    
    def ecl_tag(self, itm):
        return "Tag "+clean(TouchAuxKeyboard(QCoreApplication.translate("ecl","Tag"),itm[4:],self.mainwindow).exec_(),32)
    
    def ecl_jump(self, itm):
        itm=itm[5:]
        tagteam=[]
        for i in range(0,self.proglist.count()):
            if self.proglist.item(i).text().split()[0]=="Tag": tagteam.append(self.proglist.item(i).text()[4:])
  
        if len(tagteam)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","Jump"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No Tags defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return "Jump "+itm
        
        if not itm in tagteam: itm=tagteam[0]
        (s,r)=TouchAuxListRequester(QCoreApplication.translate("ecl","Jump"),QCoreApplication.translate("ecl","Target"),tagteam,itm,"Okay", self.mainwindow).exec_()
        
        if not s: return "Jump "+itm
        return "Jump "+r
        
    def ecl_loopTo(self, itm, vari):
        tagteam=[]
        for i in range(0,self.proglist.count()):
            if self.proglist.item(i).text().split()[0]=="Tag": tagteam.append(self.proglist.item(i).text()[4:])
  
        if len(tagteam)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","LoopTo"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No Tags defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editLoopTo(itm,tagteam,vari,self.mainwindow).exec_()
    
    def ecl_delay(self, itm, vari):
        if "R" in itm:
            try:
                num=-1*int(itm[6:-2])
                num=str(num)
            except:
                num=itm[6:-2]
        else:
            num=itm[6:]
            
        t=TouchAuxKeyboard(QCoreApplication.translate("ecl","Delay"),num,self.mainwindow).exec_()
        try:
            if int(t)<0:
                t=str(int(t)*-1)
                return "Delay "+str(int(t))+" R"
            else:
                return "Delay "+str(int(t))
        except:
            pass
        
        return "Delay "+itm[6:]
    
    def ecl_iftimer(self, itm, vari):
        tagteam=[]
        for i in range(0,self.proglist.count()):
            if self.proglist.item(i).text().split()[0]=="Tag": tagteam.append(self.proglist.item(i).text()[4:])
  
        if len(tagteam)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","IfTimer"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No Tags defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editIfTimer(itm,tagteam,vari,self.mainwindow).exec_()
    
    def ecl_interrupt(self, itm, vari):
        tagteam=[]
        for i in range(0,self.proglist.count()):
            if self.proglist.item(i).text().split()[0]=="Module":
                tagteam.append(self.proglist.item(i).text().split()[1])
  
        if len(tagteam)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","Interrupt"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No Modules defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        return editInterrupt(itm,tagteam,vari,self.mainwindow).exec_()
        
    def ecl_stop(self, itm):
        return itm
    
    def ecl_module(self, itm):
        return "Module "+clean(TouchAuxKeyboard(QCoreApplication.translate("ecl","Module"),itm[7:],self.mainwindow).exec_(),32)
    
    def ecl_call(self, itm, vari):
        tagteam=[]
        if itm.split()[0]=="CallExt":
            tagteam=os.listdir(moddir)
            tagteam.sort()
        else:    
            for i in range(0,self.proglist.count()):
                if self.proglist.item(i).text().split()[0]=="Module": tagteam.append(self.proglist.item(i).text()[7:])
  
        if len(tagteam)==0:
            t=TouchMessageBox(QCoreApplication.translate("ecl","Call"), self.mainwindow)
            t.setCancelButton()
            t.setText(QCoreApplication.translate("ecl","No Modules defined!"))
            t.setTextSize(2)
            t.setBtnTextSize(2)
            t.setPosButton(QCoreApplication.translate("ecl","Okay"))
            (v1,v2)=t.exec_()
            return itm
        
        try:
            if not itm.split()[1] in tagteam: itm=itm.split()[0] +" "+ tagteam[0] + " 1"
        except:
            itm=itm.split()[0]+" ? 1"
            
        return editCall(itm,tagteam,vari,self.mainwindow).exec_()

    def ecl_print(self, itm):
        return "Print "+TouchAuxKeyboard(QCoreApplication.translate("ecl","Print"),itm[6:],self.mainwindow).exec_()
        
    def ecl_queryIn(self, itm):
        return editQueryIn(itm, self.mainwindow).exec_()
    
    def ecl_message(self, itm):
        a=itm[8:].split("'")
        return "Message "+TouchAuxKeyboard(QCoreApplication.translate("ecl","Message"),a[0],self.mainwindow).exec_()+"'"+TouchAuxKeyboard(QCoreApplication.translate("ecl","BtnTxt"),a[1],self.mainwindow).exec_()
    
    def ecl_request(self, itm):
        return itm

#
# and the initial application launch
#

if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
