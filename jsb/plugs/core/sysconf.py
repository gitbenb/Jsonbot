# jsb/plugs/core/sysconf.py
#
#

""" show system configuration stuff. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.utils.exception import handle_exception

## basic imports

import os

## sysconf command

def handle_sysconf(bot, event):
    if bot.type != "console": event.reply("this command only works on the console bot") ; return
    if not event.rest: event.missing("<item>") ; return
    target = event.rest.upper()
    todo = []
    for item in os.sysconf_names:
        if target in item: todo.append(item)
    result = {}
    for t in todo:
        try: result[t] = os.sysconf(t)
        except Exception, ex: pass
    if result: event.reply("sysinfo found for %s" % target, result)
    else: event.reply("no result found for %s" % target)

cmnds.add("sysconf", handle_sysconf, "OPER")
examples.add("sysconf", "show sysconf information", "sysconf")
 