#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

# code based upon the work of Jean Francois Puget, found at
# https://www.ibm.com/developerworks/community/blogs/jfp/entry/How_To_Compute_Mandelbrodt_Set_Quickly?lang=en
#


import numpy as np
import sys, math, time
from auxiliaries import *
from TouchStyle import *
from colormap import *

hostdir = os.path.dirname(os.path.realpath(__file__)) + "/"
showdir=showdir = hostdir + "../37681ea0-dc00-11e6-9598-0800200c9a66/pics/"
if not os.path.exists(showdir): showdir=""

# für die Entwicklungsumgebung PeH
if not os.path.exists(showdir):
    showdir = hostdir + "../../37681ea0-dc00-11e6-9598-0800200c9a66/pics/"
    if not os.path.exists(showdir): showdir=""
    develop=True
else:
    develop=False

try:
    with open(hostdir+"manifest","r") as f:
        r=f.readline()
        while not "version" in r:
          r=f.readline()
        
        if "version" in r:
          vstring = "v" + r[ r.index(":")+2 : ]
        else: vstring=""
        f.close()
except:
    vstring=""
    
colormap=[1,1,1]*16
curcolset="r-g-b"
colormap=setColorMap(curcolset)

cancel=False

class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)

        translator = QTranslator()
        path = os.path.dirname(os.path.realpath(__file__))
        translator.load(QLocale.system(), os.path.join(path, "benoitxt_"))
        self.installTranslator(translator)

        self.xmin=-2.15
        self.xmax=1.1833333
        self.ymin=-1.25
        self.ymax=1.25
        self.maxiter=3
        self.zoomfac=2
        
        # create the empty main window
        self.w = TouchWindow("BenoiTxt")
        
      
        # create central widget
        
        self.centralwidget=QWidget()
        
        self.layout=QVBoxLayout()
        
        self.vers=QLabel()
        self.vers.setObjectName("tinylabel")
        self.vers.setAlignment(Qt.AlignRight)
        self.vers.setText(vstring)
        self.layout.addWidget(self.vers)
        
        #self.layout.addStretch()
        
        self.text=QLabel()
        self.text.setText("...yawn...")
        self.text.setObjectName("smalllabel")
        self.text.setAlignment(Qt.AlignCenter)
        
        self.layout.addWidget(self.text)
        self.layout.addStretch()
        
        self.progress=QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setMinimum(0)
        self.progress.setValue(0)
        
        self.layout.addWidget(self.progress)
        self.layout.addStretch()
        
        self.knopf=QPushButton("Start")
        self.knopf.clicked.connect(self.rechne)
        
        self.layout.addWidget(self.knopf)
        
        self.centralwidget.setLayout(self.layout)
        
        self.w.setCentralWidget(self.centralwidget)
        
        self.w.show()

        # create an overlay pixmap:
  
        self.bild = QLabel(self.w)
        self.bild.setGeometry(0, 0, 240, 320)
        self.bild.setPixmap(QPixmap(240,320))

        self.bild.mousePressEvent=self.on_bild_clicked
        
        self.exec_()
         

    
    def on_bild_clicked(self,sender):
        self.bild.mousePressEvent=None
        self.bild.hide()
        success=True
        while success:
            t=TouchAuxMultibutton("BenoiTxt",self.parent())
            t.setButtons([ QCoreApplication.translate("obc","Zoom in"),
                           QCoreApplication.translate("obc","Zoom out"),
                           QCoreApplication.translate("obc","Move"),
                           QCoreApplication.translate("obc","Set colors"),
                           QCoreApplication.translate("obc","Options"),"",
                           QCoreApplication.translate("obc","Exit")
                           ]) 
            (success,result)=t.exec_()
            
            if   result==QCoreApplication.translate("obc","Exit"): self.exit()
            elif result==QCoreApplication.translate("obc","Options"):
                save=QCoreApplication.translate("obc","Save image")
                if showdir=="": save=""
                
                t=TouchAuxMultibutton("BenoiTxt",self.parent())
                t.setButtons([ QCoreApplication.translate("obc","Zoom factor"),
                               QCoreApplication.translate("obc","Reset region"),
                               QCoreApplication.translate("obc","Region data"),
                               QCoreApplication.translate("obc","Set iterations"),
                               QCoreApplication.translate("obc","Re-calculate"),
                               save
                              ]) 
                (success,result)=t.exec_() 
            
            if success==False: self.bild.show()
            
            if result==QCoreApplication.translate("obc","Reset region"):
                self.xmin=-2.15
                self.xmax=1.1833333
                self.ymin=-1.25
                self.ymax=1.25
                success=False
                self.progress.setValue(0)
            if result==QCoreApplication.translate("obc","Region data"):
                r=self.regionData()
                if not r:
                    self.bild.show()
                success=False
            elif result==QCoreApplication.translate("obc","Re-calculate"):
                success=False
                self.progress.setValue(0)
            elif result==QCoreApplication.translate("obc","Save image"):    
                self.saveImage()
                success=False
                self.bild.show()
            elif result==QCoreApplication.translate("obc","Zoom factor"):
                r=self.setZoomFactor()
                if r:
                    success=False
                    self.bild.show()
            elif result==QCoreApplication.translate("obc","Zoom in"):
                self.bild.show()
                self.do_zoom()
                success=False
                self.bild.hide()
                self.progress.setValue(0)
            elif result==QCoreApplication.translate("obc","Zoom out"):
                self.bild.show()
                self.do_zoom_out()
                success=False
                self.bild.hide()
                self.progress.setValue(0) 
            elif result==QCoreApplication.translate("obc","Move"):
                self.bild.show()
                self.do_move()
                success=False
                self.bild.hide()
                self.progress.setValue(0)
            elif result==QCoreApplication.translate("obc","Set iterations"):
                r=self.setIterations()
                if r:
                    success=False
                    self.bild.show()
            elif result==QCoreApplication.translate("obc","Set colors"):
                self.setColors()
                success=False
            self.processEvents()
        
        self.processEvents()
        
        if self.bild.isVisible(): self.bild.mousePressEvent=self.on_bild_clicked     
        else:                     self.bild.mousePressEvent=None
        self.processEvents()
        
    def regionData(self):
        xwidth=self.xmax-self.xmin
        ywidth=self.ymax-self.ymin
        xc = self.xmin+0.5*xwidth
        yc = self.ymin+0.5*ywidth
        
        mb=TouchAuxMessageBox("Region",self.parent())
        mb.buttonsHorizontal(True)
        mb.setPosButton(QCoreApplication.translate("region","Set"))
        mb.setNegButton(QCoreApplication.translate("region","Okay"))
        mb.setText("Re./Im. center:<br>"+"{:.12f}".format(xc)+"<br>"+"{:.12f}".format(yc)+"<br>Im. width:<br>"+"{:.12f}".format(ywidth))
        
        (suc,res)=mb.exec_()
        
        if suc and res==QCoreApplication.translate("region","Set"):
            cx="{:.24f}".format(xc)
            cy="{:.24f}".format(yc)
            wy="{:.24f}".format(ywidth)
            t=TouchAuxKeyboard("Re. cent.",cx, self.parent())
            ncx=t.exec_()
            t=TouchAuxKeyboard("Im. cent.",cy, self.parent())
            ncy=t.exec_()
            t=TouchAuxKeyboard("Im. width",wy, self.parent())
            nwy=t.exec_()
            if ncx!="" and ncy!="" and nwy!="":
                if isfloat(ncx) and isfloat(ncy) and isfloat(nwy):
                  ywidth=float(nwy)
                  xwidth=ywidth*4/3
                  xc=float(ncx)
                  yc=float(ncy)
                  self.xmin = xc-(0.5*xwidth)
                  self.xmax = xc+(0.5*xwidth)
                  self.ymin = yc-(0.5*ywidth)
                  self.ymax = yc+(0.5*ywidth)
                  self.progress.setValue(0)
                  return True
        return False
      
    def saveImage(self):
        m=TouchAuxMessageBox(QCoreApplication.translate("save","Save"), self.parent())
        m.setText(QCoreApplication.translate("save","Save TXT image or generate HiRes 1280x960 image (will take a lot of time)?"))
        m.setPosButton(QCoreApplication.translate("save","Save"))
        m.setNegButton(QCoreApplication.translate("save","Generate"))
        (s,r)=m.exec_()
        if s and r==QCoreApplication.translate("save","Save"):
            if not os.path.exists(showdir + "BenoiTxt/"): os.mkdir(showdir + "BenoiTxt")
            if os.path.isdir(showdir + "BenoiTxt"):
              void=self.bild.pixmap().save(showdir + "BenoiTxt/" +time.strftime("%y%m%d%H%M%S")+".png","PNG",80)
        elif s and r==QCoreApplication.translate("save","Generate"):  
            self.riese(1280,960)
        self.bild.show()
        self.knopf.setEnabled(True)     
    
    def setColors(self):
        global curcolset, colormap
        self.bild.hide()
        (success,result) = TouchAuxListRequester(QCoreApplication.translate("colors","Colors"),
                                                 QCoreApplication.translate("colors","Select color set"),
                                                 listColorMaps(),
                                                 curcolset,
                                                 QCoreApplication.translate("colors","Okay")
                                                 ,self.parent()).exec_()
        if success:
            curcolset=result
            colormap=setColorMap(result)
            
            self.knopf.setEnabled(False)
            self.text.setText("...colormapping")
            self.processEvents()
            self.mand2pixmap(320,240,self.m,int(math.pow(2,(self.maxiter+3))),self.bild.pixmap(), self.progress, self)
            self.bild.update()
            self.text.setText("...ready")
            self.processEvents()
        self.bild.show()
        self.knopf.setEnabled(True)
            
    def setIterations(self):
      
        (success,result)= TouchAuxRequestInteger(QCoreApplication.translate("reqint","Iterations"),
                                                 QCoreApplication.translate("reqint","Set calc. depth:"),
                                                 self.maxiter,1,10,
                                                 QCoreApplication.translate("reqint","Okay")).exec_()
        if success==False or result==self.maxiter: return False
        self.maxiter=result
        return True
    
    def setZoomFactor(self):
        if self.zoomfac==1.5: self.zoomfac=1
        (success,result) = TouchAuxRequestInteger(QCoreApplication.translate("reqint","Zoom"),
                                                 QCoreApplication.translate("reqint","Set zoom factor:"),
                                                 self.zoomfac,1,10,
                                                 QCoreApplication.translate("reqint","Okay")).exec_()
        if success==False or result==self.zoomfac:
            if self.zoomfac==1: self.zoomfac=1.5
            return False
        self.zoomfac=result
        if self.zoomfac==1: self.zoomfac=1.5
        return True
    
    def do_zoom(self):
        x=self.xmin
        self.bild.mousePressEvent=self.on_zoom_clicked
        self.bild.update()
        
        while x==self.xmin:
            self.processEvents()       
        self.bild.mousePressEvent=None
        
    def on_zoom_clicked(self, event):
        z=1/self.zoomfac
        
        ky = 1-(event.pos().x())/240
        kx = 1-(event.pos().y())/320 
               
        dx = (self.xmax - self.xmin)
        dy = (self.ymax - self.ymin)

        self.xmin = self.xmin + (dx*kx) - (0.5 * z * dx) 
        self.ymin = self.ymin + (dy*ky) - (0.5 * z * dy)
        self.xmax = self.xmin + (z * dx)
        self.ymax = self.ymin + (z * dy)
        
    def do_zoom_out(self):
        x=self.xmin
        self.bild.mousePressEvent=self.on_zoom_out_clicked
        self.bild.update()
        
        while x==self.xmin:
            self.processEvents()
        self.bild.mousePressEvent=None
        
    def on_zoom_out_clicked(self, event):
        ky = 1-(event.pos().x())/240
        kx = 1-(event.pos().y())/320
        
        dx = (self.xmax - self.xmin)
        dy = (self.ymax - self.ymin)
        
        self.xmin = self.xmin + (dx*kx) - (0.5 * self.zoomfac * dx) 
        self.ymin = self.ymin + (dy*ky) - (0.5 * self.zoomfac * dy)
        self.xmax = self.xmin + (self.zoomfac * dx)
        self.ymax = self.ymin + (self.zoomfac * dy)       

    
    def do_move(self):
        x=self.xmin
        self.bild.mousePressEvent=self.on_move_clicked
        self.bild.update()
        
        while x==self.xmin:
            self.processEvents()
        self.bild.mousePressEvent=None
        
    def on_move_clicked(self, event):
        ky = 1-(event.pos().x())/240
        kx = 1-(event.pos().y())/320 
               
        dx = (self.xmax - self.xmin)
        dy = (self.ymax - self.ymin)
        
        self.xmin = self.xmin + (dx*kx) - (0.5 * dx) 
        self.ymin = self.ymin + (dy*ky) - (0.5 * dy)
        self.xmax = self.xmin + dx
        self.ymax = self.ymin + dy
    
    def stop(self):
        self.cancel=True
    
    def rechne(self):
        self.knopf.setDisabled(True)
        self.text.setText("...computing")
        self.progress.setValue(0)
        (xv,yv,self.m)=mandelbrot_set2(self.xmin, self.xmax, self.ymin, self.ymax, 320, 240, int(math.pow(2,(self.maxiter+3))), self.progress, self)      
        
        self.text.setText("...colormapping")
        self.progress.setValue(100)
        self.processEvents()
        self.mand2pixmap(320,240,self.m,int(math.pow(2,(self.maxiter+3))),self.bild.pixmap(), self.progress, self)
        self.bild.show()
        self.text.setText("...ready")
        
        self.knopf.setEnabled(True)
        self.processEvents()
        self.bild.mousePressEvent=self.on_bild_clicked
        
    def riese(self, width, height):
        
        self.knopf.setDisabled(True)
        self.bild.hide()
        self.text.setText("...computing<br>hi-res")
        self.progress.setValue(0)
        self.processEvents()
        (xv,yv,ma)=mandelbrot_set2(self.xmin, self.xmax, self.ymin, self.ymax, width, height, int(math.pow(2,(self.maxiter+3))), self.progress, self)
        self.text.setText("...colormapping<br>hi-res")
        self.progress.setValue(100)
        self.processEvents()
        mpm=QPixmap(height,width)
        self.mand2pixmap(width,height,ma,int(math.pow(2,(self.maxiter+3))),mpm, self.progress, self)
        self.text.setText("...save")
        self.processEvents()
        if not os.path.exists(showdir + "BenoiTxt/"): os.mkdir(showdir + "BenoiTxt")
        if os.path.isdir(showdir + "BenoiTxt"):
          void=mpm.transformed(QTransform().rotate(90)).save(showdir + "BenoiTxt/" +time.strftime("%y%m%d%H%M%S")+".png","PNG",80)
        self.bild.show()
        self.text.setText("...ready")
    
    def mand2pixmap(self,width:int,height:int, mand, maxiter:int, pixmap, progress, e):
        pen=[]
        pen.append(qRgb(0,0,0))
        for i in range(16):
            (r,g,b)=colormap[i]
            pen.append(qRgb(r,g,b))
        
        z = np.full((width, height),16, dtype=int)
        mand2 = np.remainder(mand, z)
        mand2[mand==0]=-1
        mand2 = np.add(mand2, np.ones((width, height), int))
              
        st=100/height
        im=QImage(height, width, QImage.Format_RGB888)
        for j in range(0,height-1,5):
            for i in range(width):
                im.setPixel(height-j-1,width-i-1,pen[mand2[i,j]])
                im.setPixel(height-j-2,width-i-1,pen[mand2[i,j+1]])
                im.setPixel(height-j-3,width-i-1,pen[mand2[i,j+2]])
                im.setPixel(height-j-4,width-i-1,pen[mand2[i,j+3]])
                im.setPixel(height-j-5,width-i-1,pen[mand2[i,j+4]])
            progress.setValue(st*j)
            e.processEvents()
        p = QPainter()
        p.begin(pixmap)
        p.drawImage(QPoint(0,0),im)
        self.bild.update()
        
def isfloat(value):
  try:
    float(value)
    return True
  except:
    return False          

def mandelbrot_set2(xmin,xmax,ymin,ymax,width,height,maxiter, progress, e):
    r1 = np.linspace(xmin, xmax, width)
    r2 = np.linspace(ymin, ymax, height)
    c = r1 + r2[:,None]*1j
    n3 = mandelbrot_numpy(c,maxiter, progress, e)
    return (r1,r2,n3.T) 

def mandelbrot_numpy(c, maxiter, progress, e):
    output = np.zeros(c.shape, int)
    z = np.zeros(c.shape, np.complex64)
    for it in range(maxiter):
        notdone = np.less(z.real*z.real + z.imag*z.imag, 4.0)
        output[notdone] = it
        z[notdone] = z[notdone]**2 + c[notdone]
        e.processEvents()
        progress.setValue(100*it/maxiter)
    output[output == 0] = 1
    output[output == maxiter-1] = 0
    return output
  
  
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
