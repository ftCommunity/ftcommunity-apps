#! /usr/bin/env python3
import telepot
import sys
import pprint
import time
import ftrobopy
import os
import configparser
import socket
global_config = '/media/sdcard/data/config.conf'
language = ''
default_language = 'EN'
language_list = ['EN', 'DE']
try:
    config = configparser.SafeConfigParser()
    config.read(global_config)
    language = config.get('general', 'language')
except:
    pass
if language == '' or language not in language_list:
    language = default_language
if language == 'EN':
    str_noapi = 'API KEY MISSING'
    str_printapi = 'Your API-Key: '
    str_message_already_killed = 'Bot is shutting down!'
elif language == 'DE':
    str_noapi = 'API KEY MISSING'
    str_printapi = 'Dein API-Key: '
    str_message_already_killed = 'Bot wird gestoppt!'
configfile_path = '/media/sdcard/apps/6026c098-cb9b-45da-9c8c-9d05eb44a4fd/config'
if os.path.exists(configfile_path) != True:
    print(str_noapi)
    os.system('rm /tmp/telegram.pid')
    exit(2)
else:
    try:
        configfile = configparser.RawConfigParser()
        configfile.read(configfile_path)
        api_key = configfile.get('config', 'key')
        print(str_printapi + api_key)
    except:
        print(str_noapi)
        os.system('rm /tmp/telegram.pid')
        exit(2)
bot = telepot.Bot(api_key)
bot.getMe()
txt = ftrobopy.ftrobopy('127.0.0.1', 65000)
global function
function = ''
global tempdata
tempdata = ''
global killbot
killbot = ''


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def handle(msg):
    pprint.pprint(msg)
    command = msg['text']
    chat_id = msg['chat']['id']
    print(command, chat_id)

    def app_select_keyboard():
        base = "/opt/ftc"

        def scan_app_dirs():
            app_base = os.path.join(base, "apps")
            app_groups = os.listdir(app_base)
            app_dirs = []
            for i in app_groups:
                try:
                    app_group_dirs = os.listdir(os.path.join(app_base, i))
                    for a in app_group_dirs:
                        app_dir = os.path.join(app_base, i, a)
                        manifestfile = os.path.join(app_dir, "manifest")
                        if os.path.isfile(manifestfile):
                            manifest = configparser.RawConfigParser()
                            manifest.read(manifestfile)
                            appname = manifest.get('app', 'name')
                            app_dirs.append((appname, os.path.join(app_base, i, a)))
                except:
                    pass
            app_dirs.sort(key=lambda tup: tup[0])
            return ([x[1] for x in app_dirs])
        appdir_list = scan_app_dirs()
        print(appdir_list)
        print(len(appdir_list))
        app_dict = {}
        for app_dir in appdir_list:
            manifestfile = os.path.join(app_dir, "manifest")
            manifest = configparser.RawConfigParser()
            manifest.read(manifestfile)
            appname = manifest.get('app', 'name')
            executable = os.path.join(app_dir, manifest.get('app', 'exec'))
            app_dict[appname] = executable
        app_pseudo_dict = sorted(app_dict.items())
        print(app_pseudo_dict)
        return app_pseudo_dict, app_dict
    global function
    global killbot
    global tempdata
    if killbot != '':
        bot.sendMessage(chat_id, str_message_already_killed)
        return
    # FUNCTION WITH ///
    if command == '/sound':
        bot.sendMessage(chat_id, 'Now enter the sound ID')
        function = 'sound'
        print('Calling sound feature')
    elif command == '/currentfx':
        if function != '':
            bot.sendMessage(chat_id, 'Current function is: ' + function)
        else:
            bot.sendMessage(chat_id, 'Currently no function is active!')
        print('Calling Current fx feature')
    elif command == '/botstop':
        bot.sendMessage(chat_id, 'Stopping bot soon!')
        bot.sendMessage(chat_id, 'Good Bye!')
        killbot = chat_id
        print('Stopping BOT')
    elif command == '/help':
        print('Calling help feature')
        function = ''
        bot.sendMessage(chat_id, '-----This is the TXT-Bot help-----')
        bot.sendMessage(chat_id, '/help - See this help')
        bot.sendMessage(chat_id, '/sound - Use this to play Sounds on the TXT')
        bot.sendMessage(chat_id, '/screenshot - Use this to take a Screenshot of the TXTs Scrren')
        bot.sendMessage(chat_id, '/botstop - Use this to stop the bot')
        bot.sendMessage(chat_id, '-------End of TXT-Bot help--------')
        print('Help print')
    elif command == '/screenshot':
        print('Calling Screenshot feature')
        function = ''
        bot.sendMessage(chat_id, 'Taking Screenshot! Please Wait')
        bot.sendChatAction(chat_id, 'upload_photo')
        os.system('rm /tmp/screenshot.png >/dev/null 2>&1')
        os.system('python3 /var/www/screenshot.py >/dev/null 2>&1')
        if os.path.exists('/tmp/screenshot.png'):
            bot.sendPhoto(chat_id, open('/tmp/screenshot.png', 'rb'))
            print('Screenshot sent')
        else:
            bot.sendMessage(chat_id, 'Failure taking screenshot!')
            print('Error taking screenshot')
    elif command == '/startapp':
        print('Calling start APP feature')
        function = 'startapp'
        app_list, app_dict = app_select_keyboard()
        tempdata = app_dict
        keyboard = []
        count = 0
        while count <= (len(app_list) - 1):
            local_keyboard = []
            app = app_list[count]
            appname = app[0]
            local_keyboard.append(appname)
            keyboard.append(local_keyboard)
            count = count + 1
        show_keyboard = {'keyboard': keyboard}
        bot.sendMessage(chat_id, 'Select APP to start', reply_markup=show_keyboard)
    elif command == '/stopapp':
        print('Calling stop APP feature')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("localhost", 9000))
            sock.sendall(bytes("stop-app" + "\n", "UTF-8"))
        except socket.error as msg:
            bot.sendMessage(chat_id, 'Launcher is not responding! Try again after rebooting the TXT!')
        finally:
            sock.close()
    # FUNCTION WITHOUT ///
    # NONE
    # FUNCTION WITH FREE VALUE
    elif function == 'sound':
        if is_number(command) == True:
            bot.sendMessage(chat_id, 'Playing sound ' + command)
            txt.play_sound(int(command), 60)
            print('Playing Sound Number ' + command)
        else:
            bot.sendMessage(
                chat_id, 'This is not a value! Leaving Sound Menu!')
        function = ''
    elif function == 'startapp':
        print(tempdata)
        hide_keyboard = {'hide_keyboard': True}
        if command in tempdata:
            print('exists')
            app_executable = tempdata[command]
            app_executable = app_executable.replace('/opt/ftc/apps/', '')
            print('Starting: ' + app_executable)
            bot.sendMessage(chat_id, 'Starting ' + command, reply_markup=hide_keyboard)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(("localhost", 9000))
                sock.sendall(bytes("stop-app" + "\n", "UTF-8"))
                time.sleep(1)
                sock.sendall(bytes("launch " + app_executable + "\n", "UTF-8"))
            except socket.error as msg:
                bot.sendMessage(chat_id, 'Launcher is not responding! Try again after rebooting the TXT!')
            finally:
                sock.close()
        else:
            print('ERROR')
        tempdata = ''
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
        os.system('rm /tmp/telegram.pid')
        bot.sendMessage(killbot, 'Killed sucessfully!')
        print('KILLED')
        exit(1)
