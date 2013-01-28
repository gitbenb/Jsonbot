# jsb/lib/sink.py
#
#

""" 
    sinkhole where all events are pushed to so final handling might take place.
    it is a thead with input queue, so the main process of event handling doesn't
    get stalled by the sink handling of these events.

"""

## jsb imports

from jsb.lib.threadloop import ThreadLoop
from jsb.utils.trace import whichmodule
from jsb.utils.dol import Dol
from jsb.lib.runner import longrunner
from jsb.utils.lazydict import LazyDict

## basic imports

import logging

## Sinker class


class Sinker(LazyDict):

     def __init__(self, cb, modname, cbtype, *args, **kwargs):
        self.modname = modname
        self.cb = cb
        self.cbtype = cbtype
        self.args = args
        self.kwargs = kwargs

## SinkHandler class

class SinkHandler(ThreadLoop):

    def __init__(self, name="", queue=None, *args, **kwargs):
        ThreadLoop.__init__(self, name, queue, *args, **kwargs)
        self.cbs = Dol()

    def register(self, cb, modname=None, cbtype=None, *args, **kwargs):
        """ register a sink callback. """
        modname = modname or whichmodule(2)
        self.cbs.add(Sinker(cb, modname, cbtype, *args, **kwargs))
        logging.warn("registered %s sink handler for the %s plugin" % (str(cb), modname))
 
    def unregister(self, modname=None):
        """ unregister a sink callback. """
        modname = modname or whichmodule(2)
        try: size = len(self.cbs[modname]) ; del self.cbs[modname] ; logging.warn("%s sink callbacks removed" % size)
        except KeyError: pass
 
    def handle(self, bot, event):
        """ handle a sink callback by pushing corresponding callbacks to the long runner. """
        cbslists = self.cbs.values()
        for cb in cbslists:
            for sinker in cbs:
                if sinker.cbtype and sinker.cbtype != event.cbtype: continue
                event.sinker = sinker
                longrunner.put(event.speed, sinker.cb, bot, event)

mainsink = SinkHandler()

#### BHJTW 25-7-2012