#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import os, socket, subprocess, time
def run():
    print('Running ft-robo-snap')
    os.system('cd /media/sdcard/apps/599047da-5f01-4a15-a94f-0fc14cc4a88b/ft-robo-snap && chmod +x ../python27/python2.7 && LD_LIBRARY_PATH=../python27/lib ../python27/python2.7 robo-snap.py localhost')

def checkrunning():
    TCP_IP = '0.0.0.0'
    TCP_PORT = 65004
    BUFFER_SIZE = 20
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(1)
    conn, addr = s.accept()
    while True:
        data = conn.recv(BUFFER_SIZE)
        if not data: break
        print('received data: ' , data)
        conn.send(data)
    conn.close()
#os.chdir('/media/sdcard/apps/599047da-5f01-4a15-a94f-0fc14cc4a88b/ft-robo-snap')
os.system('chmod +x /media/sdcard/apps/599047da-5f01-4a15-a94f-0fc14cc4a88b/run.sh')
subprocess.call('/media/sdcard/apps/599047da-5f01-4a15-a94f-0fc14cc4a88b/run.sh')
