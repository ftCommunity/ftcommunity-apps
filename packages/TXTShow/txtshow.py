#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import sys, time, os
from TouchStyle import *
from threading import Timer
from auxiliaries import *

try:
    if TouchStyle_version<1.2:
        print("TouchStyle >= v1.2 not found!")
except:
    print("TouchStyle_version not found!")
    TouchStyle_version=0
    
local = os.path.dirname(os.path.realpath(__file__)) + "/"
icondir = local + "icons/"
picsdir = local + "pics/"
ovldir = local + "overlay/"

camera_present=TouchAuxFTCamIsPresent()
        
class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)
        
        translator = QTranslator()
        path = os.path.dirname(os.path.realpath(__file__))
        translator.load(QLocale.system(), os.path.join(path, "txtshow_"))
        self.installTranslator(translator)
        
        
        self.block=False
        self.maxpic=0
        self.maxdir=0
        self.currpic=0
        self.currdir=""
        self.autorotate=True
        self.autoscale=True
        self.allowZoom=False
        self.timerdelay=3000
        
        self.window = TouchWindow("TXTShow")
        self.setupLayout()
        
        self.timer =QTimer(self)
        self.timer.timeout.connect(self.on_timer)
        
        self.scan_directories()
        
        # read preferences here
        
        if os.path.isfile(local + ".txtshowconf"):
            with open(local+".txtshowconf","r") as f:
                r=f.readline()
                while r!="":
                    if "album=" in r: self.currdir=r[r.index("album=")+6 : -1]
                    try:
                        if "delay=" in r: self.timerdelay=int(r[r.index("delay=")+6 : -1])
                    except:
                        self.timerdelay=int(3000)
                    r=f.readline()
        # prefs done
        
        self.scan_images()
        
        self.window.show()
        
        # *********** check for camera presence **************
        self.set_camera()

        
        self.timer.start(self.timerdelay)
        self.currpic=-1
        self.on_timer() # erstes Bild laden!
         
        self.exec_()     
        
        # write preferences here
        
        self.saveprefs()
#
#*****************************
#

    def on_timer(self):
        self.currpic=self.currpic+1
        if self.currpic>=len(self.picstack): self.currpic=0        
        self.scan_images()
        if self.currpic>=len(self.picstack): self.currpic=0
        
        self.offset_x=0
        self.offset_y=0
        
        self.currpixmap=QPixmap(picsdir+self.currdir+"/"+self.picstack[self.currpic])
        
        if (self.currpixmap.size().width()>self.currpixmap.size().height()) and self.autorotate:
            self.currpixmap = self.currpixmap.transformed(QTransform().rotate(270))
        
        if self.currpixmap.width()>240 or self.currpixmap.height()>320:
            self.allowZoom=True
        else:
            self.allowZoom=False
        
        if self.autoscale or (not self.allowZoom):
            self.layer_picture.setPixmap(self.currpixmap.scaled(QSize(240, 320), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.paint_zoom()
        self.updatelayerimage()
        
    def paint_zoom(self):
        if not self.allowZoom: return()
        base_x = (self.currpixmap.width()/2)-120
        base_y = (self.currpixmap.height()/2)-160
        target=QPixmap(240,320)
        p = QPainter()
        p.begin(target)
        p.drawPixmap(0,0,240,320,self.currpixmap,base_x+self.offset_x,base_y+self.offset_y,240,320)
        p.end()
        self.layer_picture.setPixmap(target)
    
    def set_camera(self):
        if camera_present:
          self.fw_camera.changePixmap(QPixmap(icondir+"camera-web.png"))
          self.sw_camera.changePixmap(QPixmap(icondir+"camera-web.png"))
          self.tw_camera.changePixmap(QPixmap(icondir+"camera-web.png"))
        else:
          self.fw_camera.changePixmap(QPixmap(icondir+"camera-web-disabled.png"))
          self.sw_camera.changePixmap(QPixmap(icondir+"camera-web-disabled.png"))
          self.tw_camera.changePixmap(QPixmap(icondir+"camera-web-disabled.png"))
    
    def scan_directories(self, hidden=False):
        dirs = os.listdir(picsdir)
        
        self.dirstack=list()
        
        for data in dirs:
            if os.path.isdir(picsdir + data):
                if hidden: 
                  if os.path.isfile(picsdir + data + "/.hidden"):
                    self.dirstack.append(data)   
                else:
                  if not os.path.isfile(picsdir + data + "/.hidden"):
                     self.dirstack.append(data)
                     
        self.dirstack.sort()
    
        
    def foto(self):
        if camera_present:      
            msg=TouchAuxFTCamPhotoRequester(QCoreApplication.translate("context","Smile..."),960,720, QCoreApplication.translate("context","Snap"))
            img=msg.exec_()
            if img != None: void=img.save(picsdir+self.currdir+"/"+time.strftime("%y%m%d%H%M%S")+".png","PNG",80)


    def scan_images(self):
        
        self.picstack=list()
        
        if self.currdir in self.dirstack:
            self.picstack=os.listdir(picsdir+self.currdir)
            self.picstack.sort()
    
        elif len(self.dirstack)>0:
            self.currdir=self.dirstack[0]
            self.picstack=os.listdir(picsdir+self.currdir)
            self.picstack.sort()
            self.currpic=-1
        
        
        if len(self.picstack)==0:
            self.picstack=list()
            if self.currdir != "":
              self.picstack.append("../fail.png")
            else: self.picstack.append("fail.png")
            self.currpic=-1
        
        self.updatelayerimage()
            
    def switch(self):
        self.currpic=self.currpic-1
        self.on_timer()
        self.fw_dial.setValue(self.currpic+1)
        self.updatelayerimage()
        
        if self.myStack.currentIndex()==0:
          self.myStack.setCurrentIndex(1)
        elif self.myStack.currentIndex()==1:
          self.myStack.setCurrentIndex(2)
        else:
          self.myStack.setCurrentIndex(0)
    
    def updatelayerimage(self):
        self.tw_album.setText(self.currdir)

        if self.picstack[0]=="../fail.png":
            self.fw_dial.setRange(0,0)
            self.fw_dial.setValue(0)
            self.sw_image.setPixmap(QPixmap())
        else:
            self.fw_dial.setRange(1,len(self.picstack))
            self.fw_dial.setValue(self.currpic+1)
            if self.layer_picture.pixmap():
                self.sw_image.setPixmap(self.layer_picture.pixmap().scaled(QSize(232,194), Qt.KeepAspectRatio, Qt.SmoothTransformation).transformed(QTransform().rotate(90)))

            
        
    def switchback(self):
        self.currpic=self.currpic-1
        self.on_timer()
        self.fw_dial.setValue(self.currpic+1)
        self.updatelayerimage()     
        if self.myStack.currentIndex()==2:
          self.myStack.setCurrentIndex(1)
        elif self.myStack.currentIndex()==1:
          self.myStack.setCurrentIndex(0)
        else:
          self.myStack.setCurrentIndex(2)
    
        
    def setupLayout(self):
        
        self.myStack = QStackedWidget()

        self.myStackLayout1 = QWidget() # Layout 1 -> vor- und zurückblättern
        self.myStackLayout2 = QWidget() # Layout 2 -> Bilder verschieben und löschen
        self.myStackLayout3 = QWidget() # Layout 3 -> Alben(Ordner) verwalten
        
        self.FirstWidget()
        self.SecondWidget()
        self.ThirdWidget()
        
        self.myStack.addWidget(self.myStackLayout1)
        self.myStack.addWidget(self.myStackLayout2)
        self.myStack.addWidget(self.myStackLayout3)
        
        self.myStack.setCurrentIndex(0)
        
        self.window.setCentralWidget(self.myStack)

        self.layer_black = QLabel(self.window)
        self.layer_black.setGeometry(0, 0, 240, 320)
        self.layer_black.setPixmap(QPixmap(ovldir+"ovl_black.png"))

        self.layer_picture = QLabel(self.window)
        self.layer_picture.setGeometry(0, 0, 240, 320)
        self.layer_picture.mousePressEvent=self.on_picture_clicked
        self.layer_picture.setAlignment(Qt.AlignCenter)
        
        self.layer_overlay = QLabel(self.window)
        self.layer_overlay.setGeometry(0, 0, 240, 320)
        self.layer_overlay.setPixmap(QPixmap(ovldir+"ovl_pause.png"))
        self.layer_overlay.mousePressEvent=self.on_ovl_clicked

        self.layer_overlay.hide()
        
    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            if self.autoscale: self.layer_overlay.setPixmap(QPixmap(ovldir+"ovl_play.png"))
            else: self.layer_overlay.setPixmap(QPixmap(ovldir+"ovl_play_zoom.png"))
        else:
            self.timer.start(self.timerdelay)
            if self.autoscale: self.layer_overlay.setPixmap(QPixmap(ovldir+"ovl_pause.png"))
            else: self.layer_overlay.setPixmap(QPixmap(ovldir+"ovl_pause_zoom.png"))
    
    def toggle_autoscale(self):
        self.autoscale=not self.autoscale
        #if not self.allowZoom: self.autoscale=True
        if self.timer.isActive():
            if self.autoscale: self.layer_overlay.setPixmap(QPixmap(ovldir+"ovl_pause.png"))
            else: self.layer_overlay.setPixmap(QPixmap(ovldir+"ovl_pause_zoom.png"))
        else:
            if self.autoscale: self.layer_overlay.setPixmap(QPixmap(ovldir+"ovl_play.png"))
            else: self.layer_overlay.setPixmap(QPixmap(ovldir+"ovl_play_zoom.png"))
            
    def on_picture_clicked(self,event):
        x = event.pos().x()
        y = event.pos().y()
        
        if x<48: column="left"
        elif x>191: column="right"
        elif x>95 and x<145: column="middle"
        else: column="empty"
        
        if y<48: row="top"
        elif y>272: row="bottom"
        elif y>135 and y<185: row="middle"
        else: row="empty"
        
        if self.autoscale:
            #if row=="top" and column=="right": self.program_exit()
            if row=="middle":
                tx = self.timer.isActive()
                if column=="left":
                    self.timer.stop()
                    self.currpic=self.currpic-2
                    if self.currpic<-1: self.currpic=len(self.picstack)-2
                    self.on_timer()
                    if tx: self.timer.start(self.timerdelay)
                elif column=="right":
                    self.timer.stop()
                    self.on_timer()
                    if tx: self.timer.start(self.timerdelay)
                else: self.layer_overlay.show()
            else: self.layer_overlay.show()
        else: self.layer_overlay.show()
    

    
    def on_ovl_clicked(self,event):
        
        x = event.pos().x()
        y = event.pos().y()
        
        if x<48: column="left"
        elif x>191: column="right"
        elif x>95 and x<145: column="middle"
        else: column="empty"
        
        if y<48: row="top"
        elif y>272: row="bottom"
        elif y>135 and y<185: row="middle"
        else: row="empty"
        
        if self.autoscale:  #bei automatischer größenanpassung
            if row=="top" and column=="right": self.program_exit()
            elif row=="top" and column=="middle": row="empty"
            elif row=="top" and column=="left": self.layer_hide()
            elif row=="bottom" and column=="right": self.toggle_timer()
            elif row=="bottom" and column=="left":
                self.toggle_autoscale()
                self.currpic=self.currpic-1
                self.on_timer()
            elif row=="bottom" and column=="middle": row="empty"
                
            if row=="middle":
                tx = self.timer.isActive()
                if column=="left":
                    self.timer.stop()
                    self.currpic=self.currpic-2
                    if self.currpic<-1: self.currpic=len(self.picstack)-2
                    self.on_timer()
                    if tx: self.timer.start(self.timerdelay)
                elif column=="right":
                    self.timer.stop()
                    self.on_timer()
                    if tx: self.timer.start(self.timerdelay)
                else: column="empty"
        
        else:  # bei 1:1 (zoom) -> anderes overlay
            if row=="bottom" and column=="right": self.toggle_timer()
            elif row=="bottom" and column=="left":
                self.toggle_autoscale()
                self.currpic=self.currpic-1
                self.on_timer()
            elif row=="middle" and column=="middle":
                row="empty"
            elif row=="middle" and column=="left":
                self.offset_x=max(0-(self.currpixmap.width()/2)+120,self.offset_x-64)
                self.paint_zoom()
            elif row=="middle" and column=="right":
                self.offset_x=min((self.currpixmap.width()/2)-120,self.offset_x+64)
                self.paint_zoom()
            elif row=="top" and column=="middle":
                self.offset_y=max(0-(self.currpixmap.height()/2)+160,self.offset_y-64)
                self.paint_zoom()
            elif row=="bottom" and column=="middle":
                self.offset_y=min((self.currpixmap.height()/2)-160,self.offset_y+64)
                self.paint_zoom()
            elif row=="top" and column=="right":
                row="empty"
            elif row=="top" and column=="left":
                row="empty"
                
        if row=="empty" or column=="empty": self.layer_overlay.hide()
        
    
    def layer_hide(self):
        self.remembertimer=self.timer.isActive()
        self.timer.stop()
        self.scan_directories()
        self.scan_images()
        self.set_camera()
        self.layer_black.hide()
        self.layer_picture.hide()
        self.layer_overlay.hide()
        
    def layer_show(self):
        if self.timer.isActive() or self.remembertimer: 
            self.timer.stop()
            self.timer.start(self.timerdelay)
        self.layer_black.show()
        self.layer_picture.show()
        self.layer_overlay.hide()
        self.currpic=self.currpic-1
        self.on_timer() # --> load current picture here
    
    def program_exit(self):
        self.saveprefs()
        exit()
        
    def saveprefs(self):
        with open(local+".txtshowconf","w", encoding="utf-8") as f:
            f.write("album="+self.currdir+"\n")
            f.write("delay="+str(int(self.timerdelay))+"\n")
        
    def set_delay(self):
        msg=TouchAuxRequestInteger(QCoreApplication.translate("context","Delay"),QCoreApplication.translate("context","Set slide show delay:"),self.timerdelay/1000,2,30,QCoreApplication.translate("context","Set"))
        (void,tim)=msg.exec_()
        self.timerdelay=tim*1000
    
    def FirstWidget(self):
        layout = QVBoxLayout()
        

        self.fw_dial = QDial()
        self.fw_dial.setNotchesVisible(True)
        self.fw_dial.setRange(1,10)        
        self.fw_dial.valueChanged.connect(self.fw_show_value)
        layout.addWidget(self.fw_dial)
        
        midbox = QHBoxLayout()
  
        #midbox.addStretch()
        self.fw_bckbutt = PicButton(QPixmap(icondir+"arrow-left.png"))
        self.fw_bckbutt.setMinimumHeight(50)
        self.fw_bckbutt.clicked.connect(self.fw_bckbutt_clicked)
        midbox.addWidget(self.fw_bckbutt)
        
        midbox.addStretch()
        self.fw_current = QLabel()
        self.fw_current.setAlignment(Qt.AlignCenter)
        midbox.addWidget(self.fw_current)
        midbox.addStretch()
        
        self.fw_fwdbutt = PicButton(QPixmap(icondir+"arrow-right.png"))
        self.fw_fwdbutt.clicked.connect(self.fw_fwdbutt_clicked)
        midbox.addWidget(self.fw_fwdbutt)
                
        layout.addLayout(midbox)
        
        bottbox = QHBoxLayout()
        
        self.fw_chrono = PicButton(QPixmap(icondir+"chronometer.png"))
        self.fw_chrono.clicked.connect(self.set_delay)
        bottbox.addWidget(self.fw_chrono)
        bottbox.addStretch()
        
        
        fw_preturn = PicButton(QPixmap(icondir+"key-enter.png"))
        fw_preturn.clicked.connect(self.layer_show)
        bottbox.addWidget(fw_preturn)
        
        self.fw_camera = PicButton(QPixmap(icondir+"camera-web-disabled.png"))
        self.fw_camera.clicked.connect(self.foto)
        bottbox.addWidget(self.fw_camera)
        bottbox.addStretch()
        
        self.fw_pfwd = PicButton(QPixmap(icondir+"go-next.png"))
        bottbox.addWidget(self.fw_pfwd)
        
        layout.addLayout(bottbox)
                
        self.myStackLayout1.setLayout(layout)
        
        self.fw_pfwd.clicked.connect(self.switch)
        
        self.fw_dial.setValue(5)
    
    def fw_bckbutt_clicked(self):
        self.fw_dial.setValue(max(1,self.fw_dial.value()-1))
    
    def fw_fwdbutt_clicked(self):
        self.fw_dial.setValue(min(self.fw_dial.value()+1,self.fw_dial.maximum()))

    def fw_show_value(self):
        self.fw_current.setText(str(self.fw_dial.value()))
        self.currpic=self.fw_dial.value()-1
        
    def sw_on_clicked_del(self):
        
        if self.picstack[self.currpic]=="../fail.png":
            msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
            msg.setText("'"+self.currdir+"' "+QCoreApplication.translate("context","is already empty."))
            msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
            msg.setPosButton(QCoreApplication.translate("context","Okay"))
            (void,void)=msg.exec_()
            return
      
        msg=TouchAuxMessageBox(QCoreApplication.translate("context","Warning"), self.parent())
        msg.setText(QCoreApplication.translate("context","Permanently delete image ")+"'"+self.picstack[self.currpic]+"' "+QCoreApplication.translate("context","from album")+" '"+self.currdir+"'?")
        msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
        msg.setPosButton(QCoreApplication.translate("context","Yes"))
        msg.setNegButton(QCoreApplication.translate("context","Cancel"))
        msg.buttonsVertical(False)
        (success,res)=msg.exec_()
        
        if res==QCoreApplication.translate("context","Yes"):
          cm="rm "+picsdir+self.currdir+"/"+self.picstack[self.currpic]
          void=run_program(cm)          
          self.scan_directories()
          self.scan_images()
          self.currpic=self.currpic-1
          self.on_timer()
          
    def sw_on_clicked_copy(self):
        if self.picstack[self.currpic]=="../fail.png":
            msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
            msg.setText("'"+self.currdir+"' "+QCoreApplication.translate("context","is empty. Nothing to copy."))
            msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
            msg.setPosButton(QCoreApplication.translate("context","Okay"))
            (void,void)=msg.exec_()
            return
          
        req=TouchAuxListRequester(QCoreApplication.translate("context","Copy"),"'"+self.picstack[self.currpic]+"' "+QCoreApplication.translate("context","to album:"),self.dirstack,self.currdir,QCoreApplication.translate("context","Copy"))  
        (success, destdir)=req.exec_()
   
        if success:
            if not(self.currdir==destdir):
                if os.path.isfile(picsdir+destdir+"/"+self.picstack[self.currpic]):
                    msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                    msg.setText(QCoreApplication.translate("context","Image") + " '"+self.picstack[self.currpic]+"' "+QCoreApplication.translate("context","already exists in album") + " '"+destdir+"'!")
                    msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                    msg.setPosButton(QCoreApplication.translate("context","Okay"))
                    (void,void)=msg.exec_()
                else:
                    cm="cp "+picsdir+self.currdir+"/"+self.picstack[self.currpic]+" "+picsdir+destdir+"/"
                    void=run_program(cm)
            else:
                msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                msg.setText(QCoreApplication.translate("context","Unable to copy image")+" '"+self.picstack[self.currpic]+"' "+QCoreApplication.translate("context","to album")+" '"+destdir+"'!")
                msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                msg.setPosButton(QCoreApplication.translate("context","Okay"))
                (void,void)=msg.exec_()
    
    def sw_on_clicked_move(self):
        if self.picstack[self.currpic]=="../fail.png":
            msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
            msg.setText("'"+self.currdir+"' "+QCoreApplication.translate("context","is empty. Nothing to move."))
            msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
            msg.setPosButton(QCoreApplication.translate("context","Okay"))
            (void,void)=msg.exec_()
            return
          
        req=TouchAuxListRequester(QCoreApplication.translate("context","Move"),"'"+self.picstack[self.currpic]+"' "+QCoreApplication.translate("context","to album:"),self.dirstack,self.currdir,QCoreApplication.translate("context","Move"))  
        (success, destdir)=req.exec_()
       
        if success:
            if not(self.currdir==destdir):
                if os.path.isfile(picsdir+destdir+"/"+self.picstack[self.currpic]):
                    msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                    msg.setText(QCoreApplication.translate("context","Image")+" '"+self.picstack[self.currpic]+"' "+QCoreApplication.translate("context","already exists in album")+" '"+destdir+"'!")
                    msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                    msg.setPosButton(QCoreApplication.translate("context","Okay"))
                    (void,void)=msg.exec_()
                else:
                    cm="mv "+picsdir+self.currdir+"/"+self.picstack[self.currpic]+" "+picsdir+destdir+"/"
                    void=run_program(cm)
                    self.scan_directories()
                    self.scan_images()
                    self.currpic=self.currpic-1
                    self.on_timer()
            else:
                msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                msg.setText(QCoreApplication.translate("context","Unable to move image")+" '"+self.picstack[self.currpic]+"' "+QCoreApplication.translate("context","to album")+" '"+destdir+"'!")
                msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                msg.setPosButton(QCoreApplication.translate("context","Okay"))
                (void,void)=msg.exec_() 
        
    def sw_on_clicked_renImage(self):
        if self.picstack[self.currpic]=="../fail.png":
            msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
            msg.setText("'"+self.currdir+"' "+QCoreApplication.translate("context","is empty. Nothing to rename."))
            msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
            msg.setPosButton(QCoreApplication.translate("context","Okay"))
            (void,void)=msg.exec_()
            return
        (base,extention)=os.path.splitext(self.picstack[self.currpic])
        msg=TouchAuxRequestText(QCoreApplication.translate("context","Rename"), QCoreApplication.translate("context","Please enter new name for")+" '"+self.picstack[self.currpic]+"':", base, QCoreApplication.translate("context","Rename"), self.parent())
        (success,newname)=msg.exec_()
        if success and not newname==base:
            newname=self.clean(newname,12)
            os.rename(picsdir+self.currdir+"/"+self.picstack[self.currpic], picsdir+self.currdir+"/"+newname+extention)
            self.scan_images()
            self.currpic=self.picstack.index(newname+extention)
            
    def SecondWidget(self):
        layout = QVBoxLayout()
        
        self.sw_image=QLabel()
        self.sw_image.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sw_image)
        
        midbox = QHBoxLayout()
        midbox.addStretch()
        
        self.sw_copy = PicButton(QPixmap(icondir+"edit-copy.png"))
        self.sw_copy.clicked.connect(self.sw_on_clicked_copy)
        midbox.addWidget(self.sw_copy)
        
        midbox.addStretch()
        
        self.sw_move = PicButton(QPixmap(icondir+"edit-cut.png"))
        self.sw_move.clicked.connect(self.sw_on_clicked_move)
        midbox.addWidget(self.sw_move)
        
        midbox.addStretch()
        
        self.sw_renImage = PicButton(QPixmap(icondir+"edit-rename.png"))
        self.sw_renImage.clicked.connect(self.sw_on_clicked_renImage)
        midbox.addWidget(self.sw_renImage)
        
        midbox.addStretch()
        
        self.sw_delete = PicButton(QPixmap(icondir+"trash-empty.png"))
        self.sw_delete.clicked.connect(self.sw_on_clicked_del)
        midbox.addWidget(self.sw_delete)
        midbox.addStretch()
        
        layout.addLayout(midbox)
        
        
        bottbox = QHBoxLayout()
        
        self.sw_pback = PicButton(QPixmap(icondir+"go-previous.png"))
        
        bottbox.addWidget(self.sw_pback)
        bottbox.addStretch()
        
        
        sw_preturn = PicButton(QPixmap(icondir+"key-enter.png")) 
        sw_preturn.clicked.connect(self.layer_show)
        bottbox.addWidget(sw_preturn)
        
        self.sw_camera = PicButton(QPixmap(icondir+"camera-web-disabled.png")) 
        self.sw_camera.clicked.connect(self.foto)        
        bottbox.addWidget(self.sw_camera)
        bottbox.addStretch()
        
        self.sw_pfwd = PicButton(QPixmap(icondir+"go-next.png"))
        bottbox.addWidget(self.sw_pfwd)
        self.sw_pfwd.clicked.connect(self.switch)
        self.sw_pback.clicked.connect(self.switchback)
        
        layout.addLayout(bottbox)
        
        self.myStackLayout2.setLayout(layout)

    
    def selectalbum(self,click):
      req=TouchAuxListRequester(QCoreApplication.translate("context","Select"),QCoreApplication.translate("context","Album to open:"),self.dirstack,self.currdir,QCoreApplication.translate("context","Open"))  
      (void, self.currdir)=req.exec_()
      self.tw_album.setText(self.currdir)
      self.scan_images()
      self.currpic=-1
      self.on_timer()
          
    def clean(self,newdir,maxlen):
        res=""
        valid="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_-."
        for ch in newdir:
            if ch in valid: res=res+ch
        return res[:maxlen]
      
    def addAlbum(self):
        msg=TouchAuxRequestText(QCoreApplication.translate("context","New"), QCoreApplication.translate("context","Album to be created:"), QCoreApplication.translate("context","MyAlbum"), QCoreApplication.translate("context","Create"), self.parent())
        (success,newdir)=msg.exec_()
        if success:
            newdir=self.clean(newdir,12)
            if newdir in self.dirstack:
                msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                msg.setText("'"+newdir+"' "+QCoreApplication.translate("context","already exists! Could not create."))
                msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                msg.setPosButton(QCoreApplication.translate("context","Okay"))
                (void,void)=msg.exec_()
            else:
                try:
                    os.mkdir(picsdir + newdir)
                    self.currdir=newdir
                except:
                    msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                    msg.setText("'"+newdir+"' "+QCoreApplication.translate("context","could not be created."))
                    msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                    msg.setPosButton(QCoreApplication.translate("context","Okay"))
                    (void,void)=msg.exec_()
                
                self.scan_directories()
                self.scan_images()
                self.on_timer()

    def delAlbum(self):
        if len(self.dirstack)>1:
            msg=TouchAuxMessageBox(QCoreApplication.translate("context","Warning"), self.parent())
            
            if self.picstack[0]=="../fail.png": n=0
            else: n=len(self.picstack)
            
            msg.setText(QCoreApplication.translate("context","Really permanently delete the album")+" '"+self.currdir+"' "+QCoreApplication.translate("context","with")+" "+str(n)+" "+QCoreApplication.translate("context","images?"))
            msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
            msg.setPosButton(QCoreApplication.translate("context","Yes"))
            msg.setNegButton(QCoreApplication.translate("context","Cancel"))
            msg.buttonsVertical(False)
            (void,res)=msg.exec_()
            if res==QCoreApplication.translate("context","Yes"):
              cm="rm -r "+picsdir+self.currdir+"/"
              void=run_program(cm)
              self.scan_directories()
              self.scan_images()
              self.on_timer()
        else:
            msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
            msg.setText("'"+self.currdir+"' "+QCoreApplication.translate("context","is the last album and can not be deleted."))
            msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
            msg.setPosButton(QCoreApplication.translate("context","Okay"))
            (void,void)=msg.exec_()
          
      
    def renAlbum(self):
        msg=TouchAuxRequestText(QCoreApplication.translate("context","Rename"), QCoreApplication.translate("context","Please enter new name for")+" '"+self.currdir+"':", self.currdir, QCoreApplication.translate("context","Rename"), self.parent())
        (success,newdir)=msg.exec_()
        if success:
            newdir=self.clean(newdir,12)
            if newdir in self.dirstack:
                msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                msg.setText("'"+newdir+"' "+QCoreApplication.translate("context","already exists! Could not rename."))
                msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                msg.setPosButton(QCoreApplication.translate("context","Okay"))
                (void,void)=msg.exec_()
            else:
                try:
                    os.rename(picsdir+self.currdir, picsdir + newdir)
                    self.currdir=newdir
                except:
                    msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                    msg.setText("'"+self.currdir+"' "+QCoreApplication.translate("context","could not be renamed."))
                    msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                    msg.setPosButton(QCoreApplication.translate("context","Okay"))
                    (void,void)=msg.exec_()
                
                self.scan_directories()
                self.scan_images()
                self.on_timer()
    
    def ThirdWidget(self):
        
        layout = QVBoxLayout()
     
        labox=QHBoxLayout()
        lab=QLabel()
        lab.setText(QCoreApplication.translate("context","Album:"))
        labox.addWidget(lab)
        labox.addStretch()
        
        self.tw_changeAlbum = PicButton(QPixmap(icondir+"folder-image-people.png"))
        self.tw_changeAlbum.clicked.connect(self.selectalbum)
        labox.addWidget(self.tw_changeAlbum)
        layout.addLayout(labox)
        
        self.tw_album = QLineEdit()
        self.tw_album.setReadOnly(True)
        self.tw_album.mousePressEvent=self.selectalbum
        self.tw_album.setText(self.currdir)

        layout.addWidget(self.tw_album)
        layout.addStretch()        
        
        midbox=QHBoxLayout()
        
        midbox.addStretch()
        
        tw_addAlbum = PicButton(QPixmap(icondir+"folder-add.png"))
        tw_addAlbum.clicked.connect(self.addAlbum)
        midbox.addWidget(tw_addAlbum)

        midbox.addStretch()
        
        tw_delAlbum = PicButton(QPixmap(icondir+"folder-del.png"))
        tw_delAlbum.clicked.connect(self.delAlbum)
        midbox.addWidget(tw_delAlbum)
        
        midbox.addStretch()
        
        tw_renAlbum = PicButton(QPixmap(icondir+"edit-rename.png"))
        tw_renAlbum.clicked.connect(self.renAlbum)
        midbox.addWidget(tw_renAlbum)
        
        midbox.addStretch()
       
        layout.addLayout(midbox)
        layout.addStretch()
        
        bottbox = QHBoxLayout()
        
        self.tw_pback = PicButton(QPixmap(icondir+"go-previous.png"))
        self.tw_pback.clicked.connect(self.switchback)
        bottbox.addWidget(self.tw_pback)
        bottbox.addStretch()
        
        
        tw_preturn = PicButton(QPixmap(icondir+"key-enter.png")) 
        tw_preturn.clicked.connect(self.layer_show)
        bottbox.addWidget(tw_preturn)
        
        self.tw_camera = PicButton(QPixmap(icondir+"camera-web-disabled.png"))
        self.tw_camera.clicked.connect(self.foto)
        bottbox.addWidget(self.tw_camera)
        bottbox.addStretch()
        
        self.tw_wizard = PicButton(QPixmap(icondir+"tools-wizard.png"))
        bottbox.addWidget(self.tw_wizard)
        self.tw_wizard.clicked.connect(self.on_wizard_clicked)
        
        layout.addLayout(bottbox)
        
        self.myStackLayout3.setLayout(layout)
   
    def on_wizard_clicked(self):
   
        mbu = TouchAuxMultibutton(QCoreApplication.translate("context","Wizard"),self.parent())
        mbu.setTextSize(2)
        mbu.setText(QCoreApplication.translate("context","Do you want to hide the current album")+" '"+self.currdir+"' "+QCoreApplication.translate("context","or do you want to show already hidden albums?"))
        mbu.setButtons([QCoreApplication.translate("context","Hide"),QCoreApplication.translate("context","Show")])
        
        (res,but)=mbu.exec_()
        
        if but==QCoreApplication.translate("context","Hide"):
            if len(self.dirstack)>1:
                p=TouchAuxKeyboard(QCoreApplication.translate("context","Key?"),"",self.parent())
                pw1=p.exec_()

                p=TouchAuxKeyboard(QCoreApplication.translate("context","Confirm"),"",self.parent())
                pw2=p.exec_()
                  
                if pw1==pw2:
               
                    f = open(picsdir+self.currdir+"/.hidden", "w")
                    if f != None:
                        f.write(pw1)
                        f.close()
                        self.scan_directories()
                        self.scan_images()
                else:
                    msg=TouchAuxMessageBox(QCoreApplication.translate("context","Error"), self.parent())
                    msg.setText(QCoreApplication.translate("context","Keys did not match! Try again."))
                    msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                    msg.setPosButton(QCoreApplication.translate("context","Okay"))
                    (void,void)=msg.exec_()
                
            else:
                msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                msg.setText("'"+self.currdir+"' "+QCoreApplication.translate("context","is the last album and can not be hidden."))
                msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                msg.setPosButton(QCoreApplication.translate("context","Okay"))
                (void,void)=msg.exec_()
        elif but==QCoreApplication.translate("context","Show"):
            
            # scan for hidden scan_directories
            self.scan_directories(True)
            
            if len(self.dirstack)>0:
            
                msg=TouchAuxListRequester(QCoreApplication.translate("context","Show"), QCoreApplication.translate("context","Select album to unlock:"), self.dirstack, self.dirstack[0],QCoreApplication.translate("context","Show"),self.parent())
                (res,showdir)=msg.exec_()
                if res:
                    p=TouchAuxKeyboard(QCoreApplication.translate("context","Key?"),"",None)
                    pw1=p.exec_()
                    
                    f = open(picsdir + showdir + "/.hidden", "r")
                    pw2=f.read()
                    f.close  
                    
                    if pw1==pw2:
                        os.remove(picsdir + showdir + "/.hidden")
                        self.currdir=showdir
                        self.scan_directories()
                    else:
                        msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                        msg.setText(QCoreApplication.translate("context","Key not matching."))
                        msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                        msg.setPosButton(QCoreApplication.translate("context","Okay"))
                        (void,void)=msg.exec_()
            else:
                msg=TouchAuxMessageBox(QCoreApplication.translate("context","Info"), self.parent())
                msg.setText(QCoreApplication.translate("context","No hidden albums found."))
                msg.addPixmap(QPixmap(icondir + "dialog-warning.png"))
                msg.setPosButton(QCoreApplication.translate("context","Okay"))
                (void,void)=msg.exec_()
                
            self.scan_directories()
            self.scan_images()
            
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
