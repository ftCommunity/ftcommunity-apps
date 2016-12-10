#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import os
import json
arguments = cgi.FieldStorage()
LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_PATH = os.path.join(LOCAL_PATH, 'stations.json')
station_file = open(JSON_PATH)
stations = json.load(station_file)
if 'n' in arguments and 'u' in arguments:
    json_write = open(JSON_PATH, 'w')
    table = {
         ord('ä'): 'ae',
         ord('ö'): 'oe',
         ord('ü'): 'ue',
         ord('Ä'): 'Ae',
         ord('Ö'): 'Oe',
         ord('Ü'): 'Ue',
         ord('ß'): 'ss',
       }
    stations[arguments['n'].value.translate(table)] = arguments['u'].value
    json_write.write(json.dumps(stations, ensure_ascii=False))
    json_write.close()
if 'd' in arguments:
    if arguments['d'].value in stations:
        delete_station = arguments['d'].value
        stations = { k:v for k, v in stations.items() if v != stations[arguments['d'].value]}
        json_write = open(JSON_PATH, 'w')
        json_write.write(json.dumps(stations, ensure_ascii=False))
        json_write.close()
print('''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<title>fischertechnik TXT community firmware</title>
<link rel="stylesheet" href="/txt.css" />
<link rel="icon" href="/favicon.ico" type="image/x-icon" />
</head><body>
<h1><div class="outline"><font color="red">fischer</font><font color="#046ab4">technik</font>&nbsp;<font color="#fcce04">TXT</font></div></h1>
''')
print('''
<div align="center">
<h2>Radio</h2>
<table align="center"><tr><td align="center"><img src="icon.png"/></td></tr></table>
<h2>Configuration</h2>
<h3>To add a station enter the values in these fields!</h3>
<form>
Station Name:<input type="text" name="n"><br>
URL: <input type="url" name="u"><br>
<input type="submit" value="New Station">
</form>
<h3>To remove a station click on the remove button!</h3>
''')
print('''
<table align="center">
<tr>
<th>Station</th>
<th>URL</th>
<th>Remove</th>
</tr>''')
for station, url in stations.items():
    print('<tr>')
    print('<td>' + station + '</td>')
    print('<td><a href="' + url + '">' + url + '</a></td>')
    print('<td><a href="?d=' + station + '"><font color="red">Remove</font></a></td>')
    print('</tr>')
print('</table>')
