#! /usr/bin/env python3
import telepot
import sys
import pprint
import time
import ftrobopy
import os
import configparser
approot = (os.path.realpath(__file__).rpartition('/')
           [0] + os.path.realpath(__file__).rpartition('/')[1])
configfile_path = approot + 'config'
if os.path.exists(configfile_path) != True:
    print('Configure your Telegram API key descriped on the TXT Website!')
    exit(2)
else:
    configfile = configparser.RawConfigParser()
    configfile.read(configfile_path)
    api_key = configfile.get('config', 'key')
    print('Your API-Key: :' + api_key)
bot = telepot.Bot(api_key)
bot.getMe()
txt = ftrobopy.ftrobopy('127.0.0.1', 65000)
global function
function = ''
global killbot
killbot = ''


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def handle(msg):
    # pprint.pprint(msg)
    command = msg['text']
    chat_id = msg['chat']['id']
    print(command, chat_id)
    global function
    global killbot
    if killbot != '':
        bot.sendMessage(chat_id, 'Bot is shutting down!')
        return
    #print('from function before ' + function)
    # FUNCTION WITH ///
    if command == '/sound':
        bot.sendMessage(chat_id, 'Now enter the sound ID')
        function = 'sound'
    elif command == '/currentfx':
        if function != '':
            bot.sendMessage(chat_id, 'Current function is: ' + function)
        else:
            bot.sendMessage(chat_id, 'Currently no function is active!')
    elif command == '/botstop':
        bot.sendMessage(chat_id, 'Stopping bot soon!')
        bot.sendMessage(chat_id, 'Good Bye!')
        killbot = chat_id
    elif command == '/help':
        bot.sendMessage(chat_id, '-----This is the TXT-Bot help-----')
        bot.sendMessage(chat_id, '/help - See this help')
        bot.sendMessage(chat_id, '/sound - Use this to play Sounds on the TXT')
        bot.sendMessage(
            chat_id, '/screenshot - Use this to take a Screenshot of the TXTs Scrren')
        bot.sendMessage(chat_id, '/botstop - Use this to stop the bot')
        bot.sendMessage(chat_id, '-------End of TXT-Bot help--------')
    elif command == '/screenshot':
        bot.sendMessage(chat_id, 'Taking Screenshot! Please Wait')
        bot.sendChatAction(chat_id, 'upload_photo')
        os.system('rm /tmp/screenshot.png')
        os.system('python3 /var/www/screenshot.py')
        if os.path.exists('/tmp/screenshot.png'):
            bot.sendPhoto(chat_id, open('/tmp/screenshot.png', 'rb'))
        else:
            bot.sendMessage(chat_id, 'Failure taking screenshot!')
        # FUNCTION WITHOUT ///
    # NONE
    # FUNCTION WITH FREE VALUE
    elif function == 'sound':
        if is_number(command) == True:
            bot.sendMessage(chat_id, 'Playing sound ' + command)
            txt.play_sound(int(command), 60)
            print('Playing Sond Number ' + command)
        else:
            bot.sendMessage(
                chat_id, 'This is not a value! Leaving Sound Menu!')
        function = ''
    else:
        bot.sendMessage(
            chat_id, 'Wrong Command! See /help for further information')
        print('Wrong Command')
    #print('from function after ' + function)
bot.message_loop(handle)
print('Listening ...')
while True:
    time.sleep(1)
    #print('from global ' + function)
    if killbot != '':
        time.sleep(5)
        bot.sendMessage(killbot, 'Killed sucessfully!')
        exit(1)
