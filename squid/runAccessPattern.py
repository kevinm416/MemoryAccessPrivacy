#! /usr/bin/python

import sys
import urllib2
import random

import re

HOST = '192.168.1.13:3128'
TYPE = 'http'
user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.19'\
    ' (KHTML, like Gecko) Chrome/18.0.1025.142 Safari/535.19'
headers = { 'User-Agent' : user_agent }

SEQUENTIAL = '--S'
RANDOM = '--R'

def streamifyFile(file):
    l = file.readline()
    yield l.strip()
    data = []
    for line in file:
        if line == SEQUENTIAL or line == RANDOM:
            yield data
            data = []
            yield line.strip()
        else:
            data.append(line.strip())
    yield data

def getAccessTypeAndURLsFromFile(file):
    def timesURLPair(l):
        url_regex = '(\S+)\s*$'
        patn = '(\d+)\s+' + url_regex
        m = re.match(patn, l)
        if m:
            return (int(m.group(1)), m.group(2))
        else:
            m = re.match(url_regex, l)
            if not m:
                print 'Error: malformed line "%s"' % l
                exit(1)
            return (1, m.group(1))
    s = streamifyFile(file)
    for accessType in s:
        data = s.next()
        data = map(timesURLPair, data)
        yield(accessType, data)
    
def openURL(url):
    print 'Accessing: %s' % url
    req = urllib2.Request(url, None, headers)
    req.set_proxy(HOST, TYPE)
    handle = urllib2.urlopen(req)
    return handle

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'Expecting a file name with URLs as an argument'
        exit(1)
    f = open(sys.argv[1], 'r')
    
    for accessType, data in getAccessTypeAndURLsFromFile(f):
        if accessType == SEQUENTIAL:
            for times, url in data:
                for x in range(times):
                    handle = openURL(url)
#                    print handle.read()
        elif accessType == RANDOM:
            URLPool = []
            for times, url in data:
                URLPool += times * [url]
            random.shuffle(URLPool)
            for url in URLPool:
                handle = openURL(url)
#                print handle.read()

    f.close()
