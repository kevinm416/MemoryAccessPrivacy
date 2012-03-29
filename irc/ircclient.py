import sys
import socket
import string
import sets
from threading import Thread
from Queue import Queue, Empty

class IrcClient(Thread):
    def __init__(self, nick, host='localhost', port=6667):
        Thread.__init__(self)
        self.channels = sets.Set()
        self.nick = nick
        self.host = host
        self.port = port
        self.sock = socket.socket()
        self.msgQ = Queue()
        self.msgQ.put("NICK %s\r\n" % self.nick)
        self.msgQ.put("USER %s %s bla :%s\r\n" % 
            (self.nick, self.host, self.nick))
        
    def enter(self, channel):
        if not channel in self.channels:
            self.msgQ.put("JOIN %s\r\n" % channel)
            self.channels.add(channel)
        else:
            raise Exception("Trying to join a channel you are already in")

    def leave(self, channel):
        if channel in self.channels:
            self.msgQ.put("PART %s\r\n" % channel)
            self.channels.remove(channel)
        else:
            raise Exception("Trying to leave a channel you are not in")

    def quit(self):
        self.msgQ.put("QUIT")
    
    def send(self, channel, msg):
        if channel in self.channels:
            print 'put', msg, 'in queue'
            self.msgQ.put("PRIVMSG %s %s\r\n" % (channel, msg))
        else:
            raise Exception("Trying to send to a channel you are not connected to")

    def run(self):
        self.sock.connect((self.host, self.port))

        readbuffer=""
        while 1:
            readbuffer=readbuffer+self.sock.recv(1024)
            temp=string.split(readbuffer, "\n")
            readbuffer=temp.pop( )

            for line in temp:
                print line
                line=string.rstrip(line)
                line=string.split(line)

                if(line[0]=="PING"):
                    self.sock.sendall("PONG %s\r\n" % line[1])
            
            try:
                while True:
                    msg = self.msgQ.get_nowait()
                    print 'got msg:', msg
                    self.sock.sendall(msg)
                    if msg == "QUIT":
                        self.quit()
                        return
            except Empty:
                pass

def enqueue_stream(stream, queue):
    for line in iter(stream.readline, ''):
        queue.put(line)
    stream.close()
    queue.put(('done',))

if __name__ == '__main__':
    print sys.argv
    if not len(sys.argv) == 4:
        print 'usage: ircclient <host> <channel> <nickname>'
        sys.exit(1)
    
    host = sys.argv[1]
    channel = sys.argv[2]
    nickname = sys.argv[3]

    # start irc client thread
    c = IrcClient(nickname, host)
    c.start()
    c.enter(channel)

    # start enqueue thread
    q = Queue()
    t = Thread(target=enqueue_stream, args=(sys.stdin, q))
    t.daemon = True
    t.start()

    while True:
        try:
            line = q.get(True)
            print 'got line:', line
            if not type(line) is str:
                break
            else:
                c.send(channel, line)
        except Empty:
            continue

    c.leave(channel)
    c.quit()
    
    c.join()
    print 'done'





