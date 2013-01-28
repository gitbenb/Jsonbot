# jsb/plugs/common/greeting.py
#
#

""" send a welcome greeting. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.callbacks import callbacks

## basic imports

import time

## greeting precondition

def greetingpre(bot, event):
    if event.chan and event.chan.data.greetingmsg: return True
    return False

## greeting callback

def greetingcb(bot, event):
    txt = event.chan.data.greetingmsg
    txt = txt.replace("$nick", event.nick)
    txt = txt.replace("$channel", event.channel)
    txt = txt.replace("$time", time.ctime(time.time()))
    bot.say(event.nick, txt)

callbacks.add("JOIN", greetingcb, greetingpre)

## greeting-set command

def handle_greetingset(bot, event):
    if not event.rest: event.missing("<greeting message>") ; return
    event.chan.data.greetingmsg = event.rest
    event.chan.save()
    event.done()

cmnds.add("greeting-set", handle_greetingset, 'OPER')
examples.add("greeting-set", "set the channel greetings message, you can use $nick, $channel or $time", "greeting-set hello $nick, welcome in $channel")

## greeting-del command

def handle_greetingdel(bot, event):
    event.chan.data.greetingmsg = ""
    event.chan.save()
    event.done()

cmnds.add("greeting-del", handle_greetingdel, "OPER")
examples.add("greeting-del", "remove greeting message", "greeting-del")

#### BHJTW 11-04-2012
