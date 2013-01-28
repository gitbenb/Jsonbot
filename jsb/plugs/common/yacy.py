# /jsb/plugs/common/yacy.py
# -*- coding: utf-8 -*-
#
#
#

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.lib.commands import cmnds
from jsb.utils.url import geturl2
from jsb.imports import getjson

json = getjson()

# basic imports

import urllib
import random
import logging

## defines

queryurl = "http://%s/yacysearch.json?query=%s&maximumRecords=10"

prio1 = ["yacy-suche.de:8090",]

hosts = ["sokrates.homeunix.net:9090",
"suche.cyberneticworld.de:80",
"paraploi.de:8080",
"4o4.dyndns.org:8080",
"yacy.pyronet.tv:80",
"yacysearch.msi.eu:8090",
"yacy.linux-lan.net:8090",
"pixelhero.co.uk:8090",
"yacy.caloulinux.net:80",
"146.0.96.7:8090",
"d.ozg.ca:8090",
"yacy.dyndns.org:8000",
"yacy-suche.de:8090",
"yacy.de.vc:80",
"wayround.org:80"]


errorhosts = []

## getresults function

def getresults(url):
    logging.warn(url)
    result = geturl2(url)
    return result

## yacy command


def handle_yacy(bot, event):
    if not event.rest: event.missing("<searchitem>") ; return
    global hosts
    random.shuffle(hosts)
    got = ""
    r = None
    logging.warn("error hosts is %s" % str(errorhosts))
    if len(hosts) == len(errorhosts): event.reply("no alive server found") ; return
    for h in prio1 + hosts:
        if h in errorhosts: continue
        try:
            r = json.loads(getresults(queryurl % (h, urllib.quote_plus(event.rest))))
            if r: got = h ; break
        except Exception, ex: errorhosts.append(h) ; handle_exception() ; continue
    result = []
    for channel in r['channels']:
         for item in channel['items']: result.append("%s - %s (%s)" % (item['title'], item['link'], item['size']))
    if result: event.reply("results from %s: " % got, result, dot=" || ")
    else: event.reply("no result")

cmnds.add("yacy", handle_yacy, ["OPER", "USER"])
