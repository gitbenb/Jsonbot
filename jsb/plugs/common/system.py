# jsb/plugs/common/system.py
#
#

""" system related commands. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples

## basic imports

import sys

## system-modules command

def handle_systemmodules(bot, event):
    res = []
    for name, mod in sys.modules.iteritems():
        if "jsb" in name and mod != None: res.append(name)
    res.sort()
    event.reply("jsb modules in sys.modules are: ", res)

cmnds.add("system-modules", handle_systemmodules, ["OPER", ])
examples.add("system-modules", "show the sys.modules contents", "sys-modules")
