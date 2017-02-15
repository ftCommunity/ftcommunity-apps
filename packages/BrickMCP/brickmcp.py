#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys,os, shutil
import zipfile as z
from auxiliaries import *
from TouchStyle import *

hostdir = os.path.dirname(os.path.realpath(__file__)) + "/"
brickdir = hostdir + "../1f2d90a3-11e9-4a92-955a-73ffaec0fe71/user/"

# für die Entwicklungsumgebung PeH
if not os.path.exists(brickdir):
    brickdir = hostdir + "../../1f2d90a3-11e9-4a92-955a-73ffaec0fe71/user/"
    develop = True
else:
    develop = False
    

class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)

        translator = QTranslator()
        path = os.path.dirname(os.path.realpath(__file__))
        translator.load(QLocale.system(), os.path.join(path, "brickmcp_"))
        self.installTranslator(translator)


        # create the empty main window
        w = TouchWindow("BrickMCP")
        w.show()
        
        # hand over control to some TouchAux GUI items...
        res=True
        while res==True:
            res=self.muttley()        
        
        
        #self.exec_()        
        
    def muttley(self):  # as Dick Dastardly used to say: Muttley, do something!
        
        success=False
        
        something = TouchAuxMultibutton("BrickMCP",self.parent())
        
        if os.path.exists(brickdir+".mcplock"): 
        
            something.setText(QCoreApplication.translate("mcplocked","BrickMCP is locked on this device. Password required to:"))
            something.setButtons([ QCoreApplication.translate("mcplocked","Unlock"),
                                   "",
                                   QCoreApplication.translate("mcplocked","USB Import")
                                   ])
        
            (success,res)=something.exec_()
            if res==QCoreApplication.translate("mcplocked","Unlock"):
                self.unlock()
            elif res==QCoreApplication.translate("mcplocked","USB Import"):
                self.usb_import("locked")
        
        else: 
        
            something.setText(QCoreApplication.translate("unlocked","The Brickly Master Control Program:"))
            something.setButtons([ #QCoreApplication.translate("unlocked","Manage projects"),
                                   QCoreApplication.translate("unlocked","USB Import"),
                                   "",
                                   QCoreApplication.translate("unlocked","Lock BrickMCP")
                                   ])
        
            (success,res)=something.exec_()
            
            if res==QCoreApplication.translate("unlocked","Lock BrickMCP"):
                self.lock()
            elif res==QCoreApplication.translate("unlocked","USB Import"):
                self.usb_import("unlocked")
        return success
    
    def unlock(self):
        
        t=TouchAuxKeyboard("Key","",self.parent()).exec_()
        
        f=open(brickdir+".mcplock","r")
        if t==f.read():
            f.close()
            os.remove(brickdir+".mcplock")
        else:
            f.close()
    
    def lock(self):
        t=TouchAuxKeyboard("Key","",self.parent()).exec_()
        u=TouchAuxKeyboard("Confirm","",self.parent()).exec_()
        
        if t==u:
            f=open(brickdir+".mcplock","w")
            f.write(t)
            f.close()
        else:
            r=TouchAuxMessageBox(QCoreApplication.translate("lock","Error"), self.parent())
            r.setText(QCoreApplication.translate("lock","Keys did not match."))
            r.exec_()                     
        
      
    def usb_import(self, status:str):
        idir="/media/usb0/"
        if develop: idir="/home/apdent/Downloads/"
        
        liste=[]
        if os.path.exists(idir): l = os.listdir(idir)
        
        for m in l:
            #if os.path.isdir(idir+m) and not m[:1]==".": liste.append("<"+m+">")  # Directories
            if m[:8]=="Brickly-" and m[-4:]==".zip": liste.append(m[8:-4])
            
        liste.sort()
        
        if len(liste)==0:
            r=TouchAuxMessageBox(QCoreApplication.translate("usbimport","Info"), self.parent())
            r.setText(QCoreApplication.translate("usbimport","No Brickly projects found."))
            r.setPosButton(QCoreApplication.translate("usbimport","Okay"))
            r.exec_()
            return
          
        (success,result) = TouchAuxListRequester( QCoreApplication.translate("usbimport","Select"),
                                                  "",
                                                  liste, liste[0],
                                                  QCoreApplication.translate("usbimport","Okay"),
                                                  self.parent()).exec_()
        if success==False: return
        
        m=os.getcwd()
        os.chdir(brickdir)
        
        self.cleanup()
        
        filename=idir+"Brickly-"+result+".zip"
        print(filename)
        zf=z.ZipFile(filename,"r")
        if ".readme" in zf.namelist():
            zf.extract(".readme")
            t=open(".readme","r")
            if t.read()!="Brickly ZIP file created by BrickMCP":
                os.chdir(m)
                print("nab a")
                self.upload_error("nab")
                return
            t.close()
            os.remove(".readme")
        else: 
              os.chdir(m)
              print("nab b")
              self.upload_error("nab")
              return

        if ".xml" in zf.namelist():
            zf.extract(".xml")
        else: 
            os.chdir(m)
            self.upload_error("nab")
            return
        
        if ".py" in zf.namelist():
            zf.extract(".py")
        if ".mcpchecksum" in zf.namelist():
            zf.extract(".mcpchecksum")
        if ".bricklyversion" in zf.namelist():
            zf.extract(".bricklyversion")
        zf.close()
       
        # find an empty slot
        i=1
        while (os.path.isfile("brickly-"+str(i)+".py")) or (os.path.isfile("brickly-"+str(i)+".xml")):
          i=i+1
        
        # calculate checksum on upladed brickly files
        s1=0
        if os.path.isfile(".xml"):
            s1=os.path.getsize(".xml") % 171072
        if os.path.isfile(".py"):
            s1=s1+os.path.getsize(".py") % 171072
        print("s1",s1)
        # get checksum from zip file
        s0=0
        if os.path.exists(".mcpchecksum"):
            fi=open(".mcpchecksum","r")
            r =fi.readline()
            s0=int(r)
            fi.close()
        print("s0",s0)
        # get brickly version from zip file
        ulvers=""
        if os.path.exists(".bricklyversion"):
            fi=open(".bricklyversion","r")
            ulvers = fi.readline()
            fi.close()    
        
        
        # get brickly version from TXT
        vers="n/a"
        if os.path.exists("../manifest"):
            fi=open("../manifest","r")
            r =fi.readline()
            while r!="":
                if "version" in r: vers = r
                r=fi.readline()
            fi.close()
        
        # install uploaded brickly project
        if (ulvers==vers) and (s0==s1):
            if os.path.isfile(".xml"):
                shutil.copyfile(".xml", "brickly-"+str(i)+".xml")
            if os.path.isfile(".py"):
                shutil.copyfile(".py", "brickly-"+str(i)+".py")           
        elif (s0==0):
            if os.path.isfile(".xml"):
                shutil.copyfile(".xml", "brickly-"+str(i)+".xml")
            if os.path.isfile(".py"):
                shutil.copyfile(".py", "brickly-"+str(i)+".py")
            self.upload_error("cnf")
        elif (s0!=s1):
            self.upload_error("cnm")
        elif (ulvers!=vers) and (s0==s1):
            if os.path.isfile(".xml"):
                shutil.copyfile(".xml", "brickly-"+str(i)+".xml")
            if os.path.isfile(".py"):
                shutil.copyfile(".py", "brickly-"+str(i)+".py")
            self.upload_error("vnm")
            
        # remove all extracted files

        self.cleanup()     
        
        # **********************************************************************************************************************
            
        # altes current dir wieder setzen
        os.chdir(m)
    
    def upload_error(self, error:str):
        
        m=TouchAuxMessageBox("Error",self.parent())
        
        if error=="cnm":
            m.setText(QCoreApplication.translate("ulerror","Chechsum does not match. Project was not added."))
        elif error=="cnf":
            m.setText(QCoreApplication.translate("ulerror","Chechsum does not match. Project was added anyway, but may be corrupt. Please check carefully."))
        elif error=="vnm":
            m.setText(QCoreApplication.translate("ulerror","Brickly version does not match. Project was added anyway, but may be corrupt. Please check carefully."))
        elif error=="nab":
            m.setText(QCoreApplication.translate("ulerror","File was not a Brickly project!"))
        else:
            m.setText(QCoreApplication.translate("ulerror","Error during upload. Workspace may be corrupt!"))
        
        m.setPosButton(QCoreApplication.translate("ulerror","Okay"))
        m.exec_()
    
    def cleanup(self):    
        if os.path.isfile(".xml"):
            os.remove(".xml")
        if os.path.isfile(".py"):
            os.remove(".py")
        if os.path.isfile(".readme"):
            os.remove(".readme")
        if os.path.isfile(".bricklyversion"):
            os.remove(".bricklyversion")
        if os.path.isfile(".mcpchecksum"):
            os.remove(".mcpchecksum")
            
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)