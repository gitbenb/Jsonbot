# jsb/plugs/common/overflow.py
#
#

""" Grabs data for a StackOverflow user. You must enable this plugin first by running .. ;overflow-cfg enable 1 """

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.utils.lazydict import LazyDict
from jsb.utils.url import geturl2, striphtml, re_url_match
from jsb.utils.generic import splittxt
from jsb.utils.timeutils import today
from jsb.lib.persistconfig import PersistConfig
from jsb.lib.persiststate import PlugState
from jsb.lib.jsbimport import _import_byfile
from jsb.lib.datadir import getdatadir
from jsb.lib.callbacks import callbacks
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.fleet import getfleet
from jsb.lib.periodical import minutely, periodical
from jsb.lib.errors import URLNotEnabled
from jsb.imports import getjson

json = getjson()

## basic imports

import os
import logging
import uuid
import time
import StringIO
import gzip
import urllib

## defines

cfg = PersistConfig()
cfg.define("enable", 0)
cfg.define("sleep", 5)

state = PlugState()
state.define("ids", {})
state.define("seen", [])
state.define("names", {})
state.define("watch", [])

teller = 0
dostop = False

## plugin init

def init_threaded():
    try:
        if cfg.enable: sync() ; scan()
    except URLNotEnabled: logging.error("URL fetching is not enabled")

## plugin shutdown

def shutdown():
    periodical.kill()

## make sure plugin gets autoloaded on start

def dummycb(bot, event): pass

callbacks.add("START", dummycb)


## geturls function

def geturls(txt):
    result = []
    if "http://" in txt or "https://" in txt:
        for item in re_url_match.findall(txt):
            logging.debug("web - raw - found url - %s" % item)
            try: txt = txt.replace(item, '')
            except ValueError:  logging.error("web - invalid url - %s" % url)
            i = item
            if i.endswith('"'): i = i[:-1]
            if i.endswith('")'): i = i[:-2]
            result.append(i)
    return (result, striphtml(txt))

## OverFlowAPI

class OverFlowAPI(object):

    def __init__(self, api_key=None):
        self.api_key = api_key

    def api(self, mount, size=30, options={}):
        url = 'http://api.stackoverflow.com/1.0%s/%s?body=true&pagesize=%s' % (mount, urllib.urlencode(options), size)
        if self.api_key is not None:
            url += '&key=%s' % self.api_key
        content = StringIO.StringIO(geturl2(url, timeout=15))
        return gzip.GzipFile(fileobj=content).read()
  
    def timeline(self, target, size=30):
        json_data = self.api("/users/%s/timeline" % target, size)
        return json.loads(json_data)['user_timelines']

    def answers(self, target, size=30):
        json_data = self.api("/answers/%s/" % target, size)
        return json.loads(json_data)['answers']

    def search(self, title, size=30, tags=["google-app-engine",]):
        json_data = self.api("/search?intitle=%s&tagged=%s" % (title, ";".join(tags)), size)
        return json.loads(json_data)

of = OverFlowAPI()

## gettimeline function

def gettimeline(target, nr=30):
    answers = of.timeline(target, nr)
    logging.info("grabbed %s timeline items for %s" % (len(answers), target))
    return answers

def getanswers(target, nr=30):
    answers = of.answers(target, nr)
    logging.info("grabbed %s answer items for %s" % (len(answers), target))
    return answers

def search(target, nr=30):
    answers = of.search(target, nr)
    logging.info("grabbed %s answer items for %s" % (len(answers), target))
    return answers

def sync():
    target = ";".join(state.data.watch)
    if not target: logging.warn("no channels started yet") ; return
    res = gettimeline(target)
    if not res: logging.warn("no result from %s" % id) ; return
    todo = []
    for r in res:
        a = LazyDict(r)
        logging.debug("got %s" % a.tojson())
        if a.creation_date not in state.data.seen: state.data.seen.insert(0, a.creation_date) ; todo.append(a)
        #todo.append(a)
    state.data.seen = state.data.seen[:100]
    state.save()
    logging.info("returned %s items" % len(todo))
    return todo

## scan function

@minutely
def scan(skip=False):
    global teller, dostop
    if dostop: return
    teller += 1
    try: do = int(cfg.sleep)
    except ValueError: do = 5
    if do < 1: do = 5
    if teller % do != 0: return 
    logging.info("running")
    fleet = getfleet()
    todo = sync()
    if not todo: logging.info("nothing todo") ; return
    for b in todo:
        uid = str(b.user_id)
        if not uid in state.data.ids: logging.warn("we don't follow id %s" % uid) ; continue
        for channel in state.data.ids[uid]:
            if dostop: return
            botname, chan = channel
            bot = fleet.byname(botname)
            if bot:
                if b.post_id: url = ("http://stackoverflow.com/questions/%s" % b.post_id) or "no url found"
                bot.say(chan, "*%s* %s - *%s* - %s - %s - %s (%s)" % (state.data.names[uid].upper(), b.action, b.description, url, time.ctime(b.creation_date), b.detail or "no detail", b.post_type))
                if b.action == "answered":
                    aa = getanswers(b.post_id)
                    if aa:
                        a = aa[-1]
                        try: body = a['body']
                        except KeyError: continue
                        (urls, c) = geturls(body)
                        if c: bot.say(chan, u"> " + c)
                        else: bot.say(chan, "can't find answers")
                        if urls: bot.say(chan, "urls: %s" % " -=- ".join(urls))
            else: logging.warn("no %s bot in fleet" % botname)

## overflow-start command

def handle_overflowstart(bot, event):
    global state
    for bla in event.args:
        try: name, gid = bla.split(":")
        except: name = gid = bla
        state.data.names[gid] = name
        target = [bot.cfg.name, event.channel]
        if not state.data.ids.has_key(gid): state.data.ids[gid] = []
        if not gid in state.data.watch or not target in state.data.ids[gid]: state.data.ids[gid].append(target) ; state.data.watch.append(gid)
        else: event.reply("we are already monitoring %s in %s" % (gid, str(target)))
    state.save()
    sync()
    event.done()

cmnds.add("overflow-start", handle_overflowstart, ["OPER", ])
examples.add("overflow-start", "start monitoring a stackoverflow id into the channel", "overflow-start bthate:625680")

## overflow-stop command

def handle_overflowstop(bot, event):
    if not event.args: event.missing("<stackoveflow id") ; return
    global state
    id = event.args[0]
    try:
        del state.data.ids[id]
        del state.data.names[id]
        state.save()
        event.done()
    except (KeyError, ValueError): event.reply("we are not monitoring %s in %s" % (id, event.channel))
    
cmnds.add("overflow-stop", handle_overflowstop, ["OPER", ])
examples.add("overflow-stop", "stop monitoring a stackoverflow id", "overflow-stop 625680")

## overflow-list command

def handle_overflowlist(bot, event): event.reply("ids list: ", state.data.ids)

cmnds.add("overflow-list", handle_overflowlist, ['OPER', ])

## overflow-names command

def handle_overflownames(bot, event): event.reply("names list: ", state.data.names)

cmnds.add("overflow-names", handle_overflownames, ['OPER', ])

## overflow-disable command

def handle_overflowdisable(bot, event): global dostop ; dostop = True ; event.done()

cmnds.add("overflow-disable", handle_overflowdisable, ['OPER', ])

## overflow-enable command

def handle_overflowenable(bot, event): global dostop ; dostop = False ; event.done()

cmnds.add("overflow-enable", handle_overflowenable, ['OPER', ])

## overflow-answers command

def handle_overflowanswers(bot, event):
    result = []
    for aa in getanswers(event.rest):
        a = LazyDict(aa)
        result.append("%s - %s" % (a.owner['display_name'], striphtml(a.body)))
    event.reply("answers for %s: " % event.rest, result)
    
cmnds.add("overflow-answers", handle_overflowanswers, ["OPER", "USER"])

## overflow-search command

def handle_overflowsearch(bot, event):
    result = []
    res = search(event.rest, 10)
    nritems = 10
    for aa in res['questions'][:nritems]:
        a = LazyDict(aa)
        if not a.accepted_answer_id: continue
        url = "http://stackoverflow.com/questions/%s" % a.accepted_answer_id
        result.append("%s - %s - %s" % (a.title, ";".join(a.tags), url))
    if result: event.reply("results: ", result, dot=" -=- ")
    else: event.reply("no result found")

cmnds.add("overflow-search", handle_overflowsearch, ["OPER", "USER"])


"""

{"user_id": 818274, 
 "description": "What is the proper way to write to the Google App Engine blobstore as a file in Python 2.5", 
 "comment_id": 11614983, 
 "detail": "Yes, but it hardly explains the out of memory warning. A list of 4000 integers is something like 4000 times 40 bytes, i.e. 160 KB. That may seem a lot but is a drop in the 128 MB bucket...", 
"creation_date": 1328857684, 
"post_id": 9219465, 
"post_type": "answer", 
"action": "comment", 
"timeline_type": "comment"}


"""

#### BHJTW 09-02-2012
