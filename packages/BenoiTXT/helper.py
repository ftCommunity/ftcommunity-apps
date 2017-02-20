#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import sys, time, os, shlex
import numpy, cv2
from subprocess import *
from TouchStyle import *
from threading import Timer
from auxiliaries import *

try:
    if TouchStyle_version<1.2:
        print("aux: TouchStyle >= v1.2 not found!")        
except:
    print("aux: TouchStyle_version not found!")
    TouchStyle_version=0

local = os.path.dirname(os.path.realpath(__file__)) + "/auxicon/"

class myColorRequest(TouchDialog):
    """ 
        Opens up a window containing a list of items and returns the item selected by the user
        
        ******** function call **********
        m = TouchAuxColorRequest(title:str, initcolor:QColor(), parent:class)
        (int:QColor)=m.exec_()
        ******** parameters *************
       
        title:str       Title of the input window
        parent:class    Parent class
               
        ******** Return values **********
        success:bool         True for user confirmed selection, False for user aborted selection
        result:str           selected item in case of success==True or None in case of success=False
    """
    
    def __init__(self,title:str, initcolor, parent=None):
        TouchDialog.__init__(self,title,parent)  
                
        self.result=None
        self.initcolor=initcolor
        self.title=title
        self.confbutclicked=False
        
    def on_button(self):
        self.result=self.sender().text()
        self.close()
        
    def exec_(self):
        self.layout=QVBoxLayout()
        
        # the message
        self.l_color=QLabel()
        self.l_color.setObjectName("smalllabel")
        self.l_color.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.l_color)
        
        self.layout.addStretch()
        
        self.s_red=QSlider()
        self.s_red.setOrientation(Qt.Horizontal)
        self.s_red.setRange(0,255)
        self.s_red.setSingleStep(1)
        self.s_red.setPageStep(1)
        self.s_red.setValue(self.initcolor.red())
        self.s_red.valueChanged.connect(self.on_color_update)
        self.layout.addWidget(self.s_red)

        self.layout.addStretch()
        
        self.s_green=QSlider()
        self.s_green.setOrientation(Qt.Horizontal)
        self.s_green.setRange(0,255)
        self.s_green.setSingleStep(1)
        self.s_green.setPageStep(1)
        self.s_green.setValue(self.initcolor.green())
        self.s_green.valueChanged.connect(self.on_color_update)
        self.layout.addWidget(self.s_green)
        
        self.layout.addStretch()
        
        self.s_blue=QSlider()
        self.s_blue.setOrientation(Qt.Horizontal)
        self.s_blue.setRange(0,255)
        self.s_blue.setSingleStep(1)
        self.s_blue.setPageStep(1)
        self.s_blue.setValue(self.initcolor.blue())
        self.s_blue.valueChanged.connect(self.on_color_update)
        self.layout.addWidget(self.s_blue)
        
        self.layout.addStretch()
        
        self.cbox=QLabel()
        self.cbox.setPixmap(QPixmap(240,40))
        self.layout.addWidget(self.cbox)
        
        self.layout.addStretch()
        if TouchStyle_version >=1.3:
           self.setCancelButton()
           confirmbutton=self.addConfirm()
           confirmbutton.clicked.connect(self.on_button)
        else:
           self.layout.addStretch()
           okb=QPushButton("Okay")
           okb.clicked.connect(self.on_button)
           self.layout.addWidget(okb)
        
        self.on_color_update()
        self.centralWidget.setLayout(self.layout) 
        
        TouchDialog.exec_(self)
        
        if self.confbutclicked or self.result!=None: return True,QColor(self.s_red.value(),self.s_green.value(), self.s_blue.value())
        return False,None
      
    def on_color_update(self):
        self.l_color.setText(
                           "R "+("00"+str(self.s_red.value()))[-3:]+" :"+
                           "G "+("00"+str(self.s_green.value()))[-3:]+": "+
                           "B "+("00"+str(self.s_blue.value()))[-3:])
        p=QPainter()
        p.begin(self.cbox.pixmap())
        p.fillRect(0,0,240,40,QColor(self.s_red.value(),self.s_green.value(), self.s_blue.value()))
        self.cbox.update()
        self.update()

class colorset(TouchDialog):
    """ 
        Opens up a window containing a list of items and returns the item selected by the user
        
        ******** function call **********
        m = colorset(title:str, colors[]:QColor, parent:class)
        (success, colors)=m.exec_()
        ******** parameters *************
       
        title:str       Title of the input window
        parent:class    Parent class
               
        ******** Return values **********
        success:bool         True for user confirmed selection, False for user aborted selection
        result:QColor[]      array of colors or None in case of success=False
    """
    
    def __init__(self,title:str, colors, parent=None):
        TouchDialog.__init__(self,title,parent)  
                
        self.result=None
        self.colors=colors
        
        self.title=title
        self.confbutclicked=False
        
    def on_button(self):
        self.result=self.sender().text()
        self.close()
        
    def colorgrid(self):
        colcnt = len(self.colors)
        cpr=8
        
        k=QVBoxLayout()
        c=QHBoxLayout()
        
        for i in range(32):
            s = i % cpr
            z = i // cpr
            if s==0:
                if i>0:
                    c.addStretch()
                    k.addLayout(c)
                    c=QHBoxLayout()
                
            self.b=PicButton(QPixmap(28,28))
            p=QPainter()
            p.begin(self.b.pixmap)
            if i<colcnt:
                p.fillRect(0,0,28,28,QColor(qRgb(self.colors[i][0],self.colors[i][1],self.colors[i][2])))
            else:
                p.fillRect(0,0,28,28,QColor(0,0,0))
                self.b.hide()
            p.end()
            self.b.setObjectName(str(i))
            self.b.setMaximumWidth(21)
            self.b.released.connect(self.on_color_clicked)
            c.addWidget(self.b)

        c.addStretch()
        k.addLayout(c)
        return k
    
    def on_color_clicked(self):
       ccol = int(float(self.sender().objectName()))
       if self.mode=="copy" or self.mode=="swap":
          self.firstcol=int(float(self.sender().objectName()))         
          if self.mode=="copy": self.mode="copy2"
          else: self.mode="swap2"
          self.findChild(QLabel, "titlebar").setText("target:")
       elif self.mode=="magic":
          self.firstcol=int(float(self.sender().objectName()))         
          self.mode="magic2"
          self.findChild(QLabel, "titlebar").setText("end:")
       elif self.mode=="copy2":
          self.colors[int(float(self.sender().objectName()))] = self.colors[self.firstcol]
          b=self.findChild(QAbstractButton, self.sender().objectName())
          p=QPainter()
          p.begin(b.pixmap)
          p.fillRect(0,0,28,28,QColor(qRgb(0,0,0)))
          p.end()
          b.show()
          self.update()
          self.mode=""
          self.findChild(QLabel, "titlebar").setText(self.title)
       elif self.mode=="swap2":
          z=int(float(self.sender().objectName()))
          h=self.colors[z]
          self.colors[z] = self.colors[self.firstcol]
          self.colors[self.firstcol]=h
          b=self.findChild(QAbstractButton, str(z))
          p=QPainter()
          p.begin(b.pixmap)
          p.fillRect(0,0,28,28,QColor(qRgb(self.colors[z][0],self.colors[z][1],self.colors[z][2])))
          p.end()
          b=self.findChild(QAbstractButton, str(self.firstcol))
          p=QPainter()
          p.begin(b.pixmap)
          p.fillRect(0,0,28,28,QColor(qRgb(self.colors[self.firstcol][0],self.colors[self.firstcol][1],self.colors[self.firstcol][2])))
          p.end()
          b.show()
          self.update()
          self.mode=""
          self.findChild(QLabel, "titlebar").setText(self.title)
       elif self.mode=="magic2":
          second=int(float(self.sender().objectName()))
          if second==self.firstcol: return
          if second<self.firstcol:
            a=self.firstcol
            self.firstcol=second
            second=a
          rs=self.colors[self.firstcol][0]
          gs=self.colors[self.firstcol][1]
          bs=self.colors[self.firstcol][2]
          re=self.colors[second][0]
          ge=self.colors[second][1]
          be=self.colors[second][2]
          dr = (re-rs)/(second-self.firstcol)
          dg = (ge-gs)/(second-self.firstcol)
          db = (be-bs)/(second-self.firstcol)
          for z in range(self.firstcol+1, second):
              self.colors[z]=[int(rs+(z-self.firstcol)*dr),
                              int(gs+(z-self.firstcol)*dg),
                              int(bs+(z-self.firstcol)*db) ]
          
              b=self.findChild(QAbstractButton, str(z))
              p=QPainter()
              p.begin(b.pixmap)
              p.fillRect(0,0,28,28,QColor(qRgb(self.colors[z][0],self.colors[z][1],self.colors[z][2])))
              p.end()
              b.show()
          self.update()
          self.mode=""
          self.findChild(QLabel, "titlebar").setText(self.title)
       else:
          m=myColorRequest("Color",QColor(qRgb(self.colors[ccol][0],self.colors[ccol][1],self.colors[ccol][2])), None)
          (s,c)=m.exec_()
          if s:
              self.colors[ccol][0]=c.red()
              self.colors[ccol][1]=c.green()
              self.colors[ccol][2]=c.blue()
       p=QPainter()
       p.begin(self.sender().pixmap)
       p.fillRect(0,0,28,28,QColor(qRgb(self.colors[ccol][0],self.colors[ccol][1],self.colors[ccol][2])))
       p.end()
       
    def addcolor(self):
        if (len(self.colors))<32:
          self.colors.append([ 0, 0, 0])
          b=self.findChild(QAbstractButton, str((len(self.colors)-1)))
          p=QPainter()
          p.begin(b.pixmap)
          p.fillRect(0,0,28,28,QColor(qRgb(0,0,0)))
          p.end()
          b.show()
   
    def delcolor(self):
        if len(self.colors)<2: return
        b=self.findChild(QAbstractButton, str((len(self.colors)-1)))
        if b!=None: b.hide()
        self.colors.pop()
    
    def set_palette(self):
        self.mode=""
        cnc = len(self.colors)
        (s,r) = TouchAuxRequestInteger("Colors","Set palette size:",cnc,4,32,"Okay",self.parent()).exec_()
        if s and r!=cnc:
            if r>cnc:
              for i in range(cnc,r): self.addcolor()
            if r<cnc:
              for i in range(r,cnc): self.delcolor()
              
        return
    
    def color_copy(self):
        self.mode="copy"
        self.findChild(QLabel, "titlebar").setText("source:")
    def color_swap(self):
        self.mode="swap"
        self.findChild(QLabel, "titlebar").setText("source:")
    def color_magic(self):
        self.mode="magic"
        self.findChild(QLabel, "titlebar").setText("start:")
        
    def set_layout(self):
        self.layout=QVBoxLayout()
        
        # the message
        self.gridwidget=QWidget()
        
        self.gridwidget.setLayout(self.colorgrid())
        
        self.layout.addWidget(self.gridwidget)
        
        h=QHBoxLayout()
        pb = PicButton(QPixmap(local+"../icons/palette.png"))
        pb.clicked.connect(self.set_palette)
        h.addWidget(pb)
        h.addStretch()        
        
        pb = PicButton(QPixmap(local+"../icons/copy.png"))
        pb.clicked.connect(self.color_copy)
        h.addWidget(pb)
        h.addStretch()
 
        pb = PicButton(QPixmap(local+"../icons/swap.png"))
        pb.clicked.connect(self.color_swap)
        h.addWidget(pb)
        h.addStretch()
        
        pb = PicButton(QPixmap(local+"../icons/magic.png"))
        pb.clicked.connect(self.color_magic)
        h.addWidget(pb)

        self.layout.addStretch()        
        
        self.layout.addLayout(h)
       
        if TouchStyle_version >=1.3:
           self.setCancelButton()
           confirmbutton=self.addConfirm()
           confirmbutton.clicked.connect(self.on_button)
        else:
           self.layout.addStretch()
           okb=QPushButton("Okay")
           okb.clicked.connect(self.on_button)
           self.layout.addWidget(okb)
        
        self.on_color_update()
    
    def exec_(self):
        self.mode=""
        self.set_layout()

        self.centralWidget.setLayout(self.layout) 
       
        TouchDialog.exec_(self)
        
        if self.confbutclicked or self.result!=None: return True,self.colors
        return False,None
      
    def on_color_update(self):
        return
        self.l_color.setText(
                           "R "+("00"+str(self.s_red.value()))[-3:]+" :"+
                           "G "+("00"+str(self.s_green.value()))[-3:]+": "+
                           "B "+("00"+str(self.s_blue.value()))[-3:])
        p=QPainter()
        p.begin(self.cbox.pixmap())
        p.fillRect(0,0,240,40,QColor(self.s_red.value(),self.s_green.value(), self.s_blue.value()))
        self.cbox.update()
        self.update()