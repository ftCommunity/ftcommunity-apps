#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
import time
import cgi
import os

__author__     = "Leon Schnieber"
__copyright__  = "Copyright 2019"
__maintainer__ = "Leon Schnieber"
__email__      = "olaginos-buero@outlook.de"
__status__     = "Developement"

def genMain():
    print("<!DOCTYPE html>")
    print("<head>")
    print("<title>RoProPreter</title>")
    print("<link rel=\"stylesheet\" href=\"/txt.css\" />")
    print("<link rel=\"icon\" href=\"/favicon.ico\" type=\"image/x-icon\" />")
    print("</head>")
    print("<body><center>")
    print("<h1><div class=\"outline\"><font color=\"red\">fischer</font><font color=\"#046ab4\">technik</font>&nbsp;<font color=\"#fcce04\">TXT</font></div></h1>")
    print("<p/><h1>")
    print("RoProPreter")
    print("</h1><p/>")
    print("<img src=\"icon.png\">")
    print("<br /><hr /><br />")
    print("<b><u>Programmspeicher</u></b><br />")
    files = os.listdir("files/")
    print("<br /><table>")
    print("<tr>")
    print("<th>Dateiname</th><th>l&ouml;schen</th>")
    print("</tr>")
    for fileD in files:
        if ".rpp" in fileD:
            print("<tr>")
            print("<td>" + fileD + "</td>")
            print("<td><a href=\"web.py?delete=" + fileD + "\">l&ouml;schen</a></td>")
            print("</tr>")
    print("</table><br />")
    # add list of programs
    print("<hr />")
    print("<b><u>Programm hochladen</u></b><br />")
    print("<form action=\"web.py\" method=\"post\" enctype=\"multipart/form-data\"><br />")
    print("<input name=\"fileUpload\" type=\"file\" size=\"150\" />")
    print("<button type=\"submit\" >Hochladen.</button>")
    print("</form>")
    print("<br /><hr /><br />")
    print("<p><a href=\"/\">zur&uuml;ck zur Startseite</a></p>")
    print("</center></body></html>")

def saveDownload(filehandler):
    path = filehandler.filename
    try:
        with open("files/" + path, "w", encoding="utf-8") as f:
            f.write(filehandler.file.read().decode())
            f.close()
            os.chmod("files/" + path, 0o666)
    except BaseException:
        pass
    genMain()

def delete(filename):
    os.remove("files/" + filename)
    genMain()

if __name__ == "__main__":
    data = cgi.FieldStorage()
    if "fileUpload" in data:
        saveDownload(data["fileUpload"])
    elif "delete" in data:
        delete(data["delete"].value.replace("..", ""))
    else:
        genMain()
