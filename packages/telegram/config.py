#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi, configparser
arguments = cgi.FieldStorage()
local_config = 'config'
global_config = '/media/sdcard/data/config.conf'
key_argument = ''
language = ''
default_language = 'EN'
language_list = ['EN','DE']
try:
	key_argument = arguments['key'].value
except: pass
if key_argument != '':
	config = configparser.ConfigParser()
	cfgfile = open("config",'w')
	config.add_section('config')
	config.set('config','key',key_argument)
	config.write(cfgfile)
	cfgfile.close()
key = ''
try:
	config = configparser.SafeConfigParser()
	config.read('config')
	key = config.get('config','key')
except: pass

try:
	config = configparser.SafeConfigParser()
	config.read(global_config)
	language = config.get('general','language')
except: pass
if language == '' or language not in language_list:
	language = default_language
print('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">')
print('<html xmlns="http://www.w3.org/1999/xhtml">')
print('<head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />')
print('<title>fischertechnik TXT community firmware</title>')
print('<link rel="stylesheet" href="/txt.css" />')
print('<link rel="icon" href="/favicon.ico" type="image/x-icon" />')
print('</head><body>')
print('<h1><div class="outline"><font color="red">fischer</font><font color="#046ab4">technik</font>&nbsp;<font color="#fcce04">TXT</font></div></h1>')
print('<div align="center">')
print('<h2>')
if language == 'EN':
	print('Telegram Config')
elif language == 'DE':
	print('Telegram Konfiguration')
print('</h2>')
print('<table align="center">')
print('<tr><td align="center"><img src="icon.png"/></td></tr>')
print('</table>')
print('<h2>')
if language == 'EN':
	print('Actions')
elif language == 'DE':
	print('Aktionen')
print('</h2>')
print('<table align="center">')
print('<tr><td>')
if language == 'EN':
	print('To install Telegram visit <a href=https://telegram.org/>Telegram</a> and download the version for your device.<br>Then write these messages to @BotFather:<br>1. /newbot<br>2. *Chose a name for your bot*<br>3. *Chose a username ending with "bot"*<br>Now copy the Token into the Formular and press "Send"')
elif language == 'DE':
	print('Um Telegram zu installieren, besuche <a href=https://telegram.org/>Telegram</a> und lade die Vesion für dein Gerät herunter.<br>Anschließend schreibe folgende Nachrichten an @BotFather:<br>1. /newbot<br>2. *Wähle einen Nicknamen für deinen Bot*<br>3. *Wähle einen Benutzerneman mit der Endung "bot"*<br>Kopiere den Token in das Formular und drücke "Senden"')
print('</td></tr>')
print('<tr><td>')
if language == 'EN':
	if key != '':
		print('<h3>Current API-Key: ' + key + '</h3>')
	else:
		print('<h3>No API-Key set</h3>')
elif language == 'DE':
	if key != '':
		print('<h3>Aktueller API-Key: ' + key + '</h3>')
	else:
		print('<h3>Kein API-Key gesetzt</h3>')
print('</td></tr>')
print('<tr><td>')
print('<form>')
print('<label for="key">API-Key: <input type="text" id="key" name="key"></label>')
if language == 'EN':
	print('<input type="submit" value="Send">')
elif language == 'DE':
	print('<input type="submit" value="Senden">')
print('</form>')
print('</td></tr>')
print('<td><tr><br></tr></td>')
print('<tr><td><a href=/>Home</a></td></tr>')
print('</table>')
print('</body>')
print('</html>')
