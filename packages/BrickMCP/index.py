#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import cgi, shutil
import sys, os
import ba
import xml.etree.ElementTree as et
import zipfile as z


hostdir = os.path.dirname(os.path.realpath(__file__)) + "/"
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

def getkey(feed):
    return feed[1]
  
def scan_brickly():
    global bricks
    
    bricks=[]
    a=0
    if os.path.exists(brickdir):
        stack=os.listdir(brickdir)
        for l in stack:

            if ("brickly" in l) and (".xml" in l): 
                name=""
                xml=et.parse(brickdir+l).getroot()
                for child in xml:
                    # remove any namespace from the tag
                    if '}' in child.tag: child.tag = child.tag.split('}', 1)[1]
                    if child.tag == "settings" and 'name' in child.attrib:
                        name = child.attrib['name']
                if name != "": bricks.append((l,name))
                
        bricks=sorted(bricks, key=getkey)   

def brickly_not_found():
    # html head ausgeben
    if loc=="de":        ba.htmlhead("BrickMCP", "Verwalte Deine Brickly Projekte")
    elif loc=="fr":      ba.htmlhead("BrickMCP", "Organiser vos projets Brickly")
    else:                ba.htmlhead("BrickMCP", "Manage your Brickly projects")
    
    print("</p><hr></p>")
    
    if loc=="de":        print("Brickly konnte auf diesem TXT nicht gefunden werden!")
    elif loc=="fr":      print("Brickly introuvable sur ce TXT.")
    else:                print("Brickly could not be found on this TXT.")

    print("</p><hr></p>")

    # html abschließen
    if loc=="de":        ba.htmlfoot("",  "/",  "TXT Home")
    elif loc=="fr":      ba.htmlfoot("",  "/",  "TXT Home")
    else:                ba.htmlfoot("",  "/",  "TXT Home")


def indexpage():
    # html head ausgeben
    if loc=="de":        ba.htmlhead("BrickMCP", "Verwalte Deine Brickly Projekte")
    elif loc=="fr":      ba.htmlhead("BrickMCP", "Organiser vos projets Brickly")
    else:                ba.htmlhead("BrickMCP", "Manage your Brickly projects")
    
    # brickly-projekte scannen
    scan_brickly()
    
    # liste bauen
    if loc=="de":        print("<hr /></p><b>Auf dem TXT gefundene Brickly Projekte:</b><br>Anklicken zum Herunterladen.<br><br>")
    elif loc=="fr":      print("<hr /></p><b>Brickly projets trouv&eacute;s sur le TXT:</b><br>Cliquez pour t&eacute;l&eacute;charger, svp.<br><br>")
    else:                print("<hr /></p><b>Brickly projects found on this TXT:</b><br>Click to download.<br><br>")
    
    print('<table border="1" rules="rows" cellpadding="5">')
    print('<thead><tr>')
    
    if loc=="de":       print('<th>Projekt</th><th>Download</th><th>L&ouml;schen</th></tr>')
    elif loc=="fr":     print('<th>Projet</th><th>T&eacute;l&eacute;charger</th><th>Supprimer</th></tr>')
    else:               print('<th>Project</th><th>Download</th><th>Delete</th></tr>')
    
    print('</thead>')
    print('<tbody>')
    
    
    for b in bricks:
        
        print('<tr>')
        
        # erste Spalte
        print('<td>')
        
        print("<a href='ba.py?file=" + b[0] + "&path=" + brickdir + "&brickpack=True'>" + b[1] + "</a>")
        
        print('</td>')
        
        #zweite Spalte
        print('<td>')
        
        print("<center><a href='ba.py?file=" + b[0] + "&path=" + brickdir + "&brickpack=True'>" + "<img src='download.png'>" + "</a></center>")
        
        print('</td>')        
        
        # dritte Spalte
        print('<td>')
        
        if loc=="de":   print("<center><a href='index.py?del=" + b[0] + "' onclick='return confirm(" + '"' + "Soll das Projekt "  + b[1] + ' wirklich gel&ouml;scht werden?"'+")'><img src='remove.png'></a></center>")
        elif loc=="fr": print("<center><a href='index.py?del=" + b[0] + "' onclick='return confirm(" + '"' + "Voulez-vous vraiment supprimer le projet "  + b[1] + '?"'+")'><img src='remove.png'></a></center>")
        else:           print("<center><a href='index.py?del=" + b[0] + "' onclick='return confirm(" + '"' + "Do you really want to delete "  + b[1] + '?"'+")'><img src='remove.png'></a></center>")
        
        print('</td>')
        
        # Ende der Zeile
        print('</tr')
    
    # Ende divTableBody
    if loc=="de":       print('<tr><td colspan="3"><center>Ende der Liste</center></td></tr')
    elif loc=="fr":     print('<tr><td colspan="3"><center>Fin de la liste</center></td></tr>')
    else:               print('<tr><td colspan="3"><center>End of the list</center></td></tr>')
    print('</tbody>')
    
    # Ende divTable
    print('</table>')
        
    print("<hr /><br>")
    
    if loc=="de":
        print('<form action="index.py" method="post" enctype="multipart/form-data">')
        print('<label>Brickly Projekt auf TXT laden (*.zip):')
        print('<input name="datei" type="file" size="50" accept="application/zip,application/x-zip,application/x-zip-compressed"> </label>')
        print('<button type="submit">Hochladen</button></form>')
    elif loc=="fr":
        print('<form action="index.py" method="post" enctype="multipart/form-data">')
        print('<label>Envoyer un fichier de projet Brickly au TXT (*.zip):')
        print('<input name="datei" type="file" size="50" accept="application/zip,application/x-zip,application/x-zip-compressed"> </label>')
        print('<button type="submit">Envoyer</button></form>')
    else:
        print('<form action="index.py" method="post" enctype="multipart/form-data">')
        print('<label>Select a Brickly project to upload to the TXT (*zip):')
        print('<input name="datei" type="file" size="50" accept="application/zip,application/x-zip,application/x-zip-compressed"> </label>')
        print('<button type="submit">Upload</button></form>')
        
    # html abschließen
    if loc=="de":        ba.htmlfoot("Viel Spa&szlig;",        "/",    "TXT Home")
    elif loc=="fr":      ba.htmlfoot("Amusez-vous",      "/",    "TXT Home")
    else:                ba.htmlfoot("Have fun",         "/",    "TXT Home")

def upload(fileitem):

    if not fileitem.filename:
        return False,"No valid file"

    m=os.getcwd()
    os.chdir(brickdir)
        
    filename = fileitem.filename    
    
    open(filename, 'wb').write(fileitem.file.read())
    os.chmod(filename,0o666)
    
    if os.path.isfile(".xml"):
        os.remove(".xml")
    if os.path.isfile(".py"):
        os.remove(".xml")
    if os.path.isfile(".readme"):
        os.remove(".readme")
    
    zf=z.ZipFile(filename,"r")
    zf.extractall()
    zf.close()
    
    i=1
    while (os.path.isfile("brickly-"+str(i)+".py")) or (os.path.isfile("brickly-"+str(i)+".xml")):
      i=i+1
      
    if os.path.isfile(".xml"):
        shutil.copyfile(".xml", "brickly-"+str(i)+".xml")
        os.remove(".xml")
    if os.path.isfile(".py"):
        shutil.copyfile(".py", "brickly-"+str(i)+".py")
        os.remove(".py")
    if os.path.isfile(".readme"):
        os.remove(".readme")
    
    os.remove(filename)
    os.chdir(m)

def remove(brick):
    
    m=os.getcwd()
    os.chdir(brickdir)
    
    if os.path.isfile(brick):

        os.remove(brick)
    if os.path.isfile(brick[:-4]+".py"):

        os.remove(brick[:-4]+".py")


    os.chdir(m)
   
    
# *****************************************************
# *************** Ab hier geht's los ******************
# *****************************************************

if __name__ == "__main__":
   
    form = cgi.FieldStorage()
    
    loc=""
    if "lang" in form:
        if form["lang"].value=="de":
            f = open(".locale","w")
            f.write("de")
            f.close
        elif form["lang"].value=="fr":
            f = open(".locale","w")
            f.write("fr")
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
    
    # Abbrechen, wenn Brickly nicht installiert...
    
    if not os.path.exists(brickdir):
        brickly_not_found()
        exit()


    if "del" in form:
        remove(form["del"].value)
        indexpage()
    elif "datei" in form:
        upload(form["datei"])
        indexpage()
    else:
        indexpage()