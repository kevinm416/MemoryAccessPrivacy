import subprocess
import sys
from datetime import datetime
import re
import traceback

class MessageType:
    CHAT = 0
    INFO = 1
    META = 2

users = {}

def join(name):
    print 'JOIN', name
    if name not in users:
        users[name] = True

def quit(name):
    print 'QUIT', name
    if name in users:
        del users[name]

def talk(name, msg):
    print 'TALK', name, msg.rstrip()
    if name not in users: 
        join(name)
    # users[name].send(msg)

def parseDate(line):
    (start, remaining) = line.lstrip().split(' ', 1)
    date = datetime.strptime(start, '%m/%d/%y_%H:%M:%S')
    return (date, remaining)
    
def parseMessageType(line):
    line = line.lstrip()

    msgType = None
    userName = None
    message = None

    indicator = line[0]
    if line.startswith('<'):
        msgType = MessageType.CHAT
        (userName, message) = line[1:].split('>', 1)
    elif line.startswith('*'):
        msgType = MessageType.META
        (userName, message) = line[1:].lstrip().split(' ', 1)
    elif line.startswith('-!-'):
        msgType = MessageType.INFO
        (userName, message) = line[len('-!-'):].lstrip().split(' ', 1)
    else:
        raise Exception("what is this message type'%s'?" % line)
    return (msgType, userName, message)

def sendMessage(msgType, userName, message):
    if msgType == MessageType.CHAT:
        talk(userName, message)
    elif msgType == MessageType.INFO:
        if 'joined' in message:
            join(userName)
        elif 'quit' in message:
            quit(userName)

if __name__ == '__main__':
    convo = open('/home/kevin/repos/MemoryAccessPrivacy/irc/android.log')
    for line in convo:
        try:
            (date, remaining) = parseDate(line)
            (messageType, userName, message) = parseMessageType(remaining)
            sendMessage(messageType, userName, message)
        except Exception as e:
            traceback.print_exc()
            continue
    #subprocess.call(['ls', '/home/kevin'])