#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

# TODO
# - when stopping the app with the button while the solver thread
#   is still running this basically makes the launcher lock until
#   the solver thread is done

import sys, os
from TxtStyle import *
import pycuber as pc
from pycuber.solver import CFOPSolver
from threading import Thread

# a rotating "i am busy" widget to be shown while the solver runs
class BusyAnimation(QWidget):
    expired = pyqtSignal()

    def __init__(self, parent=None):
        super(BusyAnimation, self).__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.Window)
        self.setStyleSheet("background:transparent;")
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.resize(64, 64)
        pos = parent.mapToGlobal(QPoint(0,0))
        self.move(pos + QPoint(parent.width()/2-32, parent.height()/2-32))

        self.step = 0

        # animate at 5 frames/sec
        self.atimer = QTimer(self)
        self.atimer.timeout.connect(self.animate)
        self.atimer.start(200)

        # create small circle bitmaps for animation
        self.dark = self.draw(16, QColor("#808080"))
        self.bright = self.draw(16, QColor("#fcce04"))
        
    def draw(self, size, color):
        img = QImage(size, size, QImage.Format_ARGB32)
        img.fill(Qt.transparent)

        painter = QPainter(img)
        painter.setPen(Qt.white)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(0, 0, img.width()-1, img.height()-1)
        painter.end()

        return img

    def animate(self):
        # this is ugly ... we should be able to prevent
        # it not become invisble in the first place ...
        if not self.isVisible():
            self.show()

        self.step += 45
        self.repaint()

    def close(self):
        self.atimer.stop()
        super(BusyAnimation, self).close()

    def paintEvent(self, event):
        radius = min(self.width(), self.height())/2 - 16
        painter = QPainter()
        painter.begin(self)

        painter.setRenderHint(QPainter.Antialiasing)

        painter.translate(self.width()/2, self.height()/2)
        painter.rotate(45)
        painter.rotate(self.step)
        painter.drawImage(0,radius, self.bright)
        for i in range(7):
            painter.rotate(45)
            painter.drawImage(0,radius, self.dark)

        painter.end()

class AboutDialog(TxtDialog):
    def __init__(self,parent):
        text = '<h2><font color="#fcce04">Cube</font></h2>' \
               '<b>Rubiks cube solver</b><br>' \
               '2016 by Till Harbaum<br>' \
               '<h2><font color="#fcce04">Credits</font></h2>' \
               '<b>' + pc.__title__ + ' ' + pc.__version__ + \
               '</b><br> by Adrian Liaw<br>' \
               '<b>App Icon</b><br> by Booyabazooka, Meph666'

        TxtDialog.__init__(self, "About", parent)
        
        txt = QTextEdit()
        txt.setReadOnly(True)
        
        font = QFont()
        font.setPointSize(16)
        txt.setFont(font)
    
        txt.setHtml(text)

        self.setCentralWidget(txt)

class CubeWidget(QWidget):
    def __init__(self, cube, parent=None):
        super(CubeWidget, self).__init__(parent)
        
        qsp = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        qsp.setHeightForWidth(True)
        self.setSizePolicy(qsp)

        self.cube = cube

        # draw a square
    def draw_square(self, painter, x, y, size, color, base_color):
        painter.setPen(base_color)
        painter.setBrush(color)
        painter.drawRect(x, y, size-1, size-1)

    def heightForWidth(self,w):
        return 3*w/4

    def cube_color(self, colour):
        cube2qt = {
            "red":     QColor("#FF0000"), "yellow":  QColor("#FFFF00"), "green":   QColor("#00FF00"),
            "white":   QColor("#FFFFFF"), "orange":  QColor("#FFA500"), "blue":    QColor("#0000FF"),
            "unknown": QColor("#000000")
        }
        return cube2qt[colour]

    def draw_face(self, painter, xb, yb, size, face):
        for x in range(3):
            for y in range(3):
                self.draw_square(painter, xb+size*x, yb+size*y, size, 
                                 self.cube_color( face[y][x].colour ), QColor("#000000"))

    def paintEvent(self, QPaintEvent):
        size = min(self.height()/3, self.width()/4)/3
 
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        self.draw_face(painter, size*3, size*0, size, self.cube.U)
        self.draw_face(painter, size*0, size*3, size, self.cube.L)
        self.draw_face(painter, size*3, size*3, size, self.cube.F)
        self.draw_face(painter, size*6, size*3, size, self.cube.R)
        self.draw_face(painter, size*9, size*3, size, self.cube.B)
        self.draw_face(painter, size*3, size*6, size, self.cube.D)
            
        painter.end()

    def update(self, cube):
        self.cube = cube
        self.repaint()

        # sublcass TxtWindow to implement a close signal
        # to interrupt a running busy animation
class CubeWindow(TxtWindow):
    closed = pyqtSignal()

    def __init__(self, str):
        TxtWindow.__init__(self, str)

    def close(self):
        self.closed.emit()
        super(TxtWindow, self).close()
        
class FtcGuiApplication(TxtApplication):
    def __init__(self, args):
        TxtApplication.__init__(self, args)

        self.busy = None

        # create the empty main window
        self.w = CubeWindow("Cube")
        self.w.closed.connect(self.on_closed)
        
        menu = self.w.addMenu()
        menu_about = menu.addAction("About")
        menu_about.triggered.connect(self.show_about)

        self.vbox = QVBoxLayout()
        self.vbox.addStretch()
        
        # Create a Cube object
        self.cube = pc.Cube()
        self.randomized = False

        # solve
        self.solution = None
        self.step = 0
        self.timer = None

        # display cube
        self.cw = CubeWidget(self.cube)
        self.vbox.addWidget(self.cw)

        # display status
        self.status = QLabel("Solved")
        self.status.setObjectName("tinylabel")
        self.status.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.status)

        self.vbox.addStretch()

        # add buttons to step forth and back
        hbox_w = QWidget()
        hbox = QHBoxLayout()

        self.btn_rnd = QPushButton("R")
        self.btn_rnd.clicked.connect(self.on_rnd_clicked)
        hbox.addWidget(self.btn_rnd)

        self.btn_solve = QPushButton("S")
        self.btn_solve.clicked.connect(self.on_solve_clicked)
        hbox.addWidget(self.btn_solve)

        self.btn_back = QPushButton("<")
        self.btn_back.clicked.connect(self.on_back_clicked)
        hbox.addWidget(self.btn_back)

        self.btn_fore = QPushButton(">")
        self.btn_fore.clicked.connect(self.on_fore_clicked)
        hbox.addWidget(self.btn_fore)

        hbox_w.setLayout(hbox)
        self.vbox.addWidget(hbox_w)

        self.w.centralWidget.setLayout(self.vbox)

        # update view and buttons
        self.ui_update()

        self.w.show()
        self.exec_()        

    def on_closed(self):
        if self.busy:
            self.busy.close()
            self.busy = None
        
    def start_solver(self, cube):
        self.step = 0
        self.solution = None
        self.busy = BusyAnimation(self.w)

        # run solver in background
        self.t = Thread(target=self.solve, args=(self.cube.copy(),))
        self.t.start()

        # start timer to monitor thread (there's sure a nicer way
        # to solve this. e.g. by using a QThread)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(1000/10)

    def solve(self, cube):
        solver = CFOPSolver(cube)
        self.solution = solver.solve(False)  # True suppresses _all_ output!

    def on_timer(self):
        if not self.t.isAlive():
            self.timer.stop()
            print(self.solution)
            self.ui_update()
            self.busy.close()
            self.busy = None

    def cube_do(self, cmd):
        self.cube(cmd)
        self.ui_update()

    def ui_update(self):
        self.cw.update(self.cube)
        # as long as the timer is running the solver is running
        # and you basically cannot do anything in the gui
        if self.timer != None and self.timer.isActive():
            self.status.setText("Solving ...")
            self.btn_back.setEnabled(False)
            self.btn_fore.setEnabled(False)
            self.btn_solve.setEnabled(False)
            self.btn_rnd.setEnabled(False)
        else:
            self.btn_rnd.setEnabled(True)

            if self.solution:
                self.status.setText("Solution step " + 
                                    str(self.step) + "/" + 
                                    str(len(self.solution)))
                self.btn_back.setEnabled(self.step != 0)
                self.btn_fore.setEnabled(self.step != len(self.solution))
                self.btn_solve.setEnabled(False)
            else:
                if self.randomized: self.status.setText("Not solved")
                self.btn_back.setEnabled(False)
                self.btn_fore.setEnabled(False)
                self.btn_solve.setEnabled(self.randomized)

    def on_rnd_clicked(self):
        self.solution = None
        self.randomized = True

        # randomize
        rand_alg = pc.Formula().random()
        self.cube(rand_alg)

        self.ui_update();

    def on_solve_clicked(self):
        print("SOLVE")
        self.start_solver(self.cube)
        self.ui_update()

    def on_back_clicked(self):
        if self.step != 0:
            self.step -= 1
            cmd = self.solution[self.step].inverse()
            self.cube_do(cmd)

    def on_fore_clicked(self):
        if self.step != len(self.solution):
            cmd = self.solution[self.step]
            self.step += 1
            self.cube_do(cmd)

    def show_about(self):
        dialog = AboutDialog(self.w)
        dialog.exec_()
        
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
