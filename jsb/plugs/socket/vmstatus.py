# jsb/plugs/socket/vmstatus.py
#
#

""" cat the output of /proc/<botpid>/status. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples

## basic imports

import os

## vmstatus command

def handle_vmstatus(bot, event):
    result = open("/proc/%s/status" % os.getpid(), "r").read()
    event.reply("vmstatus results: ", result.split("\n"))

cmnds.add("vmstatus", handle_vmstatus, ["OPER", ])
examples.add("vmstatus", "show output of /proc/<botpid>/status", "vmstatus")
