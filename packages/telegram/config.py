#! /usr/bin/env python3
import cgi, configparser
arguments = cgi.FieldStorage()
#print(arguments.value)
key = ''
try:
	key = arguments['key'].value
except: pass
if key != '':
	#print('Hi')
	#print(key)
	Config = configparser.ConfigParser()
	cfgfile = open("config",'w')
	Config.add_section('config')
	Config.set('config','key',key)
	Config.write(cfgfile)
	cfgfile.close()
print('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">')
print('<html xmlns="http://www.w3.org/1999/xhtml">')
print('<head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />')
print('<title>fischertechnik TXT community firmware</title>')
print('<link rel="stylesheet" href="/txt.css" />')
print('<link rel="icon" href="/favicon.ico" type="image/x-icon" />')
print('</head><body>')
print('<h1><div class="outline"><font color="red">fischer</font><font color="#046ab4">technik</font>&nbsp;<font color="#fcce04">TXT</font></div></h1>')
print('<div align="center">')
print('<h2>Telegram Config</h2>')
print('<table align="center">')
print('<tr><td align="center"><img src="icon.png"/></td></tr>')
print('</table>')
print('<h2>Actions</h2>')
print('<table align="center">')
print('<tr><td>To install Telegram visit <a href=https://telegram.org/>Telegram</a> and download the version for your device.<br>Then write this messages to @BotFather:<br>1. /newbot<br>2. *Chose a name for your bot*<br>3. *chose a username ending with "bot"*<br>Now copy the Token into the Formular and press "Send"<br>')
print('<tr><td>')
print('<form>')
print('<label for="key">API-Key: <input type="text" id="key" name="key"></label> <input type="submit" value="Send">')
print('</form>')
print('</td></tr>')
print('<td><tr><br></tr></td>')
print('<tr><td><a href=/>Home</a></td></tr>')
print('</table>')
print('</body>')
print('</html>')
