#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

# TODO: Add kinetic scrolling
# http://blog.codeimproved.net/posts/kinetic-scrolling.html

import sys
import subprocess
import stat
import json
from TouchStyle import *

LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_PATH = os.path.join(LOCAL_PATH, 'stations.json')
# currently on TXT the mpg123 tools are stored below the app directory
if platform.machine() == "armv7l":
    MPG123 = os.path.join(LOCAL_PATH, "mpg123", "mpg123") + " -q --stdout --encoding u8 --rate 22050 --mono"
    TXT_PLAY = os.path.join(LOCAL_PATH, "txt_snd_cat")
    # check if the executables really are executable
    # as the file came from a zip during installation it
    # may not have the executable flag set
    EXECS = [MPG123.split()[0], TXT_PLAY]
    for e in EXECS:
        st = os.stat(e)
        if not (st.st_mode & stat.S_IEXEC):
            os.chmod(e, st.st_mode | stat.S_IEXEC)
else:
    # on a PC play through sox and use the same encoding for
    # authentic sound (minus the TXTs static noise ...)
    MPG123 = "mpg123 --stdout --encoding u8 --rate 22050 --mono"
    TXT_PLAY = "play -q -t raw -b 8 -e unsigned -r 22050 -c 1 -"


class StationListWidget(QListWidget):
    play = pyqtSignal(str)

    def __init__(self, parent=None):
        super(StationListWidget, self).__init__(parent)
        self.file = open(JSON_PATH)
        self.stations = json.load(self.file)
        self.proc_mpg123 = None
        self.proc_txt_snd_cat = None

        for station, url in self.stations.items():
            item = QListWidgetItem(station)
            item.setData(Qt.UserRole, (station, url))
            self.addItem(item)

        self.itemClicked.connect(self.onItemClicked)

    def __del__(self):
        self.stop_player()

    def stop_player(self):
        # stop all player processes
        if self.proc_txt_snd_cat:
            self.proc_txt_snd_cat.terminate()

        if self.proc_mpg123:
            self.proc_mpg123.terminate()

        if self.proc_mpg123:
            self.proc_mpg123.wait()
            self.proc_mpg123 = None

        if self.proc_txt_snd_cat:
            # kill sox/txt_snd_cat if it's still running
            if not self.proc_txt_snd_cat.poll():
                self.proc_txt_snd_cat.kill()

            self.proc_txt_snd_cat.wait()
            self.proc_txt_snd_cat = None

    def stop(self):
        self.stop_player()
        self.clearSelection()
        self.play.emit(None)

    def onItemClicked(self, item):
        # stop whatever is currently playing
        self.stop_player()

        station, url = item.data(Qt.UserRole)
        mpg123_cmd = MPG123.split() + [url]
        # make sure the local mpg123/lib directory is being searched
        # for libraries
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.path.join(LOCAL_PATH, "mpg123", "lib")
        self.proc_mpg123 = subprocess.Popen(mpg123_cmd, env=env, stdout=subprocess.PIPE)
        self.proc_txt_snd_cat = subprocess.Popen(TXT_PLAY.split(), stdin=self.proc_mpg123.stdout, stdout=subprocess.PIPE)
        self.proc_mpg123.stdout.close()  # Allow mpg123 to receive a SIGPIPE if txt_play exits.

        self.play.emit(station)

class FtcGuiApplication(TouchApplication):

    def __init__(self, args):
        TouchApplication.__init__(self, args)

        # create the empty main window
        self.w = TouchWindow("MP3")

        self.vbox = QVBoxLayout()

        self.songlist = StationListWidget(self.w)
        self.songlist.play[str].connect(self.play)
        self.vbox.addWidget(self.songlist)

        self.playing = QLabel()
        self.playing.setText('No Stream')
        self.playing.setStyleSheet('color: yellow')
        self.playing.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.playing)
        self.stop_but = QPushButton("Stop")
        self.stop_but.setDisabled(True)
        self.stop_but.clicked.connect(self.songlist.stop)
        self.vbox.addWidget(self.stop_but)

        self.w.centralWidget.setLayout(self.vbox)

        self.w.show()

        self.exec_()

    def play(self, data):
        if data == None:
            self.stop_but.setEnabled(False)
            self.playing.setText('No Stream')
            self.playing.self.playing.setStyleSheet('color: yellow')
        else:
            self.stop_but.setEnabled(True)
            self.playing.setText(data)
            self.playing.setStyleSheet('color: #00ff00')

if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
