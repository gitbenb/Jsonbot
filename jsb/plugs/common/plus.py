# jsb/plugs/common/plus.py
#
#

""" plugin to query the Google+ API. """

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.utils.lazydict import LazyDict
from jsb.utils.url import geturl2
from jsb.lib.persistconfig import PersistConfig
from jsb.lib.persiststate import PlugState
from jsb.lib.jsbimport import _import_byfile
from jsb.lib.datadir import getdatadir
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.fleet import getfleet
from jsb.lib.periodical import minutely, periodical
from jsb.imports import getjson

json = getjson()

## basic imports

import os
import logging
import uuid

## defines

cfg = PersistConfig()
cfg.define("enable", 0)

state = PlugState()
state.define("ids", {})
state.define("seen", {})

teller = 0

## getplus function

def getplus(target):
    credentials = _import_byfile("credentials", getdatadir() + os.sep + "config" + os.sep + "credentials.py")
    url = "https://www.googleapis.com/plus/v1/people/%s/activities/public?alt=json&pp=1&key=%s" % (target, credentials.googleclient_apikey)
    result = geturl2(url)
    data = json.loads(result)
    res = []
    for item in data['items']:
        i = LazyDict(item)
        res.append("%s - %s - %s" % (i.actor['displayName'], i['title'], item['url']))
    return res

## PlusLoop class

@minutely
def plusscan(skip=False):
    global teller
    teller += 1
    if teller % 5 != 0: return 
    logging.warn("running plus scan")
    fleet = getfleet()
    for id, channels in state.data.ids.iteritems():
        if not id in state.data.seen: state.data.seen[id] = []
        for botname, chan in channels:
            try:
                res = getplus(id)
                if not res: logging.warn("no result from %s" % id) ; continue
                bot = fleet.byname(botname)
                if bot:
                    todo = []
                    for r in res:
                        stamp = uuid.uuid3(uuid.NAMESPACE_URL, str(r)).hex
                        if stamp not in state.data.seen[id]:
                            state.data.seen[id].append(stamp)
                            todo.append(r)
                    if todo: bot.say(chan, "new plus update: " , todo)
                else: logging.warn("no %s bot in fleet" % botname)
            except AttributeError, ex: logging.error(str(ex))
            except Exception, ex: handle_exception()
    state.save()

## plus command

def handle_plus(bot, event):
    if event.args: target = event.args[0]
    else: event.missing("userid") ; return
    try: res = getplus(target)
    except Exception, ex: event.reply("an error occured: %s" % str(ex)) ; return
    if res: event.reply("results: ", res, dot=" || ")
    else: event.repy("no data found")

cmnds.add("plus", handle_plus, ["OPER", "USER"])
examples.add("plus", "query activities of a userid on google+", "plus 115623252983295760522")

## plus-start command

def handle_plusstart(bot, event):
    if not event.args: event.missing("<g+ id>") ; return
    global state
    gid = event.args[0]
    target = [bot.cfg.name, event.channel]
    if not state.data.ids.has_key(gid): state.data.ids[gid] = []
    if not target in state.data.ids[gid]:
        state.data.ids[gid].append(target)
        state.save()
        event.done()
    else: event.reply("we are already monitoring %s in %s" % (gid, str(target)))

cmnds.add("plus-start", handle_plusstart, ["OPER", ])
examples.add("plus-start", "start monitoring a google+ id into the channel", "plus-start 115623252983295760522")

## plus-stop command

def handle_plusstop(bot, event):
    if not event.args: event.missing("<g+ id>") ; return
    global state
    gid = event.args[0]
    try:
        del state.data.ids[gid]
        state.save()
        event.done()
    except (KeyError, ValueError): event.reply("we are already monitoring %s" % gid)

cmnds.add("plus-stop", handle_plusstop, ["OPER", ])
examples.add("plus-stop", "stop monitoring a google+ id", "plus-stop 115623252983295760522")


def handle_pluslist(bot, event): event.reply("ids list: ", state.data.ids) 

cmnds.add("plus-list", handle_pluslist, ['OPER', ])

def init():
    if cfg.enable: plusscan(True)

def shutdown():
    periodical.kill()
