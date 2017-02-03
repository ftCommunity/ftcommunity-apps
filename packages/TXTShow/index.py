#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import cgi, shutil
import sys, os, shlex, time, json
from PyQt4 import QtGui, QtCore
from subprocess import Popen, call, PIPE

hostdir = os.path.dirname(os.path.realpath(__file__)) + "/"
local = ""
picsdir = local + "pics/"

def run_program(rcmd):
    """
    Runs a program, and it's paramters (e.g. rcmd="ls -lh /var/www")
    Returns output if successful, or None and logs error if not.
    """

    cmd = shlex.split(rcmd)
    executable = cmd[0]
    executable_options=cmd[1:]    

    try:
        proc  = Popen(([executable] + executable_options), stdout=PIPE, stderr=PIPE)
        response = proc.communicate()
        response_stdout, response_stderr = response[0].decode('UTF-8'), response[1].decode('UTF-8')
    except OSError as e:
        if e.errno == errno.ENOENT:
            print( "Unable to locate '%s' program. Is it in your path?" % executable )
        else:
            print( "O/S error occured when trying to run '%s': \"%s\"" % (executable, str(e)) )
    except ValueError as e:
        print( "Value error occured. Check your parameters." )
    else:
        if proc.wait() != 0:
            print( "Executable '%s' returned with the error: \"%s\"" %(executable,response_stderr) )
            return response
        else:
            #print( "Executable '%s' returned successfully." %(executable) )
            #print( " First line of response was \"%s\"" %(response_stdout.split('\n')[0] ))
            return response_stdout

def scan_directories():
    global dirstack
    dirs = os.listdir(picsdir)
    
    dirstack=list()
    
    for data in dirs:
        if os.path.isdir(picsdir + data): dirstack.append(data)
    
    dirstack.sort()

"""def save_uploaded_file():
    form = cgi.FieldStorage()
    if "datei" not in form:
        return False,"No file"

    fileitem = form["datei"]
    if not fileitem.file or not fileitem.filename:
        return False,"No valid file"

    filename = fileitem.filename
    
    if not os.path.exists(localdir+filename):
        print("Writing file to " + filename + "<br/>")
        open(localdir+filename, 'wb').write(fileitem.file.read())

        return True,filename
    else: 
        return False,None
"""

def create_html_head():
    print('Content-Type: text/html')
    print('')
    print('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')
    print('<html xmlns="http://www.w3.org/1999/xhtml">')
    print('<head>')
    print('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />')
    print('<meta http-equiv="cache-control" content="max-age=0" />')
    print('<meta http-equiv="cache-control" content="no-cache" />')
    print('<meta http-equiv="expires" content="0" />')
    print('<meta http-equiv="expires" content="Tue, 01 Jan 1980 1:00:00 GMT" />')
    print('<meta http-equiv="pragma" content="no-cache" />')
    print('<title>TXTShow</title>')
    print('<link rel="stylesheet" href="/txt.css" />')
    print('<link rel="icon" href="/favicon.ico" type="image/x-icon" />')
    print('</head>')
    
    print('<body>')
       
    print('<center>')

    print('<h1><div class="outline"><font color="red">fischer</font><font color="#046ab4">technik</font>&nbsp;<font color="#fcce04">TXT</font></div></h1>')
    
    print('<p/><h1>TXTShow</h1><p/>Present your images on the TXT<br>')

def create_html_output_dirs():
    global dirstack
    create_html_head()
    print('<div style="width:90%; height:296px; line-height:3em;overflow:scroll;padding:5px;background-color:#549adc;color:#0c6acc;border:4px solid #0c6acc;border-style: outset;">')
    
    for d in dirstack:
      print('<div title="'+d+'"; style="width:120px; float: left; padding: 2px; margin: 4px; border:1px #0c6acc solid; border-style: inset;">')
      print('<a href="index.py?ld='+d+'"><img style="border:1px #0c6acc solid; border-style: outset" src="'+"icons/folder-image-people.png"+'"><br>'+d+"</a><br>")
      print('<center><a href="index.py?rd='+d+'" onclick="return confirm('+"'"+'Really delete album <'+d+'>?'+"'"+')"><img src="remove.png"></a></center>')
      print('</div>')

    print('</div><br>')
    
    print('Click on an album to manage its contents.<br>Click <img src="remove.png"> to remove album from TXT <b>permanently.</b><br><br>')
    print('<form action="index.py" method="post" enctype="multipart/form-data">')
    print('<label>Create a new album:')
    print('<input name="newdir" type="text" size=12> </label>')
    print('<button type="submit">Add</button></form>')
    
    print('<br><br><a href="/"> TXT Home </a>')
    
    print('</body></html>')

def create_html_output_rd_fail():
    return

def create_html_output_pics(pdir):
    pic = os.listdir(picsdir+pdir)
 
    picstack=list()
    
    for data in pic:
        if os.path.exists(picsdir + pdir + "/" +data): picstack.append(data)
    
    picstack.sort()
    
    create_html_head()
    
    print('<form action="index.py" method="post" enctype="multipart/form-data">')
    print('<input name="directory" type="hidden" value="'+pdir+'">')
    print('<label>Current album is:')
    print('<input name="rendir" type="text" size=12 value="'+pdir+'"> </label>')
    print('<button type="submit">Rename</button></form>')
    print('<div style="width:90%; height:296px; line-height:3em;overflow:scroll;padding:5px;background-color:#549adc;color:#0c6acc;border:4px solid #0c6acc;border-style: outset;">')
    
    for pic in picstack:
      print('<div title="'+pic+'"; style="width:80; height:124px; float: left; padding: 2px; margin: 4px; border:1px #0c6acc solid; border-style: inset;"><a href="'+picsdir+pdir+"/"+pic+'">')
      print('<img style="border:1px #0c6acc solid; border-style: outset" src="'+picsdir+pdir+"/"+pic+'" height="96"></a><br>')
      print('<center><a href="index.py?rp='+pic+'&directory='+pdir+'" onclick="return confirm('+"'"+'Really delete image '+pic+'?'+"'"+')"><img src="remove.png"></a></center>')
      print('</div>')


    print('</div><br>')
    
    print('Click on the picture itself to view. Right-click to download.<br>Click <img src="remove.png"> to remove picture from TXT <b>permanently.</b><br><br>')
    print('Picture size should be 320x240 to 960x720. Mind the limited ressources of the TXT.<br>')
    print('<form action="index.py" method="post" enctype="multipart/form-data">')
    print('<input name="directory" type="hidden" value="'+pdir+'">')
    print('<label>Select a picture to add (*.png, *.jpg):')
    print('<input name="datei" type="file" size="50" accept="image/*"> </label>')
    print('<button type="submit">Add</button></form>')
    print('<br><br><a href="index.py"> Back to album list </a>')
    
    print('</body></html>')
    
def upload():    
    #create_html_head()
    #print('</div><p/>Uploading, please wait...<br>')
    #print('</body></html>')
    return

def save_uploaded_file(tdir):
    global form
    if "datei" not in form:
        return False,"No file"

    fileitem = form["datei"]
    if not fileitem.file or not fileitem.filename:
        return False,"No valid file"

    filename = fileitem.filename    
    
    if not os.path.exists(tdir+filename):
        open(tdir+filename, 'wb').write(fileitem.file.read())
        os.chmod(tdir+filename,0o666)
        return True, filename
    else:
        return False, None
    

def clean(newdir,maxlen):
    res=""
    valid="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_-."
    for ch in newdir:
        if ch in valid: res=res+ch
    return res[:maxlen]


form = cgi.FieldStorage()

if "ld" in form:
    create_html_output_pics(form["ld"].value)    
elif "rd" in form:
    #dummy = run_program("mv pics/" + form["r"].value+" pics/."+form["r"].value)
    scan_directories()
    if len(dirstack)>1:
      dummy = shutil.rmtree(hostdir+"pics/" + form["rd"].value)
      scan_directories()
      create_html_output_dirs()
    else:
      create_html_head()
      print("</p><b>"+form["rd"].value+"</b> is the last existing Album and can not be removed.")
      print("</p><a href="+'"'+"index.py"+'">'+"Back to album list</a></html></head>") 
elif "rp" in form:
    dummy = os.remove(hostdir+"pics/" + form["directory"].value+"/"+form["rp"].value)
    create_html_output_pics(form["directory"].value) 
elif "rendir" in form:
     if clean(form["rendir"].value,12)!="":
        dummy = os.rename(hostdir+"pics/" + form["directory"].value, hostdir+"pics/" + clean(form["rendir"].value,12))
        create_html_output_pics(clean(form["rendir"].value,12))
     else:
        create_html_output_pics(form["directory"].value)
elif "newdir" in form:
     if clean(form["newdir"].value,12)!="":
        dummy = os.mkdir(hostdir+"pics/" + clean(form["newdir"].value,12))
        dummy = os.chmod(hostdir+"pics/" + clean(form["newdir"].value,12),0o777)
        create_html_output_pics(clean(form["newdir"].value,12))
     else: 
       scan_directories()
       create_html_output_dirs()
elif "datei" in form:
    upload()

    (success,file)=save_uploaded_file("pics/"+form["directory"].value+"/")
    if success==True:
        create_html_output_pics(form["directory"].value)
    else:
        create_html_head()
        print("</p>Error uploading image! File already exists or no memory available.")
        print("</p><a href="+'"'+"index.py"+'">'+"Back to album list</a></html></head>") 
else:
    scan_directories()
    create_html_output_dirs()
