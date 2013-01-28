# jsb/plugs/common/input.py
#
#

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.callbacks import callbacks
from jsb.lib.persist import PlugPersist, PlugPersistCollection
from jsb.utils.timeutils import strtotime

## basic imports

import os
import time
import string

import jsb.utils.name

jsb.utils.name.allowednamechars += string.printable

class InputData(PlugPersist): pass

## input callback

def input(bot, event):
    inp = event.txt
    if inp.startswith(";in "): inp = inp[4:]
    timed = strtotime(inp)
    fn = "%s,%s,%s,%s,%s" % (event.channel, timed or "", event.cbtype, event.ctime, inp[:200])
    input = InputData(fn)
    input.data = event.tojson()
    if ";in" in event.txt or not ";" in event.txt: input.save() ; event.reply("ok")

callbacks.add("CONSOLE", input)
cmnds.add("in", input, ["OPER", "USER"])

def look(bot, event):
    coll = PlugPersistCollection()
    fns = coll.filenames(event.rest)
    for fn in fns:
        try: cbtype, todotime, channel, ctime, txt = fn.split(",", 4)
        except ValueError as ex: print ex
        bot._raw("%s - %s" % (time.ctime(float(ctime)), txt))

cmnds.add("look", look, ["OPER", "USER"])
