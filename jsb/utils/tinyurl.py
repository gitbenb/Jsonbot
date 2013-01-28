# jsb/utils/tinyurl.py
#
#

""" tinyurl.com feeder """

__author__ = "Wijnand 'tehmaze' Modderman - http://tehmaze.com"
__license__ = 'BSD'

## jsb imports

from jsb.utils.url import striphtml, useragent
from jsb.utils.exception import handle_exception
from jsb.lib.cache import get, set

posturl = 'http://tinyurl.com/create.php'

## simpljejson

from jsb.imports import getjson
json = getjson()

## basic imports

import urllib
import urllib2
import urlparse
import re
import logging

## defines

re_url_match  = re.compile(u'((?:http|https)://\S+)')
urlcache = {}

## functions

def valid_url(url):
    """ check if url is valid """
    if not re_url_match.search(url): return False
    parts = urlparse.urlparse(url)
    cleanurl = '%s://%s' % (parts[0], parts[1])
    if parts[2]: cleanurl = '%s%s' % (cleanurl, parts[2])
    if parts[3]: cleanurl = '%s;%s' % (cleanurl, parts[3])
    if parts[4]: cleanurl = '%s?%s' % (cleanurl, parts[4])
    return cleanurl

## callbacks

def parseurl(txt):
    test_url = re_url_match.search(txt)
    if test_url:
        url = test_url.group(1)
        if url: return url

def get_tinyurl(url):
    """ grab a tinyurl. """
    res = get(url, namespace='tinyurl') ; logging.debug('tinyurl - cache - %s' % unicode(res))
    if res and res[0] == '[': return json.loads(res)
    postarray = [
        ('submit', 'submit'),
        ('url', url),
        ]
    postdata = urllib.urlencode(postarray)
    req = urllib2.Request(url=posturl, data=postdata)
    req.add_header('User-agent', useragent())
    try: res = urllib2.urlopen(req).readlines()
    except urllib2.URLError, e: logging.warn('tinyurl - %s - URLError: %s' % (url, str(e))) ; return
    except urllib2.HTTPError, e: logging.warn('tinyurl - %s - HTTP error: %s' % (url, str(e))) ; return
    except Exception, ex:
        if "DownloadError" in str(ex): logging.warn('tinyurl - %s - DownloadError: %s' % (url, str(e)))
        else: handle_exception()
        return
    urls = []
    for line in res:
        if line.startswith('<blockquote><b>'): urls.append(striphtml(line.strip()).split('[Open')[0])
    if len(urls) == 3: urls.pop(0)
    set(url, json.dumps(urls), namespace='tinyurl')
    return urls
