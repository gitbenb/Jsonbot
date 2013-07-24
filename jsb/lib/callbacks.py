# jsb/callbacks.py
#
#

""" 
    bot callbacks .. callbacks take place on registered events. a precondition 
    function can optionaly be provided to see if the callback should fire. 

"""

## jsb imports

from threads import getname, start_new_thread
from jsb.utils.locking import lockdec
from jsb.utils.exception import handle_exception
from jsb.utils.trace import calledfrom, whichplugin, callstack
from jsb.utils.statdict import StatDict
from jsb.utils.dol import Dol

## basic imports

import sys
import copy
import thread
import logging
import time

## locks

lock = thread.allocate_lock()
locked = lockdec(lock)
cpy = copy.deepcopy

## defines

stats = StatDict()

## Callback class

class Callback(object):

    """ class representing a callback. """

    def __init__(self, modname, func, prereq, kwargs, threaded=False, speed=5, force=False):
        self.modname = modname
        self.plugname = self.modname.split('.')[-1]
        self.func = func # the callback function
        self.prereq = prereq # pre condition function
        self.kwargs = kwargs # kwargs to pass on to function
        self.threaded = cpy(threaded) # run callback in thread
        self.speed = cpy(speed) # speed to execute callback with
        self.activate = False
        self.enable = True
        self.force = cpy(force)
 
## Callbacks class (holds multiple callbacks)

class Callbacks(object):

    """ 
        dict of lists containing callbacks.  Callbacks object take care of 
        dispatching the callbacks based on incoming events. see Callbacks.check()

    """

    def __init__(self):
        self.cbs = Dol()

    def size(self):
        """ return number of callbacks. """
        return self.cbs.size()

    def add(self, what, func, prereq=None, kwargs=None, threaded=False, nr=False, speed=5, force=False):
        """  add a callback. """
        what = what.upper()
        modname = calledfrom(sys._getframe())
        if not kwargs: kwargs = {}
        if nr != False: self.cbs.insert(nr, what, Callback(modname, func, prereq, kwargs, threaded, speed, force))
        else: self.cbs.add(what, Callback(modname, func, prereq, kwargs, threaded, speed, force))
        logging.debug('added %s (%s)' % (what, modname))
        return self

    register = add

    def unload(self, modname):
        """ unload all callbacks registered in a plugin. """
        unload = []
        for name, cblist in self.cbs.iteritems():
            index = 0
            for item in cblist:
                if item.modname == modname: unload.append((name, index))
                index += 1
        for callback in unload[::-1]:
            self.cbs.delete(callback[0], callback[1])
            logging.debug('unloaded %s (%s)' % (callback[0], modname))

    def disable(self, plugname):
        """ disable all callbacks registered in a plugin. """
        unload = []
        for name, cblist in self.cbs.iteritems():
            index = 0
            for item in cblist:
                if item.plugname == plugname: item.activate = False

    def activate(self, plugname):
        """ activate all callbacks registered in a plugin. """
        unload = []
        for name, cblist in self.cbs.iteritems():
            index = 0
            for item in cblist:
                if item.plugname == plugname: item.activate = True

    def whereis(self, cmnd):
        """ show where ircevent.CMND callbacks are registered """
        result = []
        cmnd = cmnd.upper()
        for c, callback in self.cbs.iteritems():
            if c == cmnd:
                for item in callback:
                    if not item.plugname in result: result.append(item.plugname)
        return result

    def list(self):
        """ show all callbacks. """
        result = []
        for cmnd, callbacks in self.cbs.iteritems():
            for cb in callbacks:
                result.append(getname(cb.func))
        return result

    def check(self, bot, event):

        """ check for callbacks to be fired. """
        self.reloadcheck(bot, event)
        type = event.cbtype or event.cmnd
        if self.cbs.has_key('ALL'):
            for cb in self.cbs['ALL']: self.callback(cb, bot, event)
        if self.cbs.has_key(type):
            target = self.cbs[type]
            for cb in target: self.callback(cb, bot, event)

    def callback(self, cb, bot, event):
        """  do the actual callback with provided bot and event as arguments. """
        #if event.stop: logging.info("callbacks -  event is stopped.") ; return
        if event.cbtype in bot.nocbs and not cb.force: logging.warn("%s in nocbs list, skipping" % event.cbtype) ; return
        event.calledfrom = cb.modname
        if not event.bonded: event.bind(bot)
        try:
            if event.status == "done":
                if not event.nolog: logging.debug("callback - event is done .. ignoring")
                stats.upitem("ignored")
                return
            if event.chan and cb.plugname in event.chan.data.denyplug:
                logging.warn("%s denied in %s - %s" % (cb.modname, event.channel, event.auth))
                stats.upitem("denied")
                return
            if cb.prereq:
                if not event.nolog: logging.info('executing in loop %s' % str(cb.prereq))
                if not cb.prereq(bot, event): return
            if not cb.func: return
            if event.isremote(): logging.info('%s - executing REMOTE %s - %s' % (bot.cfg.name, getname(cb.func), event.cbtype))
            elif not event.nolog: logging.info('%s - executing %s - %s' % (bot.cfg.name, getname(cb.func), event.cbtype))
            event.iscallback = True
            if not event.nolog: logging.debug("%s - %s - trail - %s" % (bot.cfg.name, getname(cb.func), callstack(sys._getframe())[::-1]))
            time.sleep(0.01)
            if cb.threaded: logging.info("PURE THREAD STARTED %s" % str(cb.func)) ; start_new_thread(cb.func, (bot, event))
            else:
                display = "%s/%s/%s" % (cb.plugname, bot.cfg.name, event.nick or event.channel)
                if event.cbtype == "API":
                    from runner import apirunner
                    apirunner.put(event.speed or cb.speed, display, cb.func, bot, event)
                elif  event.direct: cb.func(bot, event) 
                elif not event.dolong:
                    from runner import callbackrunner
                    callbackrunner.put(event.speed or cb.speed, display, cb.func, bot, event)
                else:
                    from runner import longrunner
                    longrunner.put(event.speed or cb.speed, display, cb.func, bot, event)
            stats.upitem(event.cbtype)
            stats.upitem("nrcallbacks")
            return True
        except Exception, ex:
            handle_exception()

    def reloadcheck(self, bot, event, target=None):
        """ check if plugin need to be reloaded for callback, """
        from boot import plugblacklist
        plugloaded = []
        done = []
        target = target or event.cbtype or event.cmnd
        if target in bot.nocbs: logging.warn("%s in nocbs list, skipping" % target) ; return
        if not event.cbtype == 'TICK': logging.debug("%s - checking for %s events" % (bot.cfg.name, target))
        try:
            from boot import getcallbacktable   
            p = getcallbacktable()[target]
        except KeyError:
            if not event.nolog: logging.debug("can't find plugin to reload for %s" % event.cmnd)
            return
        if not event.nolog: logging.debug("found %s" % unicode(p))
        for name in p:
            if name in bot.plugs: done.append(name) ; continue
            if plugblacklist and name in plugblacklist.data:
                logging.info("%s - %s is in blacklist" % (bot.cfg.name, name))
                continue
            elif bot.cfg.loadlist and name not in bot.cfg.loadlist:
                logging.info("%s - %s is not in loadlist" % (bot.cfg.name, name))
                continue
            if not event.nolog: logging.debug("%s - on demand reloading of %s" % (bot.cfg.name, name))
            try:
                mod = bot.plugs.reload(name, force=True, showerror=False)
                if mod: plugloaded.append(mod) ; continue
            except Exception, ex: handle_exception(event)
        if done and not event.nolog: logging.debug("%s - %s is already loaded" % (bot.cfg.name, str(done)))
        return plugloaded

## global callbacks

first_callbacks = Callbacks() 
cb = callbacks = Callbacks()
last_callbacks = Callbacks()
remote_callbacks = Callbacks()
api_callbacks = Callbacks()

def size():
    return "first: %s - callbacks: %s - last: %s - remote: %s" % (first_callbacks.size(), callbacks.size(), last_callbacks.size(), remote_callbacks.size(), api_callbacks.size())
