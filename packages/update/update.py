#! /usr/bin/env python3
import sys
import os
import os.path
import time
import urllib.request
import ssl
import json
#from PyQt4.QtNetwork import *
#from TxtStyle import *

downloadzip = "update.zip"
sdcardbase = "/media/sdcard/"
olddir = "update_rollback"
required_file = "rootfs.img"

# check for sudo
if os.popen("sudo whoami").read().strip() != 'root':
    print('No Permission to update! Check for sudo rights!')
    exit()

curreentver = os.popen("cat /etc/fw-ver.txt").read().strip()

# Cleanup files
os.system("sudo rm " + sdcardbase + downloadzip)
# create Folders
os.system("sudo mkdir " + sdcardbase + olddir)
# check whether simple layout is used
required_file_exsits = os.path.exists(sdcardbase + required_file)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
raw_data = urllib.request.urlopen(
    'https://api.github.com/repos/ftCommunity/ftcommunity-TXT/releases', context=ctx).read().decode()
all_releases = json.loads(raw_data)
# filter out to latest release
latest_release = all_releases[0]
# Getting version number
release_version = latest_release['tag_name']
release_version = release_version.replace("v", "")
print("Internet version: v" + release_version)
print("Local version: v" + curreentver)

# check whether we use the current version
if release_version != curreentver:
    print("Update")
    # Getting download link
    assets = latest_release['assets']
    assets_count = -1
    content_type = ''
    while content_type != 'application/zip':
        assets_count = int(assets_count) + 1
        # if assets_count > (len(assets) + 1):
        #	print("No valid download link found! Contact the developer!")
        #	exit(0x01a)
        file_info = assets[assets_count]
        content_type = file_info['content_type']
        dl_link = file_info['browser_download_url']
    #print('assets_count: ' + str(assets_count))
    print('DL: ' + dl_link)
    if required_file_exsits != True:
        print("Abort! No simple Layout")
        exit("Abort! No simple Layout")
    # download zip
    os.system('(/bin/echo "msg Update! Do not plug off the power corde! Downloading!" & /bin/echo "quit") | sudo /usr/bin/nc localhost 9000')
    os.system("sudo wget -O " + sdcardbase + downloadzip +
              " --no-check-certificate " + dl_link)
    # save files for recovery
    os.system('(/bin/echo "msg Update! Do not plug off the power corde! Saving Recovery Files!" & /bin/echo "quit") | sudo /usr/bin/nc localhost 9000')
    os.system("sudo mv " + sdcardbase + "am335x-kno_txt.dtb" +
              " " + sdcardbase + olddir + "/am335x-kno_txt.dtb")
    os.system("sudo mv " + sdcardbase + "rootfs.img" +
              " " + sdcardbase + olddir + "/rootfs.img")
    os.system("sudo mv " + sdcardbase + "uImage" +
              " " + sdcardbase + olddir + "/uImage")
    # unzip
    os.system('(/bin/echo "msg Update! Do not plug off the power corde! Unzipping!" & /bin/echo "quit") | sudo /usr/bin/nc localhost 9000')
    os.system("sudo unzip -o " + sdcardbase +
              downloadzip + " -d " + sdcardbase)
    os.system('(/bin/echo "msg Update! Do not plug off the power corde! Storing Files!" & /bin/echo "quit") | sudo /usr/bin/nc localhost 9000')
    # finishing
    os.system('(/bin/echo "msg Update finished! TXT will reboot soon!" & /bin/echo "quit") | sudo /usr/bin/nc localhost 9000')
    time.sleep(1.5)
    os.system('(/bin/echo "msg Shutting down... When the blue light switches off boot the TXT again!" & /bin/echo "quit") | sudo /usr/bin/nc localhost 9000')
    os.system("sudo /sbin/poweroff")
else:
    print("Up To Date")
    exit()
