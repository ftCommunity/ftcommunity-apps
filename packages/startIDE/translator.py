#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# provide localisation for index.py
#

import locale

# get system default locale
defaultlocale=locale.getdefaultlocale()[0]

# set default to English
LOCAL = "en"

# list of translations available, add new locales to this list
LANGLIST = ["en","de","fr"]

# determination of system preset, add new translations here, too
if defaultlocale != None:
    if "de_" in defaultlocale: LOCAL = "de"
    elif "fr_" in defaultlocale: LOCAL = "fr"
# fallback to "en" in case of unidentified locale
else:
    try:
        with open(".locale","r") as f:
            r=f.readline()
            f.close
        if r in LANGLIST:
            LOCAL=r
            print("logal:",LOCAL)
        else: LOCAL="en"
    except:
        pass
LOCAL="de"
#
#
#
    
def getActiveLocale():
    # return the active localisation
    return LOCAL
    
def getLocalesList():
    # return list of translations available
    return LANGLIST

def translate(string, locale = LOCAL):
    #
    # translate the given string to the system default localisation or to a given localisation
    #
    #####################################
    # !!! Add new translations here !!! #
    #####################################
    
    if string == "This is a test":
        if locale == "de": return "Dies ist ein Test"
        if locale == "fr": return "C'est un test"    
        # if locale == "another language": return "Translated text for this language"
    elif string == "Control your model with a finger touch":
        if locale == "de": return "Steuere Modelle mit einem Fingertipp"
        if locale == "fr": return "Contr&ocirc;lez vos mod&egrave;les avec un clic du doigt"
    elif string == "<b>Download</b> a":
        if locale == "de": return "<b>Lade</b> ein"
        if locale == "fr": return "<b>T&eacute;l&eacute;charger</b> un"
    elif string == "project":
        if locale == "de": return "Projekt"
        if locale == "fr": return "projet"
    elif string == "or a":
        if locale == "de": return "oder ein"
        if locale == "fr": return "ou un"
    elif string == "module":
        if locale == "de": return "Modul"
        if locale == "fr": return "module"
    elif string == "from your TXT.":
        if locale == "de": return "vom TXT herunter."
        if locale == "fr": return "<b>ici</b>."    
    elif string == "<b>Upload</b> a":
        if locale == "de": return "<b>Sende</b> ein"
        if locale == "fr": return "<b>T&eacute;l&eacute;charger</b> un"
    elif string == "to your TXT.":
        if locale == "de": return "von hier zum TXT."
        if locale == "fr": return "<b>sur le TXT</b>."
    elif string == "Download a project from your TXT":
        if locale == "de": return "Lade ein Projekt vom TXT herunter"
        if locale == "fr": return "T&eacute;l&eacute;charger un projet depuis le TXT"
    elif string == "Download a module from your TXT":
        if locale == "de": return "Lade ein Modul vom TXT herunter"
        if locale == "fr": return "T&eacute;l&eacute;charger un module depuis le TXT"
    elif string == "Upload a project  to your TXT":
        if locale == "de": return "Sende ein Projekt zum TXT"
        if locale == "fr": return "T&eacute;l&eacute;charger un projet sur le TXT"
    elif string == "Upload a module to your TXT":
        if locale == "de": return "Sende ein Modul zum TXT"
        if locale == "fr": return "T&eacute;l&eacute;charger un module sur le TXT"
    elif string == "Back":
        if locale == "de": return "Zur&uuml;ck"
        if locale == "fr": return "Retour"
    elif string == "Show a project code listing":
        if locale == "de": return "Zeige einen Projekt-Programmcode"
        if locale == "fr": return "Afficher le code du programme"
    elif string == "Show a module code listing":
        if locale == "de": return "Zeige einen Modul-Programmcode"
        if locale == "fr": return "Afficher le code du module"
    elif string == "Please select project:":
        if locale == "de": return "Bitte Projekt ausw&auml;hlen:"
        if locale == "fr": return "Veuillez s&eacute;lectionner le projet:"
    elif string == "Please select module:":
        if locale == "de": return "Bitte Modul ausw&auml;hlen:"
        if locale == "fr": return "Veuillez s&eacute;lectionner le module:"
    elif string == "<b>Show</b> a":
        if locale == "de": return "<b>Zeige</b> einen"
        if locale == "fr": return "<b>Afficher</b> le code d'un"
    elif string == "code listing.":
        if locale == "de": return "Programmcode"
        if locale == "fr": return ""
    elif string == "Project file:":
        if locale == "de": return "Projektdatei:"
        if locale == "fr": return "Fichier de projet:"
    elif string == "Module file:":
        if locale == "de": return "Moduldatei:"
        if locale == "fr": return "Fichier de module:"
    elif string == "Upload!":
        if locale == "de": return "Hochladen!"
        if locale == "fr": return "T&eacute;l&eacute;charger!"
    elif string == "Download!":
        if locale == "de": return "Herunterladen!"
        if locale == "fr": return "T&eacute;l&eacute;charger!"
    elif string == "":
        if locale == "de": return ""
        if locale == "fr": return ""
    # if string == "another string":  
    #     if locale == "de": return "Deutsche Übersetzung"
    #     if locale == "fr": return "Traduction francaise"
    #     if locale == "another language": return "Translated text for this language"
        
    
    # string not found or language not found:
    return string
    
