#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import cgi, shutil
import sys, os, socket
import ba
import xml.etree.ElementTree as et
import zipfile as z


hostdir = os.path.dirname(os.path.realpath(__file__)) + "/"
brickdir = hostdir + "../1f2d90a3-11e9-4a92-955a-73ffaec0fe71/user/"

# für die Entwicklungsumgebung PeH
if not os.path.exists(brickdir):
    brickdir = hostdir + "../../1f2d90a3-11e9-4a92-955a-73ffaec0fe71/user/"
    develop=True
else:
    develop=False
    
    
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
    

    
    # vtab
    print('<table border="0"><tr><td width="48px"></td><td>')
    
    print('<table width="500px" border="0" rules="rows" cellpadding="5">')
    print('<thead><tr>')
    
    if loc=="de":       print('<th width="20%">Projekt</th><th>Download</th><th>Sch&uuml;tzen</th>'+
                              '<th>Anheften</th><th>L&ouml;schen</th><th width="20px"></th></tr>')
    elif loc=="fr":     print('<th width="20%">Projet</th><th>T&eacute;l&eacute;charger</th><th>Extinguible</th>'+
                              '<th>Attacher</th><th>Supprimer</th><th width="20px"></th></tr>')
    else:               print('<th width="20%">Project</th><th>Download</th><th>Deleteable</th>'+
                              '<th>Sticky</th><th>Remove</th><th width="20px"></th></tr>')
    
    print('</thead>')
    print('</table>')
    
    print('<div style="height:110px; width:500px; overflow:auto;">')
    
    print('<table width="480px" border="1" rules="rows" cellpadding="5">')
    
    for b in bricks:
        
        print('<tr>')
        
        # erste Spalte
        print('<td width="20%">')
        
        print("<a href='ba.py?file=" + b[0] + "&path=" + brickdir + "&brickpack=True'>" + b[1] + "</a>")
        
        print('</td>')
        
        #zweite Spalte
        print('<td>')
        
        print("<center><a href='ba.py?file=" + b[0] + "&path=" + brickdir + "&brickpack=True'>" + "<img src='download.png'>" + "</a></center>")
        
        print('</td>')        
        
        # dritte Spalte
        print('<td>')
        
        (isdel,ismov)=islocked(b[0])
        
        if not isdel: print("<center><a href='index.py?lock=" + b[0] + "'>" + "<img src='icons/lock-disabled.png' alt='Lock'>" + "</a></center>")
        else:     print("<center><a href='index.py?lock=" + b[0] + "'>" + "<img src='icons/lock.png' alt='Unlock'>" + "</a></center>")
        
        print('</td>')
        
        # vierte Spalte
        print('<td>')
        
        if not ismov: print("<center><a href='index.py?move=" + b[0] + "'>" + "<img src='icons/immovable-disabled.png' alt='Fix'>" + "</a></center>")
        else:     print("<center><a href='index.py?move=" + b[0] + "'>" + "<img src='icons/immovable.png' alt='Move'>" + "</a></center>")
        
        print('</td>')
        
        
        # fünfte Spalte
        print('<td>')
        
        if loc=="de":   print("<center><a href='index.py?del=" + b[0] + "' onclick='return confirm(" + '"' + "Soll das Projekt "  + b[1] + ' wirklich gel&ouml;scht werden?"'+")'><img src='remove.png'></a></center>")
        elif loc=="fr": print("<center><a href='index.py?del=" + b[0] + "' onclick='return confirm(" + '"' + "Voulez-vous vraiment supprimer le projet "  + b[1] + '?"'+")'><img src='remove.png'></a></center>")
        else:           print("<center><a href='index.py?del=" + b[0] + "' onclick='return confirm(" + '"' + "Do you really want to delete "  + b[1] + '?"'+")'><img src='remove.png'></a></center>")
        
        print('</td>')
        
        # Ende der Zeile
        print('</tr>')
    
    # Ende divTableBody
    if loc=="de":       print('<tr><td colspan="5"><center>Ende der Liste</center></td></tr')
    elif loc=="fr":     print('<tr><td colspan="5"><center>Fin de la liste</center></td></tr>')
    else:               print('<tr><td colspan="5"><center>End of the list</center></td></tr>')
    print('</tbody>')
    
    # Ende divTable
    print('</table>')

    print('</div>')
    
    print('</td><td align="center">')    
    print('<a href="index.py"><img src="icons/view-refresh.png"></a><br>')
    print('</td></tr></table>')    
        
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

    # lock-funktion
    print("<br><hr /><br>")
    
    print('<table border="0"><tr><td>')
    
    print('<a href="ba.py?lockTXT=True">')
    print('<img src="icons/document-encrypt.png"></a>')
    print('</td><td>')
    
    if loc=="de":
        print('BrickMCP auf diesem TXT verriegeln - Zugriff mit BrickMCP ist dann gesperrt.<br>Projekte in Brickly selbst k&ouml;nnen aber bearbeitet werden.')
    elif loc=="fr":
        print("Serrure BrickMCP sur cet appareil - L&rsquo;acc&egrave;s &agrave; BrickMCP est alors verrouill&eacute;.<br>Projets en Brickly lui-m&ecirc;me mais peuvent &ecirc;tre modifi&eacute;s.")
    else:
        print('Lock BrickMCP on this TXT - Access with BrickMCP will be blocked.<br>Projects can still be accessed within Brickly itself.')
    
    print('</td></tr>')
    print('</table>')
    
    # html abschließen    
    print("<br><hr /><br>")
    
    print("<a href='../1f2d90a3-11e9-4a92-955a-73ffaec0fe71/index.html'>[ Brickly ]</a><br>")
    ba.htmlfoot("", "/", "[ TXT Home] ")

def cleanup():
    if os.path.isfile(".xml"):
        os.remove(".xml")
    if os.path.isfile(".py"):
        os.remove(".py")
    if os.path.isfile(".readme"):
        os.remove(".readme")
    if os.path.isfile(".bricklyversion"):
        os.remove(".bricklyversion")
    if os.path.isfile(".mcpchecksum"):
        os.remove(".mcpchecksum")

def upload(fileitem):

    if not fileitem.filename:
        return False,"No valid file"

    m=os.getcwd()
    os.chdir(brickdir)
        
    filename = fileitem.filename    
    
    open(filename, 'wb').write(fileitem.file.read())
    os.chmod(filename,0o666)
    
    cleanup()
        
    zf=z.ZipFile(filename,"r")
    if ".readme" in zf.namelist():
        zf.extract(".readme")
        t=open(".readme","r")
        if t.read()!="Brickly ZIP file created by BrickMCP":
            os.remove(filename)
            os.chdir(m)
            upload_error("nab")
            return
        t.close()
        os.remove(".readme")
    else: 
          os.remove(filename)
          os.chdir(m)
          upload_error("nab")
          return
        
    #zf.extractall()
    if ".xml" in zf.namelist():
        zf.extract(".xml")
    else: 
        os.remove(filename)
        os.chdir(m)
        upload_error("nab")
        return
    
    if ".py" in zf.namelist():
        zf.extract(".py")
    if ".mcpchecksum" in zf.namelist():
        zf.extract(".mcpchecksum")
    if ".bricklyversion" in zf.namelist():
        zf.extract(".bricklyversion")
    zf.close()
    
    # find an empty slot
    i=1
    while (os.path.isfile("brickly-"+str(i)+".py")) or (os.path.isfile("brickly-"+str(i)+".xml")):
      i=i+1
    
    # calculate checksum on upladed brickly files
    s1=0
    if os.path.isfile(".xml"):
        s1=os.path.getsize(".xml") % 171072
    if os.path.isfile(".py"):
        s1=s1+os.path.getsize(".py") % 171072
    
    # get checksum from zip file
    s0=0
    if os.path.exists(".mcpchecksum"):
        fi=open(".mcpchecksum","r")
        r =fi.readline()
        s0=int(r)
        fi.close()
    
    # get brickly version from zip file
    ulvers=""
    if os.path.exists(".bricklyversion"):
        fi=open(".bricklyversion","r")
        ulvers = fi.readline()
        fi.close()    
    
    
    # get brickly version from TXT
    vers="n/a"
    if os.path.exists("../manifest"):
        fi=open("../manifest","r")
        r =fi.readline()
        while r!="":
            if "version" in r: vers = r
            r=fi.readline()
        fi.close()
    
    # install uploaded brickly project
    if (ulvers==vers) and (s0==s1):
        if os.path.isfile(".xml"):
            shutil.copyfile(".xml", "brickly-"+str(i)+".xml")
        if os.path.isfile(".py"):
            shutil.copyfile(".py", "brickly-"+str(i)+".py")
        indexpage()
    elif (s0==0):
        if os.path.isfile(".xml"):
            shutil.copyfile(".xml", "brickly-"+str(i)+".xml")
        if os.path.isfile(".py"):
            shutil.copyfile(".py", "brickly-"+str(i)+".py")
        upload_error("cnf")
    elif (s0!=s1):
        upload_error("cnm")
    elif (ulvers!=vers) and (s0==s1):
        if os.path.isfile(".xml"):
            shutil.copyfile(".xml", "brickly-"+str(i)+".xml")
        if os.path.isfile(".py"):
            shutil.copyfile(".py", "brickly-"+str(i)+".py")
        upload_error("vnm")
        
    # remove all extracted files

    cleanup()

    os.remove(filename)
    os.chdir(m)
    
def upload_error(err:str):    
    # html head ausgeben
    if loc=="de":        ba.htmlhead("BrickMCP", "Verwalte Deine Brickly Projekte")
    elif loc=="fr":      ba.htmlhead("BrickMCP", "Organiser vos projets Brickly")
    else:                ba.htmlhead("BrickMCP", "Manage your Brickly projects")
    
    # Meldung ausgeben
    print('<hr /><br>')
    if err=="cnf":
        if loc=="de":
            print('<b>Checksumme nicht pr&uuml;fbar!</b><br>Das Projekt wurde trotzdem in Brickly hinzugef&uuml;gt, bitte sorgf&auml;ltig pr&uuml;fen, es k&ouml;nnte besch&auml;digt sein.') 
        elif loc=="fr":
            print('<b>Checksum n&rsquo;a pas pu &ecirc;tre v&eacute;rifi&eacute;!</b><br>Le projet a &eacute;t&eacute; ajout&eacute; de toute fa&ccedil;on &agrave; Brickly.<br>')
            print('S&rsquo;il vous pla&icirc;t v&eacute;rifier avec pr&eacute;caution car il peut &ecirc;tre d&eacute;fectueux.')
        else:
            print('<b>Checksum not validated.</b><br>Project was uploaded to Brickly, but please check carefully because it might be corrupted.')
    elif err=="cnm":
        if loc=="de":
            print('<b>Checksummen stimmen nicht &uuml;berein!</b><br>Das Projekt konnte nicht zu Brickly hinzugef&uuml;gt werden.') 
        elif loc=="fr":
            print('<b>Erreur de checksum!</b><br>Le projet n&rsquo;a pas pu &ecirc;tre ajout&eacute; &agrave; Brickly.')
        else:
            print('<b>Checksum does not match.</b><br>Project could not be added to Brickly.')
    elif err=="vnm":
        if loc=="de":
            print('<b>Brickly-Versionsnummern stimmen nicht &uuml;berein!</b><br>Das Projekt wurde trotzdem zu Brickly hinzugef&uuml;gt, bitte sorgf&auml;ltig pr&uuml;fen, es k&ouml;nnte besch&auml;digt sein.') 
        elif loc=="fr":
            print('<b>Les num&egrave;ros de version Brickly ne correspondent pas!</b><br>Le projet a &eacute;t&eacute; ajout&eacute; de toute fa&ccedil;on &agrave; Brickly.<br>')
            print('S&rsquo;il vous pla&icirc;t v&eacute;rifier avec pr&eacute;caution car il peut &ecirc;tre d&eacute;fectueux.')
        else:
            print('<b>Brickly version numbers do not match.</b><br>Project was added to Brickly anyway, but please check carefully because it might be corrupted.')        
    elif err=="nab":
        if loc=="de":
            print('<b>Die hochgeladene Datei ist kein Brickly-Projekt!</b>') 
        elif loc=="fr":
            print('<b>Le fichier t&eacute;l&eacute;charg&eacute; est pas projet Brickly!</b>')
        else:
            print('<b>The uploaded file is not a Brickly project!</b>')            
    
    # html foot
    print('<br><br><hr /><br>')
    if loc=="de":        ba.htmlfoot("", "index.py",    "Zur&uuml;ck")
    elif loc=="fr":      ba.htmlfoot("", "index.py",    "Au retour")
    else:                ba.htmlfoot("", "index.py",    "Back")

    
def remove(brick):
    
    m=os.getcwd()
    os.chdir(brickdir)
    
    if os.path.isfile(brick):
        os.remove(brick)
    if os.path.isfile(brick[:-4]+".py"):
        os.remove(brick[:-4]+".py")

    os.chdir(m)

def locked():
    # html head ausgeben
    if loc=="de":        ba.htmlhead("BrickMCP", "Verwalte Deine Brickly Projekte")
    elif loc=="fr":      ba.htmlhead("BrickMCP", "Organiser vos projets Brickly")
    else:                ba.htmlhead("BrickMCP", "Manage your Brickly projects")
    
    print("<br><hr /><br><b>")
    
    if loc=="de":       print('BrickMCP ist auf diesem Ger&auml;t gesperrt.')
    elif loc=="fr":     print('BrickMCP est verrouill&eacute; sur cet appareil')
    else:               print('BrickMCP is locked on this TXT.')   
    
    print("</b><br>")

    print('<form action="index.py" method="post" enctype="multipart/form-data">')
    print('<input name="lockTXT" type="hidden" value="False">')
    print('<table border="0"><tr><td>')
    
    if loc=="de":
        print('<label>Passwort zum Entsperren:')
        print('<input name="password" type="password" size=12> </label>')
        print('</td><td>')
        print('<button type="submit"><img src="icons/document-decrypt.png" alt="Entsperren"></button>')
    elif loc=="fr":
        print('<label>Enter password to unlock:')
        print('<input name="password" type="password" size=12> </label>')
        print('</td><td>')
        print('<button type="submit"><img src="icons/document-decrypt.png" alt="Unlock"></button>')
    else:
        print('<label>Enter password to unlock:')
        print('<input name="password" type="password" size=12> </label>')
        print('</td><td>')
        print('<button type="submit"><img src="icons/document-decrypt.png" alt="Unlock"></button>')
    
    print('</td></tr></table>')
    print('</form>')

    print("<br><hr /><br>")
    
    if loc=="de":        ba.htmlfoot("", "/",    "TXT Home")
    elif loc=="fr":      ba.htmlfoot("", "/",    "TXT Home")
    else:                ba.htmlfoot("", "/",    "TXT Home")

def islocked(brick:str):
    l=False
    m=False
    if os.path.isfile(brickdir+brick):    
        with open(brickdir+brick,"r", encoding='utf-8') as f:
            st=f.read()
            f.close()
        if 'deletable="false"' in st: l=True
        if 'movable="false"' in st: m=True
    return l,m
    
def change_lock(brick:str):
    m=os.getcwd()
    os.chdir(brickdir)
    
    if os.path.isfile(brick):
        # so, und jetzt wird's luschtyg...
        (lock,move)=islocked(brick)
        if lock:
            with open(brick,"r", encoding='utf-8') as f:
                st=f.read()
                f.close()
            st=st.replace('deletable="false" ', '')
            with open(brick, 'w', encoding="utf-8") as fi:
                fi.write(st)
                fi.close()
        else:
            with open(brick,"r", encoding='utf-8') as f:
                st=f.read()
                f.close()
            if 'deletable="true" ' in st:
                st=st.replace('deletable="true" ', '')
                st=st.replace('<block ', '<block deletable="false" ')
            else:  st=st.replace('<block ', '<block deletable="false" ')    
            with open(brick, 'w', encoding="utf-8") as fi:
                fi.write(st)
                fi.close()
    
    os.chdir(m)

def change_move(brick:str):
    m=os.getcwd()
    os.chdir(brickdir)
    
    if os.path.isfile(brick):
        # so, und jetzt wird's luschtyg...
        (lock,move)=islocked(brick)
        if move:
            with open(brick,"r", encoding='utf-8') as f:
                st=f.read()
                f.close()
            st=st.replace('movable="false" ', '')
            with open(brick, 'w', encoding="utf-8") as fi:
                fi.write(st)
                fi.close()
        else:
            with open(brick,"r", encoding='utf-8') as f:
                st=f.read()
                f.close()
            if 'movable="true" ' in st:
                st=st.replace('movable="true" ', '')
                st=st.replace('<block ', '<block movable="false" ')
            else:  st=st.replace('<block ', '<block movable="false" ')    
            with open(brick, 'w', encoding="utf-8") as fi:
                fi.write(st)
                fi.close()
    
    os.chdir(m)


def killTXTApp():
    if develop: return
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Connect to server and send data
        sock.connect(("localhost", 9000))
        sock.sendall(bytes("stop-app\n", "UTF-8"))
    except socket.error as msg:
        ba.htmlhead("BrickMCP","General Error")
        print("<h2>Unable to connect to Launcher!</h2>")
        print("<h2>" , msg, "</h1>")
        ba.htmlfoot("","/","TXT Home")        
    finally:
        sock.close()



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
    
    # APPschießen
    killTXTApp()
    
    # Überprüfen, ob BrickMCP gelockt ist...
    
    if "lockTXT" in form:
        if form["lockTXT"].value=="False":
            f=open(brickdir+".mcplock","r")
            if form["password"].value==f.read():
                f.close()
                os.remove(brickdir+".mcplock")
            else:
                f.close()
    
    if os.path.exists(brickdir+".mcplock"):
        locked()
        exit()
        
    # ab hier dann arbeiten...
    if "del" in form:
        remove(form["del"].value)
        indexpage()
    elif "lock" in form:
        change_lock(form["lock"].value)
        indexpage()
    elif "move" in form:
        change_move(form["move"].value)
        indexpage()
    elif "datei" in form:
        upload(form["datei"])
    else:
        indexpage()
        