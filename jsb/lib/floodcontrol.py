# jsb/lib/floodcontrol.py
#
#

""" JSONBOT flood control. """

## jsb imports

from jsb.utils.statdict import StatDict
from jsb.utils.lazydict import LazyDict
from jsb.lib.config import getmainconfig

## basic imports

import logging
import time

##

class FloodControl(object):

    def __init__(self):
        self.stats = StatDict()
        self.times = LazyDict()
        self.wait = LazyDict()
        self.warned = LazyDict()

    def reset(self, userhost):
        try: del self.times[userhost]
        except KeyError: pass
        try: del self.stats[userhost]
        except KeyError: pass
        try: del self.wait[userhost]
        except KeyError: pass
        try: del self.warned[userhost]
        except KeyError: pass

    def check(self, userhost, timetomonitor=60, threshold=10, wait=120, floodrate=1):
        u = userhost
        t = time.time()
        w = wait
        if self.times.has_key(u):
            if t - self.times[u] > w: self.reset(u) ; return False
            if (t - self.times[u] < timetomonitor): self.stats.upitem(u)
            if (self.stats.get(u) >  threshold) or (t - self.times[u] < floodrate): self.wait[userhost] = wait ; return True
        else: self.times[u] = t ; return False
        if self.stats.get(u) <= threshold: return False
        return True

    def checkevent(self, event, dobind=True):
        if not event.iscommand: return False
        if getmainconfig().floodallow: return False
        if dobind: event.bind()
        if not event.user: got = False
        else: got = True
        t = got and event.user.data.floodtime or 60
        if t < 60: t = 60
        threshold = got and event.user.data.floodthreshold or 20
        if threshold < 20: threshold = 20
        wait = got and event.user.data.floodwait or 120
        if wait < 120: wait = 120
        floodrate = got and event.user.data.floodrate or 0.1
        if floodrate < 0.1: floodrate = 0.1
        if not self.check(event.userhost, t, threshold, wait, floodrate): return False 
        if event.user and "OPER" in event.user.data.perms: return False
        logging.warn("floodcontrol block on %s" % event.userhost)
        if event.userhost not in self.warned:
            logging.warn("floodcontrol block on %s" % event.userhost)
            event.reply("floodcontrol enabled (%s seconds)" % wait)
        self.warned[event.userhost] = time.time()
        return True

floodcontrol = FloodControl()
