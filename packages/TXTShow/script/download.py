#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import cgi, shutil
import sys, os, shlex, time, json
from subprocess import Popen, call, PIPE

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
            print('<head></head><body>failed</body></html>')
    #else: print("jibbet nit")
            
# *************************
# * ab hier geht's los... *
# *************************
      
form = cgi.FieldStorage()

"""loc=""
if "lang" in form:
    if form["lang"].value=="de":
        f = open(".locale","w")
        f.write("de")
        f.close
    else:
        f = open(".locale","w")
        f.write("en")
        f.close

if os.path.isfile(".locale"):
    f = open(".locale","r")
    loc = f.read()
    f.close()

if loc=="": loc="en"
"""

   
if ("file" in form) and ("path" in form):
    send_file(form["path"].value, form["file"].value)
else:
        print('Content-Type: text/html')
        print('')
        print('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')
        print('<html xmlns="http://www.w3.org/1999/xhtml">')
        print('<head></head><body>Doof</body></html>')
