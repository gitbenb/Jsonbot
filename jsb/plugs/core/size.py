# jsb/plugs/core/size.py
#
#

""" call a size() function in every module in sys.modules """

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples

## basic imports

import sys

## size command

def handle_size(bot, event):
    res = []
    mods = dict(sys.modules)
    for name, mod in mods.iteritems():
       if not 'jsb' in name: continue
       try: res.append("<i><%s></i> %s" % (name.split(".")[-1], unicode(getattr(mod, 'size')())))
       except (TypeError, AttributeError): continue
       except Exception, ex: handle_exception()
    event.reply("sizes in %s modules scanned: " % len(res), res, dot="<br>")

cmnds.add("size", handle_size, "OPER")
examples.add("size", "call size() functions in all available modules", "size")
