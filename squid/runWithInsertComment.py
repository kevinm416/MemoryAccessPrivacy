#! /usr/bin/python

import sys
import os
import subprocess
from Queue import Queue, Empty
from threading import Thread

comment_patn = '# %d %s'

cmd = r'''sudo %s --tool=cachegrind --trace-children=yes /usr/sbin/squid -N''' % (os.path.expanduser('~/CGTrace/vg-in-place'))

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

try:
    print comment_patn % (0, 'Start')
    p = subprocess.Popen(cmd.split(' '),
                         bufsize=1,
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.STDOUT)

    q = Queue()
    t = Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True
    t.start()

    comment_num = 1
    while True:
        comment = raw_input()
        data = []
        try:
            while True:
                line = q.get_nowait()
                print line.strip()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass
        print comment_patn % (comment_num, comment)
        comment_num += 1
except (KeyboardInterrupt, SystemExit):
    p.kill()

