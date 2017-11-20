#!/usr/bin/python3
# -*- coding: utf-8 -*-

import translator as tr
import htmlhelper as hth
import cgi, os, json

def mainpage():
    hth.htmlhead("startIDE", tr.translate("Control your model with a finger touch"))
    print('<img src="icon.png">')
    hth.separator()
    hth.text(tr.translate("<b>Download</b> a"))
    hth.link(tr.translate("project"),"index.py?action=PDown")
    hth.text(tr.translate("or a"))
    hth.link(tr.translate("module"),"index.py?action=MDown")
    hth.text(tr.translate("from your TXT."))
    hth.lf(2)
    hth.text(tr.translate("<b>Upload</b> a"))
    hth.link(tr.translate("project"),"index.py?action=PUp")
    hth.text(tr.translate("or a"))
    hth.link(tr.translate("module"),"index.py?action=MUp")
    hth.text(tr.translate("to your TXT."))
    hth.lf(2)
    hth.text(tr.translate("<b>Show</b> a"))
    hth.link(tr.translate("project"),"index.py?action=PList")
    hth.text(tr.translate("or a"))
    hth.link(tr.translate("module"),"index.py?action=MList")
    hth.text(tr.translate("code listing."))
    hth.lf(2)
    hth.separator()
    hth.htmlfoot("","/","TXT Home")

def download(obj:str):
    if obj=="P": hth.htmlhead("startIDE", tr.translate("Download a project from your TXT"))
    elif obj=="M": hth.htmlhead("startIDE", tr.translate("Download a module from your TXT"))
    
    hth.separator()
    hth.lf()
    
    if obj=="P":
        hth.text(tr.translate("Please select project:"))
        hth.lf(2)
        downloadfiles("projects/")
    elif obj=="M":
        hth.text(tr.translate("Please select module:"))
        hth.lf(2)
        downloadfiles("modules/")
    hth.lf(2)
    hth.separator()
    hth.htmlfoot("","javascript:history.back()",tr.translate("Back"))

def upload(obj:str):
    if obj=="P": hth.htmlhead("startIDE", tr.translate("Upload a project  to your TXT"))
    elif obj=="M": hth.htmlhead("startIDE", tr.translate("Upload a module to your TXT"))
    
    hth.separator()
    hth.lf(2)
    
    if obj=="P": hth.text(tr.translate("Please select project:"))
    elif obj=="M": hth.text(tr.translate("Please select module:"))
    
    print('<form action="index.py" method="post" enctype="multipart/form-data">')
    print('<label>')
    
    if obj=="P":
        hth.text(tr.translate("Project file:"))
        print('<input name="project" type="file" size="50" accept="application/zip,application/x-zip,application/x-zip-compressed"> </label>')
    elif obj=="M":
        hth.text(tr.translate("Module file:"))
        print('<input name="module" type="file" size="50" accept="application/zip,application/x-zip,application/x-zip-compressed"> </label>')

    print('<button type="submit">')
    hth.text(tr.translate("Upload!"))
    print('</button></form>')

    hth.lf(2)
    hth.separator()
    hth.htmlfoot("","javascript:history.back()",tr.translate("Back"))

def codelist(obj:str):
    if obj=="P": hth.htmlhead("startIDE", tr.translate("Show a project code listing"))
    elif obj=="M": hth.htmlhead("startIDE", tr.translate("Show a module code listing"))
    
    hth.separator()
    hth.lf()

    if obj=="P":
        hth.text(tr.translate("Please select project:"))
        hth.lf(2)
        listfiles("projects/")
    elif obj=="M":
        hth.text(tr.translate("Please select module:"))
        hth.lf(2)
        listfiles("modules/")
    hth.lf(2)
    hth.separator()
    hth.htmlfoot("","javascript:history.back()",tr.translate("Back"))

def listfiles(directory:str):
    stack=os.listdir(directory)
    for a in stack:
        hth.link(a,"index.py?list="+directory+a)
        hth.lf()

def downloadfiles(directory:str):
    stack=os.listdir(directory)
    for a in stack:
        hth.link(a,directory+a,"download")
        hth.lf()    

def uploader(obj:str, fileitem):
    
    filename = fileitem.filename    
    
    if obj=="P": filename = "projects/"+filename
    elif obj=="M": filename = "modules/"+filename
    
    try:
        open(filename, 'wb').write(fileitem.file.read())
        os.chmod(filename,0o666)
        mainpage()
    except:
        hth.htmlhead("startIDE", tr.translate("Upload failed"))
        hth.htmlfoot("","index.py",tr.translate("Back"))

def filelister(name:str):
    print('Content-Type: text/plain')
    print('')

    print("  startIDE code listing: "+name)
    print("  ======================")
    print('')
    with open(name,"r", encoding="utf-8") as f:
        code=json.load(f)
        a=0
        for i in code:
            a=a+1
            print("%5i:  %s" % (a,i))
        
# *****************************************************
# *************** Ab hier geht's los ******************
# *****************************************************

if __name__ == "__main__":
    
    form = cgi.FieldStorage()
#    hth.htmlhead("startIDE", tr.translate("Upload a project  to your TXT"))
#    print(form)
#    hth.htmlfoot("","/","TXT Home")
    
    if "action" in form:
        if form["action"].value=="PDown": download("P")
        if form["action"].value=="MDown": download("M")
        if form["action"].value=="PUp": upload("P")
        if form["action"].value=="MUp": upload("M")
        if form["action"].value=="PList": codelist("P")
        if form["action"].value=="MList": codelist("M")
    elif "module" in form:
        uploader("M", form["module"])
    elif "project" in form:
        uploader("P", form["project"])
    elif "list" in form:
        filelister(form["list"].value)
    else:
        mainpage()
    
    
