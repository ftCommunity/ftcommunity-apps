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

brickdir = hostdir + "../1f2d90a3-11e9-4a92-955a-73ffaec0fe71/user/"

# für die Entwicklungsumgebung PeH
if not os.path.exists(brickdir):
    brickdir = hostdir + "../../1f2d90a3-11e9-4a92-955a-73ffaec0fe71/user/"

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
    #print('<pre>' + sys.stdout.encoding + '</pre>')    
    print('<center>')
    print('<h1><div class="outline"><font color="red">fischer</font><font color="#046ab4">technik</font>&nbsp;<font color="#fcce04">TXT</font></div></h1>')    
    print('<p/><h1>' + progname + '</h1><p/>' + headtext + '<br>')

def htmlfoot(message:str, footlink:str, footlinktext:str):
    print('<p/>' + message)
    print('<p/><a href="' + footlink + '">' + footlinktext + "</a>")
    print("</body></html>")

def confirm_lock():
    # html head ausgeben
    if loc=="de":        htmlhead("BrickMCP", "Verwalte Deine Brickly Projekte")
    elif loc=="fr":      htmlhead("BrickMCP", "Organiser vos projets Brickly")
    else:                htmlhead("BrickMCP", "Manage your Brickly projects")
    
    print("<br><hr /><br><b>")
    
    if loc=="de":       print('BrickMCP ist jetzt gesperrt. Entsperren ist nur mit dem Passwort m&ouml;glich.')
    elif loc=="fr":     print('BrickMCP est verrouill&eacute;. Le d&eacute;verrouillage est seulement possible avec le mot de passe.')
    else:               print('BrickMCP is now locked. Unlocking is only possible by entering the password.')  
    
    print("<br><br><hr /><br>")
    
    if loc=="de":        htmlfoot("", "index.py",    "Okay")
    elif loc=="fr":      htmlfoot("", "index.py",    "Compris")
    else:                htmlfoot("", "index.py",    "Okay")


def lock():
    # html head ausgeben
    if loc=="de":        htmlhead("BrickMCP", "Verwalte Deine Brickly Projekte")
    elif loc=="fr":      htmlhead("BrickMCP", "Organiser vos projets Brickly")
    else:                htmlhead("BrickMCP", "Manage your Brickly projects")
    
    print("<br><hr /><br><b>")
    
    if loc=="de":       print('BrickMCP wird durch ein Passwort gesperrt. Entsperren ist nur mit diesem Passwort m&ouml;glich.')
    elif loc=="fr":     print('BrickMCP est verrouill&eacute; par un mot de passe. Le d&eacute;verrouillage est seulement possible avec ce mot de passe.')
    else:               print('BrickMCP will be locked with a password. Unlocking is only possible by entering the password.')   
    
    print("</b><br>")

    print('<form action="ba.py" method="post" enctype="multipart/form-data">')
    print('<input name="lockTXT" type="hidden" value="False">')
    print('<table border="0"><tr><td style="text-align: right;">')
    
    if loc=="de":
        print('<label>Passwort zum Sperren:<input name="password" type="password" size=12></label><br>')
        print('<label>Passwort best&auml;tigen:<input name="confpass" type="password" size=12></label>')
        print('</td><td>')
        print('<button type="submit"><img src="icons/document-encrypt.png" alt="Sperren"></button>')
    elif loc=="fr":
        print('<label>Mot de passe pour verrouiller:<input name="password" type="password" size=12></label><br>')
        print('<label>Confirmer le mot de passe:<input name="confpass" type="password" size=12></label>')
        print('</td><td>')
        print('<button type="submit"><img src="icons/document-encrypt.png" alt="Verroulier"></button>')
    else:
        print('<label>Enter password to lock:<input name="password" type="password" size=12></label><br>')
        print('<label>Confirm password:      <input name="confpass" type="password" size=12></label>')
        print('</td><td>')
        print('<button type="submit"><img src="icons/document-encrypt.png" alt="Lock"></button>')
    
    print('</td></tr></table>')
    print('</form>')

    print("<br><hr /><br>")
    
    if loc=="de":        htmlfoot("", "index.py",    "Nicht verriegeln")
    elif loc=="fr":      htmlfoot("", "index.py",    "Ne pas verrouiller")
    else:                htmlfoot("", "index.py",    "Do not lock")

def pwfail():
    
    # html head ausgeben
    if loc=="de":        htmlhead("BrickMCP", "Verwalte Deine Brickly Projekte")
    elif loc=="fr":      htmlhead("BrickMCP", "Organiser vos projets Brickly")
    else:                htmlhead("BrickMCP", "Manage your Brickly projects")
    
    print("<br><hr /><br><b>")

    if loc=="de":       print('Passw&ouml;rter stimmen nicht &uuml;berein! Bitte nochmal versuchen.')
    elif loc=="fr":     print('Les mots de passe ne correspondent pas. S&rsquo;il vous pla&icirc;t essayer &agrave; nouveau.')
    else:               print('Passwords do not match. Please try again.')   
    
    print("<br><br><hr /><br><b>")

    if loc=="de":        htmlfoot("", "ba.py?lockTXT=True",    "Nochmal versuchen")
    elif loc=="fr":      htmlfoot("", "ba.py?lockTXT=True",    "De nouveau")
    else:                htmlfoot("", "ba.py?lockTXT=True",    "Try again")

def do_brickpack(path:str, bf:str):
    m=os.getcwd()
    os.chdir(path)
    
    s1=0
    if os.path.isfile(os.path.basename(bf)):
        shutil.copyfile(os.path.basename(bf), ".xml")
        s1=os.path.getsize(".xml") % 171072
    if os.path.isfile(os.path.basename(bf)[:-4]+".py"):
        shutil.copyfile(os.path.basename(bf)[:-4]+".py", ".py")
        s1=s1+os.path.getsize(".py") % 171072
    
    vers="n/a"
    if os.path.exists("../manifest"):
        fi=open("../manifest","r")
        r =fi.readline()
        while r!="":
            if "version" in r: vers = r
            r=fi.readline()
        fi.close()
        
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
        fi.writestr(".mcpchecksum",str(s1))
        fi.writestr(".bricklyversion",vers)
    fi.close()
    send_file(path,"Brickly-"+name+".zip")
    os.remove("Brickly-"+name+".zip")
    os.chdir(m)


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

    loc=""
    if os.path.isfile(".locale"):
        f = open(".locale","r")
        loc = f.read()
        f.close()

    if loc=="": loc="en"
    
    
    if ("file" in form) and ("path" in form):
        path=form["path"].value
        bf = form["file"].value
        if "brickpack" in form:
            do_brickpack(path,bf)
        else:
            send_file(form["path"].value, form["file"].value)
    elif "confpass" in form:
        if form["password"].value==form["confpass"].value:
            f=open(brickdir+".mcplock","w")
            f.write(form["password"].value)
            f.close()
            confirm_lock()
        else:
            pwfail()
    elif "lockTXT" in form:
        if form["lockTXT"].value=="True":
            lock()
    else:
            print('Content-Type: text/html')
            print('')
            print('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')
            print('<html xmlns="http://www.w3.org/1999/xhtml">')
            print('<head></head><body>cgi script error. wrong objective or unknown command.</body></html>')