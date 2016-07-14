#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re
running = True
if running == True:
	ip_wlan0_raw = os.popen("ip addr show wlan0").read()
	ip_wlan0_raw = re.findall('inet (\d+.\d+.\d+.\d+\/\d+)', ip_wlan0_raw)
	ip_wlan0_raw = ip_wlan0_raw[0]
	ip_wlan0_raw = ip_wlan0_raw.split('/')
	ip_wlan0 = ip_wlan0_raw[0]
	ip_usb0_raw = os.popen("ip addr show usb0").read()
	ip_usb0_raw = re.findall('inet (\d+.\d+.\d+.\d+\/\d+)', ip_usb0_raw)
	ip_usb0_raw = ip_usb0_raw[0]
	ip_usb0_raw = ip_usb0_raw.split('/')
	ip_usb0 = ip_usb0_raw[0]
	print('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">')
	print('<html xmlns="http://www.w3.org/1999/xhtml">')
	print('<head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />')
	print('<title>fischertechnik TXT community firmware</title>')
	print('<link rel="stylesheet" href="/txt.css" />')
	print('<link rel="icon" href="/favicon.ico" type="image/x-icon" />')
	print('</head><body>')
	print('<h1><div class="outline"><font color="red">fischer</font><font color="#046ab4">technik</font>&nbsp;<font color="#fcce04">TXT</font></div></h1>')
	print('<div align="center">')
	print('<h2>ft-robo-snap</h2>')
	print('<table align="center">')
	print('<tr><td align="center"><img src="icon.png"/></td></tr>')
	print('</table>')
	print('<h2>Actions</h2>')
	print('<table align="center">')
	print('<h3>Select which connection type you are using</h3>')
	print('<tr><td><a href="http://' + ip_wlan0 + ':65003/ide/snap.html" target="ft-robo-snap"><img src="wlan.png" alt="WLAN IMAGE" /></a></td></tr>')
	print('<td><tr><a href="http://' + ip_usb0 + ':65003/ide/snap.html" target="ft-robo-snap"><img src="usb.png" alt="USB IMAGE" /></a></tr></td>')
	print('<td><tr><br></tr></td>')
	print('<tr><td><a href=/>Home</a></td></tr>')
	print('</table>')
	print('</body>')
	print('</html>')
