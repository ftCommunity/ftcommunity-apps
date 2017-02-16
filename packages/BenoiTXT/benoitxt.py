#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import numpy as np
import sys, math
from auxiliaries import *
from TouchStyle import *
from colormap import *

hostdir = os.path.dirname(os.path.realpath(__file__)) + "/"
showdir=""#showdir = hostdir + "../37681ea0-dc00-11e6-9598-0800200c9a66/pics/"
if not os.path.exists(showdir): showdir=""

# für die Entwicklungsumgebung PeH
if not os.path.exists(showdir):
    #showdir = hostdir + "../../37681ea0-dc00-11e6-9598-0800200c9a66/pics/"
    develop=True
else:
    develop=False


colormap=[1,1,1]*16
curcolset="autumn"
colormap=setColorMap(curcolset)

cancel=False

class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)

        translator = QTranslator()
        path = os.path.dirname(os.path.realpath(__file__))
        translator.load(QLocale.system(), os.path.join(path, "benoitxt_"))
        self.installTranslator(translator)

        self.xmin=-2.4
        self.xmax=0.9
        self.ymin=-1.25
        self.ymax=1.25
        self.maxiter=4
        print("maxiter",math.pow(2,(self.maxiter+3)))
        
        # create the empty main window
        self.w = TouchWindow("BenoiTxt")
        
      
        # create central widget
        
        self.centralwidget=QWidget()
        
        self.layout=QVBoxLayout()
        self.layout.addStretch()
        
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
        
        success=True
        while success:
            t=TouchAuxMultibutton("BenoiTxt",self.parent())
            if showdir!="":t.setButtons([ QCoreApplication.translate("obc","Zoom in"),
                                          QCoreApplication.translate("obc","Zoom out"),
                                          QCoreApplication.translate("obc","Move"),
                                          QCoreApplication.translate("obc","Set iterations"),
                                          QCoreApplication.translate("obc","Set colors"),
                                          QCoreApplication.translate("obc","Save image"),
                                          QCoreApplication.translate("obc","Exit")
                                          ])
            else:          t.setButtons([ QCoreApplication.translate("obc","Zoom in"),
                                          QCoreApplication.translate("obc","Zoom out"),
                                          QCoreApplication.translate("obc","Move"),
                                          QCoreApplication.translate("obc","Set iterations"),
                                          QCoreApplication.translate("obc","Set colors"),
                                          QCoreApplication.translate("obc","Exit")
                                          ]) 
            (success,result)=t.exec_()
            
            if   result==QCoreApplication.translate("obc","Exit"): self.exit()
            elif result==QCoreApplication.translate("obc","Zoom in"):
                self.do_zoom()
                success=False
                self.bild.hide()
                self.progress.setValue(0)
            elif result==QCoreApplication.translate("obc","Zoom out"):
                self.do_zoom_out()
                success=False
                self.bild.hide()
                self.progress.setValue(0) 
            elif result==QCoreApplication.translate("obc","Move"):
                self.do_move()
                success=False
                self.bild.hide()
                self.progress.setValue(0)
            elif result==QCoreApplication.translate("obc","Set iterations"):
                r=self.setIterations()
                if r:
                    success=False
                    self.bild.hide()
                    self.progress.setValue(0)
                    print("maxiter",pow(2,self.maxiter+3))
            elif result==QCoreApplication.translate("obc","Set colors"):
                self.setColors()
                success=False
            print("su",success)
    
    def setColors(self):
        global curcolset, colormap
        (success,result) = TouchAuxListRequester(QCoreApplication.translate("colors","Colors"),
                                                 QCoreApplication.translate("colors","Select color set"),
                                                 ["rainbow", "forest", "planet", "fire", "dreamy", "autumn", "icy", "r-g-b", "y-c-m", "amstrad", "zuse", "monochrome", "default"],
                                                 curcolset,
                                                 QCoreApplication.translate("colors","Okay")
                                                 ).exec_()
        if success:
            curcolset=result
            colormap=setColorMap(result)
            self.mand2pixmap(320,240,self.m,int(math.pow(2,(self.maxiter+3))),self.bild.pixmap())
            self.bild.update()
            
            
    def setIterations(self):
      
        (success,result)= TouchAuxRequestInteger(QCoreApplication.translate("reqint","Iterations"),
                                                 QCoreApplication.translate("reqint","Set calc. depth:"),
                                                 self.maxiter,1,10,
                                                 QCoreApplication.translate("reqint","Okay")).exec_()
        if success==False or result==self.maxiter: return False
        self.maxiter=result
        return True
    
    def do_zoom(self):
        x=self.xmin
        self.bild.mousePressEvent=self.on_zoom_clicked
        self.bild.update()
        
        while x==self.xmin:
            self.processEvents()
            
        self.bild.mousePressEvent=self.on_bild_clicked
        
    
    def on_zoom_clicked(self, event):
        ky = 1-(event.pos().x())/240
        kx = 1-(event.pos().y())/320 
               
        dx = (self.xmax - self.xmin)
        dy = (self.ymax - self.ymin)
        
        self.xmin = self.xmin + (dx*kx) - (0.25 * dx) 
        self.ymin = self.ymin + (dy*ky) - (0.25 * dy)
        self.xmax = self.xmin + (0.5 * dx)
        self.ymax = self.ymin + (0.5 * dy)
    
    def do_zoom_out(self):
        dx = (self.xmax - self.xmin)/2
        dy = (self.ymax - self.ymin)/2
        self.xmin=self.xmin - dx 
        self.xmax=self.xmax + dx
        self.ymin=self.ymin - dy
        self.ymax=self.ymax + dy
    
    def do_move(self):
        x=self.xmin
        self.bild.mousePressEvent=self.on_move_clicked
        self.bild.update()
        
        while x==self.xmin:
            self.processEvents()
            
        self.bild.mousePressEvent=self.on_bild_clicked
    
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
        
        if cancel:
            self.text.setText("...yawn")
            self.progress.setValue(0)
        else:
            self.mand2pixmap(320,240,self.m,int(math.pow(2,(self.maxiter+3))),self.bild.pixmap())
            self.bild.show()
            self.text.setText("...ready")
        
        self.knopf.setEnabled(True)
        self.processEvents()

        
        
    def colorize(self, n, maxiter):
        if n>0 and n<maxiter:
          return colormap[int(n % 16)]
        
        else:
          return 0,0,0
        
    
    def mand2pixmap(self,width,height,mand, maxiter, pixmap):
       
        p = QPainter()
        p.begin(pixmap)
        for i in range(width):
            
            for j in range(height):
                (r,g,b)=self.colorize(mand[i,j],maxiter)

                p.setPen(QColor(r,g,b,255))
                p.drawPoint(QPoint(height-j-1,width-i-1))
        p.end()
          
def mandelbrot_set2(xmin,xmax,ymin,ymax,width,height,maxiter, progress, e):
    r1 = np.linspace(xmin, xmax, width)
    r2 = np.linspace(ymin, ymax, height)
    n3 = np.empty((width,height))
    nup=100/(width*height)
    z=0
    for i in range(width):
        for j in range(height):
            n3[i,j]=mandelbrot(r1[i],r2[j],maxiter)
            z=z+1
            progress.setValue(z*nup)
            e.processEvents()
            if cancel: return [],[],[]
    return r1,r2,n3

def mandelbrot(creal,cimag,maxiter):
    real = creal
    imag = cimag
    for n in range(maxiter):
        real2 = real*real
        imag2 = imag*imag
        if real2 + imag2 > 4.0:
            return n
        imag = 2* real*imag + cimag
        real = real2 - imag2 + creal       
    return 0
  
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
