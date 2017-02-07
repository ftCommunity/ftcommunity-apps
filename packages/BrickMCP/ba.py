#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

# **********************************
# * support module for brickmcp.py *
# **********************************

import cgi, shutil
import sys, os, shlex, time
import zipfile as z
from string import *
import xml.etree.ElementTree as et

hostdir = os.path.dirname(os.path.realpath(__file__)) + "/"
local = ""

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

def send_file(path:str, filename:str):
    
    if os.path.exists(path+filename):
        
        g = open(path+filename,'rb')
        if g:
            print("Content-type: application/octet-stream")
            print("Content-Disposition: attachment; filename=%s" %(filename))
            print('')
            sys.stdout.flush()   
            shutil.copyfileobj(g, sys.stdout.buffer)
            sys.stdout.flush() 
            g.close() 
        else:
            print('Content-Type: text/html')
            print('')
            print('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')
            print('<html xmlns="http://www.w3.org/1999/xhtml">')
            print('<head></head><body>failed to send</body></html>')
    else:
        print('Content-Type: text/html')
        print('')
        print('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')
        print('<html xmlns="http://www.w3.org/1999/xhtml">')
        print('<head></head><body>file not found on TXT</body></html>')

def htmlhead(progname:str, headtext:str):
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
    print('<title>' + progname + '</title>')
    print('<link rel="stylesheet" href="/txt.css" />')
    print('<link rel="icon" href="/favicon.ico" type="image/x-icon" />')
    print('</head>')
    print('<body>')    
    print('<center>')
    print('<h1><div class="outline"><font color="red">fischer</font><font color="#046ab4">technik</font>&nbsp;<font color="#fcce04">TXT</font></div></h1>')    
    print('<p/><h1>' + progname + '</h1><p/>' + headtext + '<br>')

def htmlfoot(message:str, footlink:str, footlinktext:str):
    print('<p/>' + message)
    print('<p/><a href="' + footlink + '">' + footlinktext + "</a>")
    print("</body></html>")

def clean(newdir,maxlen):
    res=""
    valid="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_-."
    for ch in newdir:
        if ch in valid: res=res+ch
    return res[:maxlen]

# ***********************
# * Als cgi aufgerufen: *
# ***********************

if __name__ == "__main__":
    
    form = cgi.FieldStorage()
    
    if ("file" in form) and ("path" in form):
        path=form["path"].value
        bf = form["file"].value
        if "brickpack" in form:
            m=os.getcwd()
            os.chdir(path)
            
            if os.path.isfile(os.path.basename(bf)):
                shutil.copyfile(os.path.basename(bf), ".xml")
            if os.path.isfile(os.path.basename(bf)[:-4]+".py"):
                shutil.copyfile(os.path.basename(bf)[:-4]+".py", ".py")
            
            name=""
            xml=et.parse(bf).getroot()
            for child in xml:
                # remove any namespace from the tag
                if '}' in child.tag: child.tag = child.tag.split('}', 1)[1]
                if child.tag == "settings" and 'name' in child.attrib:
                    name = child.attrib['name']           
            
            fi = z.ZipFile("Brickly-"+name+".zip","w")
            if os.path.isfile(".xml"):
                fi.write(".xml")
                os.remove(".xml")
                if os.path.isfile(".py"):
                    fi.write(".py")
                    os.remove(".py")
                fi.writestr(".readme","Brickly ZIP file created by BrickMCP")
            fi.close()
            send_file(path,"Brickly-"+name+".zip")
            os.remove("Brickly-"+name+".zip")
            os.chdir(m)
        else:
            send_file(form["path"].value, form["file"].value)
    else:
            print('Content-Type: text/html')
            print('')
            print('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')
            print('<html xmlns="http://www.w3.org/1999/xhtml">')
            print('<head></head><body>cgi script error. did not receive filename or path for download.</body></html>')