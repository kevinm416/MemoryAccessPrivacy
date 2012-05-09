

import urllib2
import re

user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.19'\
    ' (KHTML, like Gecko) Chrome/18.0.1025.142 Safari/535.19'
headers = { 'User-Agent' : user_agent }


base = 'http://en.wikipedia.org'

seed = '/wiki/Main_Page'

sites_seen = set([seed])

sites_to_visit = [seed]

SITE_PATN = r'href="(?P<site>/wiki/[^:"]*)"'

while len(sites_seen) + len(sites_to_visit) < 1000 and len(sites_to_visit) != 0:
    site = sites_to_visit.pop()
    url = base + site
    html = urllib2.urlopen(urllib2.Request(url, None, headers)).read()
    urls = re.findall(SITE_PATN, html)
#    print html
    for u in urls:
#        print u
        if u not in sites_seen:
            sites_seen.add(u)
            sites_to_visit.append(u)
    

print '--S'
for site in sites_seen:
    print 1, base + site
for site in sites_to_visit:
    print 1, base + site
