#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import os, sys, serial, time
import queue, pty, subprocess, select, stat
from TxtStyle import *

class SmallLabel(QLabel):
    def __init__(self, str, parent=None):
        super(SmallLabel, self).__init__(str, parent)
        self.setObjectName("smalllabel")
        self.setAlignment(Qt.AlignCenter)

class LogDialog(TxtDialog):
    def __init__(self,text,parent):
        TxtDialog.__init__(self, "Log", parent)
        
        txt = QTextEdit()
        txt.setReadOnly(True)
        
        font = QFont()
        font.setPointSize(16)
        txt.setFont(font)
    
        # load gpl from disk
        txt.setPlainText(text)

        self.setCentralWidget(txt)
        
class AvrdudeWidget(QWidget):
    done = pyqtSignal(bool)
    
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)
        self.port = None
        self.bootloader_file = None
        
        self.vbox = QVBoxLayout()

        self.vbox.addStretch()
        self.lbl = SmallLabel("Idle")
        self.vbox.addWidget(self.lbl)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.vbox.addWidget(self.progress)

        # result has an optional button used to view the
        # log file
        hbox_w = QWidget()
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0,0,0,0)
        hbox_w.setLayout(hbox)
        
        self.result = SmallLabel("")
        hbox.addWidget(self.result, 1)

        self.log_btn = QPushButton("?")
        self.log_btn.clicked.connect(self.on_log)
        self.log_btn.setVisible(False)
        hbox.addWidget(self.log_btn)
        
        self.vbox.addWidget(hbox_w)
        
        self.vbox.addStretch()

        self.setLayout(self.vbox)

    def reset(self):
        # reset label above
        self.result.setStyleSheet("");
        self.result.setText("")
        self.log_btn.setVisible(False)
        # reset progress bar
        self.progress.setValue(0)
        self.lbl.setText("Idle")
        
    def setPort(self, port):
        self.port = port
        
    def on_log(self):
        dialog = LogDialog(self.log, self.parent())
        dialog.exec_()
        
    def trigger_bootloader(self):
        self.set_state("bootloader")
        try:
            ser = serial.Serial()
            ser.port = self.port
            ser.baudrate = 1200
            ser.open()
            ser.setDTR(0)
            ser.close()
            time.sleep(2)
            
        except BrokenPipeError:
            # a BrokenPipe error happens on setDTR if the bootloader
            # is already active. So we ignore this
            ser.close()
        except serial.SerialException as e:
            self.log = "Serial I/O: " + e.strerror
            return False
        except:
            print(sys.exc_info())
            self.log = "Error starting bootloader: " + str(sys.exc_info()[0])
            return False

        return True

    def build_command(self, file, bootloader=False):
        path = os.path.dirname(os.path.realpath(__file__))
        # relative paths are relative to this python file
        if file and file[0] != '/':
            file = os.path.join(path,file)
        
        cmd = [ "avrdude", 
                "-C"+os.path.join(path,"avrdude.conf"),
                "-patmega32u4" ]
        
        if bootloader:
            cmd.extend( [ "-cusbasp", "-Pusb" ])
            
            if not file:
                cmd.extend( [ "-e",
                              "-Ulock:w:0x3F:m",
                              "-Uefuse:w:0xcb:m",
                              "-Uhfuse:w:0xd8:m",
                              "-Ulfuse:w:0xff:m" ])
            else:
                cmd.extend( [ "-Uflash:w:"+file+":i",
                              "-Ulock:w:0x2F:m" ] )
        else:
            cmd.extend( [ "-cavr109",
                          "-P"+self.port,
                          "-b57600",
                          "-D",
                          "-Uflash:w:"+file+":i" ])
            
        return cmd;
    
    def exec_command(self, commandline):
        self.buffer = ""
        self.state = None

        # run subprocess
        self.log_master_fd, self.log_slave_fd = pty.openpty()
        self.app_process = subprocess.Popen(commandline, stdout=self.log_slave_fd, stderr=self.log_slave_fd)
        
        # start a timer to monitor the ptys
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.on_output_timer)
        self.log_timer.start(1)

    def set_progress(self, perc):
        # don't show progress during first bootloader flash stage
        if not self.bootloader_file:
            self.progress.setValue(perc)

    def set_state(self, state):
        if state == "bootloader":
            self.lbl.setText("Starting loader ...")
        elif state == "erase":
            self.lbl.setText("Erasing ...")
        if not self.bootloader_file:
            if state == "write":
                self.lbl.setText("Writing ...")
            elif state == "verify":
                self.lbl.setText("Verifying ...")
            elif state == "done":
                self.lbl.setText("Upload finished")

    def set_result(self, state):
        if state == None:
            self.result.setStyleSheet("");
            self.result.setText("in progress ...")
            self.log_btn.setVisible(False)
        elif state == False:
            self.result.setStyleSheet("QLabel { background-color : red; }");
            self.result.setText("Failure!")
            self.log_btn.setVisible(True)
        elif state == True:
            self.result.setStyleSheet("QLabel { background-color : green; }");
            self.result.setText("Success")
            self.log_btn.setVisible(False)
            
    def parse_line(self, str):
        # check for state indicators
        if str.startswith("avrdude"):
            parts = str.split()
            if parts[1] == "writing" and parts[2] == "flash":
                self.state = "write"
                self.set_state(self.state)
            if parts[1] == "reading" and parts[2] == "on-chip":
                self.state = "verify"
                self.set_state(self.state)
            if parts[1].startswith("done"):
                self.state = "done"
                self.set_state(self.state)
        
        if str.startswith("Reading") or str.startswith("Writing"):
            # this is a line that belongs to some ascii progress
            # bar. So we parse it for the progress bar widget
            perc = int(str.split('|')[2].strip().split()[0][:-1])
            if self.state == "write":
                self.set_progress(perc/2)
            if self.state == "verify":
                self.set_progress(50+perc/2)
        
    def parse_output(self, data):
        # append to log
        self.log = self.log + data.decode("utf-8")
        # append to buffer for line parsing
        self.buffer = self.buffer + data.decode("utf-8")
        lines = self.buffer.splitlines()
        # at least one full line in buffer?
        if len(lines) > 1:
            for i in lines[:-1]: self.parse_line(i)
            # keep last line in buffer, but keep \r if present
            self.buffer = self.buffer.splitlines(True)[-1]
        
    def app_is_running(self):
        if self.app_process == None:
            return False

        return self.app_process.poll() == None

    def on_output_timer(self):
        # read whatever the process may have written
        if select.select([self.log_master_fd], [], [], 0)[0]:
            output = os.read(self.log_master_fd, 100)
            if output: self.parse_output(output)
        else:
            # check if process is still alive
            if not self.app_is_running():
                # read all remaining data
                while select.select([self.log_master_fd], [], [], 0)[0]:
                    output = os.read(self.log_master_fd, 100)
                    if output: self.parse_output(output)
                    time.sleep(0.01)

                # close any open ptys
                os.close(self.log_master_fd)
                os.close(self.log_slave_fd)

                # remove timer
                self.log_timer = None

                # if this was only the first of the two bootloader
                # steps then only report errors
                if self.bootloader_file:
                    if self.app_process.returncode:
                        self.set_result(False)
                        self.done.emit(False)
                    else:
                        # start second bootloader step
                        self.log = ""
                        cmd = self.build_command(self.bootloader_file, True)
                        self.bootloader_file = None
                        self.exec_command(cmd)
                else:
                    self.set_result(self.app_process.returncode == 0)
                    self.done.emit(self.app_process.returncode == 0)
                
    def flash(self, file, bootloader=False):
        self.log = ""
        self.bootloader_file = None
        self.set_result(None)
        if not bootloader:
            cmd = self.build_command(file, False)
            self.exec_command(cmd)
        else:
            self.set_state("erase")
            # send preparation command, make sure file is sent afterwards
            self.bootloader_file = file
            cmd = self.build_command(None, True)
            self.exec_command(cmd)

# =========================== Test user interface =====================
            
class FtcGuiApplication(TxtApplication):
    def __init__(self, args):
        TxtApplication.__init__(self, args)

        # create the empty main window
        self.w = TxtWindow("Dude")

        vbox_w = QWidget()
        vbox = QVBoxLayout()
        
        self.avrdude = AvrdudeWidget(self.w)
        self.avrdude.setPort("/dev/ttyACM0")
        vbox.addWidget(self.avrdude)

        vbox.addStretch()

        btn = QPushButton("Bootloader")
        btn.clicked.connect(self.on_bootloader_flash)
        vbox.addWidget(btn)
        
        btn = QPushButton("Blink")
        btn.clicked.connect(self.on_blink_flash)
        vbox.addWidget(btn)
        
        vbox_w.setLayout(vbox)
        self.w.setCentralWidget(vbox_w)
 
        self.w.show() 
        self.exec_()        

    def on_bootloader_flash(self):
        self.avrdude.flash("bootloader/Caterina.hex", True)

    def on_blink_flash(self):
        self.avrdude.trigger_bootloader()
        self.avrdude.flash("binaries/Blink.ino.hex")
        
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
