# jsb/plugs/entry.py
#
#

""" entry plugin. """

# botlib imports

from botlib import O, cmnds, cb
from botlib.utils import strtotime, strtorepeat

## Entry class

class Entry(O): pass

## pre_entry precondition

def pre_entry(event):
    if event.cbtype == "PRIVMSG":
        if event.user_cmnd == "entry": event.txt = event.rest ; return True
        return False
    if not event.txt or event.user_cmnd: return False
    return True

## entry callback

def do_entry(event):
    entry = Entry(**event)
    entry.time_alert = strtotime(event.rest)
    entry.interval = strtorepeat(event.rest)
    entry.tags = entry.get_tags()
    entry.save()
    event.reply("saved on %s" % entry.time)

do_entry.pre = pre_entry

cb.register("LINE", do_entry)
cb.register("CONSOLE", do_entry)
cb.register("MESSAGE", do_entry)
cb.register("PRIVMSG", do_entry)
