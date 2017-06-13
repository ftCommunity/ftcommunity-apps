#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
from TouchStyle import *
import os

icon_path = os.path.dirname(os.path.realpath(__file__)) + '/osk/'
# simple on-screen-keyboard to be used on devices without physical
# keyboard attached


class TouchKeyboard(TouchDialog):
    # a pushbutton that additionally shows a second small label
    # in subscript

    class KbdButton(QPushButton):
        SUBSCRIPT_SCALE = 0.5

        def __init__(self, t, s, parent=None):
            if t == s:
                QPushButton.__init__(self, t, parent)
                self.sub = None
            else:
                QPushButton.__init__(self, t + " ", parent)
                self.sub = s

        def setText(self, t, s):
            if t == s:
                QPushButton.setText(self, t)
                self.sub = None
            else:
                QPushButton.setText(self, t + " ")
                self.sub = s

        def paintEvent(self, event):
            QPushButton.paintEvent(self, event)

            if self.sub:
                painter = QPainter()
                painter.begin(self)
                painter.setPen(QColor("#fcce04"))

                # half the normal font size
                font = painter.font()
                if font.pointSize() > 0:
                    font.setPointSize(font.pointSize() * self.SUBSCRIPT_SCALE)
                else:
                    font.setPixelSize(font.pixelSize() * self.SUBSCRIPT_SCALE)

                painter.setFont(font)

                # draw the time at the very right
                painter.drawText(self.contentsRect().adjusted(0, 3, -5, -3), Qt.AlignRight, self.sub)

                painter.end()

    # a subclassed QLineEdit that grabs focus once it has
    # been drawn for the first time
    class FocusLineEdit(QLineEdit):

        def __init__(self, parent=None):
            QLineEdit.__init__(self, parent)
            self.init = False

        def paintEvent(self, event):
            QLineEdit.paintEvent(self, event)
            if not self.init:
                self.setFocus()  # restore focus
                self.init = True

        def reset(self):
            self.init = False

    text_changed = pyqtSignal(str)

    keys_tab = ["A-O", "P-Z", "0-9"]
    keys_upper = [
        ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "Aa"],
        ["P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", ".", ",", " ", "_", "Aa"],
        ["=", "!", '"', "§", "$", "%", "&", "/", "(", ")", "*", "_", "'", "°", ">", "Aa"]
    ]
    keys_lower = [
        ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "Aa"],
        ["p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", ":", ";", "!", "?", "Aa"],
        ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "+", "-", "#", "^", "<", "Aa"]
    ]

    caps = False

    def __init__(self, parent=None):
        TouchDialog.__init__(self, "Input", parent)

        edit = QWidget()
        edit.hbox = QHBoxLayout()
        edit.hbox.setContentsMargins(0, 0, 0, 0)

        self.line = self.FocusLineEdit()
        self.line.setProperty("nopopup", True)
        self.line.setAlignment(Qt.AlignCenter)
        edit.hbox.addWidget(self.line)
        but = QPushButton(" ")
        but.setIcon(QIcon(icon_path + "osk_erase"))
        but.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        but.clicked.connect(self.key_erase)
        edit.hbox.addWidget(but)

        edit.setLayout(edit.hbox)
        self.layout.addWidget(edit)

        self.tab = QTabWidget()

        if self.caps:
            keys = self.keys_upper
            subs = self.keys_lower
        else:
            keys = self.keys_lower
            subs = self.keys_upper

        for a in range(3):
            page = QWidget()
            page.grid = QGridLayout()
            page.grid.setContentsMargins(0, 0, 0, 0)

            cnt = 0
            for cnt in range(len(keys[a])):
                if keys[a][cnt] == "Aa":
                    but = QPushButton()
                    but.setIcon(QIcon(icon_path + "osk_caps"))
                    but.clicked.connect(self.caps_changed)
                else:
                    but = self.KbdButton(keys[a][cnt], subs[a][cnt])
                    but.clicked.connect(self.key_pressed)

                but.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                page.grid.addWidget(but, cnt / 4, cnt % 4)

            page.setLayout(page.grid)
            self.tab.addTab(page, self.keys_tab[a])

        self.tab.tabBar().setExpanding(True)
        self.tab.tabBar().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.tab)

    def focus(self, str, cpos):
        self.line.setText(str)
        self.line.setCursorPosition(cpos)

    def key_erase(self):
        self.line.backspace()
        self.line.setFocus()  # restore focus

    def key_pressed(self):
        self.line.insert(self.sender().text()[0])
        self.line.setFocus()  # restore focus

        # user pressed the caps button. Exchange all button texts
    def caps_changed(self):
        self.line.setFocus()  # restore focus

        # default is not caps locked
        try:
            self.caps = not self.caps
        except AttributeError:
            self.caps = True

        if self.caps:
            keys = self.keys_upper
            subs = self.keys_lower
        else:
            keys = self.keys_lower
            subs = self.keys_upper

        # exchange all characters
        for i in range(self.tab.count()):
            gw = self.tab.widget(i)
            gl = gw.layout()
            for j in range(gl.count()):
                w = gl.itemAt(j).widget()
                if keys[i][j] != "Aa":
                    w.setText(keys[i][j], subs[i][j])

    def updateParent(self, parent):
        if TXT:
            # search for a matching root parent widget
            while parent and not (parent.inherits("TouchBaseWidget") or parent.inherits("TouchDialog")):
                parent = parent.parent()

            self.parent = parent

            if parent:
                parent.register(self)

            self.setParent(parent)

    def close(self):
        # user has close the input dialog. Sent updated string
        # to invoking widget
        TouchDialog.close(self)
        self.line.reset()
        self.text_changed.emit(self.line.text())


class TouchInputContext(QInputContext):

    def keyboard_present():
        # on the (non-arm) desktop always return False to force
        # on screen keyboard
        if platform.machine() != "armv7l":
            print("Forcing on screen keyboard on non-arm device")
            return False

        try:
            for i in os.listdir("/dev/input/by-id"):
                if i[-4:] == "-kbd":
                    return True
        except:
            print("No linux USB subsystem accessible")

        return False

    def __init__(self, parent):
        QInputContext.__init__(self, parent)
        self.keyboard = None

    def reset(self):
        pass

    def filterEvent(self, event):

        if(event.type() == QEvent.RequestSoftwareInputPanel):
            if self.focusWidget().property("nopopup"):
                print("ignoring keyboard widget itself")
                return True

            if not self.keyboard:
                self.keyboard = TouchKeyboard(self.focusWidget())
                self.keyboard.text_changed[str].connect(self.on_text_changed)
            else:
                self.keyboard.updateParent(self.focusWidget())

            text = ""
            cpos = 0
            self.widget = self.focusWidget()
            if self.widget.inherits("QLineEdit"):
                text = self.widget.text()
                cpos = self.widget.cursorPosition()
            elif self.widget.inherits("QTextEdit"):
                text = self.widget.toPlainText()
                cpos = self.widget.textCursor().position()
            else:
                print("Unsupported widget:", self.widget)

            self.keyboard.focus(text, cpos)

            self.keyboard.show()
            return True

            # the keyboard always overlays the entire sceen.
            # Thus we don't close it via the event but from the
            # panels own close button
        elif(event.type() == QEvent.CloseSoftwareInputPanel):
            return True

        return False

    def on_text_changed(self, str):
        if self.widget.inherits("QLineEdit"):
            self.widget.setText(str)
        elif self.widget.inherits("QTextEdit"):
            self.widget.setText(str)
