#!/bin/sh
cd /media/sdcard/apps/599047da-5f01-4a15-a94f-0fc14cc4a88b/ft-robo-snap
chmod +x ../python27/python2.7
LD_LIBRARY_PATH=../python27/lib ../python27/python2.7 robo-snap.py localhost
