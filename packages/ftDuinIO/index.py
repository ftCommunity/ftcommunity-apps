#!/usr/bin/python3
# -*- coding: utf-8 -*-

import htmlhelper as hth
import cgi, os, json, sys
from codecs import *

def mainpage():
    hth.htmlhead("ftDuinIO", "ftDuino I/O test and flash tool")
    hth.lf(1)
    print('<img src="icon.png">')
    hth.lf(1)
    hth.separator()
    hth.lf(1)
    print('Upload .ino.hex binary file to the local cache:<br><br>')
    print('<form action="index.py" method="post" enctype="multipart/form-data">')
    print('<label>')
    hth.text("hex file:")         
    print('<input name="project" type="file" size="50" accept="application/zip,application/x-zip,application/x-zip-compressed"> </label>')
    print('<button type="submit">')
    hth.text("Upload!")
    print('</button></form>')
    
    hth.lf(1)  
    hth.separator()
    hth.htmlfoot("","/","TXT Home")

def uploader(fileitem):
    
    filename = fileitem.filename    
    
    filename = "binaries/"+filename
    
    if 1: #try:
        open(filename, 'wb').write(fileitem.file.read())
        os.chmod(filename,0o666)
        hth.htmlhead("ftDuinIO", "Upload finished!")
        hth.htmlfoot("","index.py","Back")
    else: #except:
        hth.htmlhead("ftDuinIO", "Upload failed")
        hth.htmlfoot("","index.py","Back")

        
# *****************************************************
# *************** Ab hier geht's los ******************
# *****************************************************

if __name__ == "__main__":
    
    form = cgi.FieldStorage()

    if "project" in form:
        uploader(form["project"])

    else:
        mainpage()
    
    
