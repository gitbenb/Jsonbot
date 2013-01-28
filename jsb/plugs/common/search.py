# jsb/plugs/common/search.py
#
#

""" access stats data from the spider plugin. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.persist import PersistCollection, Persist
from jsb.lib.datadir import getdatadir
from jsb.utils.name import stripname
from jsb.utils.exception import handle_exception
from jsb.utils.statdict import StatDict
from jsb.utils.urldata import UrlData

## basic imports

import os

## searchobj function

def makestats(objs, target, skip=[]):
    stats = StatDict()
    if not objs: return stats
    ignore = []
    res = []
    count = {}
    for t in target:
        for u in objs:
            if u in ignore: continue
            if u and u.data and u.data.txt:
                cont = False
                for s in skip:
                    if s in u.data.url: cont = True ; break
                if cont: continue
                if t in u.data.txt:
                    res.append(u)
                else:
                    ignore.append(u)
                    try: res.remove(u)
                    except ValueError: pass 
    for item in res:
        c = 0
        if not item in ignore:
            for t in target: c += item.data.txt.count(t)
            stats.upitem(item.data.url, c)
    return stats

def stats_response(stats, target=[], skip=[]):
    r = []
    first = []
    todo = stats.top(start=3)
    if not todo: todo = stats.top()
    for res in todo:
        cont = False
        for s in skip:
            if s in str(res): cont = True
        if cont: continue
        url = res[0]
        count = res[1]
        if not url.endswith(".html"): continue
        if "genindex" in str(url): continue
        splitted = url.split("/")
        if target and target[-1] in splitted[-1]: first.append("%s (%s)" % (url, count))
        else: r.append("%s (%s)" % (url, count))
    first.extend(r)
    return first

## search command

def handle_search(bot, event):
    if not event.options: event.makeoptions()
    all = event.options.all
    res = []
    target = event.args
    if not target: event.missing("<search words seperated by space>") ; return
    coll = PersistCollection(getdatadir() + os.sep + 'spider' + os.sep + "data")
    files = coll.filenames(target)
    if files:
        for f in files:
            try: res.append(Persist(f).data.url)
            except AttributeError, ex: continue
    objs = coll.search('txt', event.rest)
    if not objs: objs = coll.objects().values()
    stats = makestats(objs, target, res)
    urls = stats_response(stats, target)
    res.extend(urls)
    if res:
        if len(res) < 4 or all: event.reply("found %s urls: " % len(res), res, dot=" -or- ")
        else: event.reply("found %s urls, use --all for more: " % len(res), res[:3], dot=" -or- ")
    else: event.reply("no urls found")

cmnds.add("search", handle_search, ["OPER", "USER", "GUEST"])
examples.add("search", "search scanned sites by the spider", "search license")
