# jsb/lib/fleet.py
#
#

""" fleet is a list of bots. """

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.utils.generic import waitforqueue
from jsb.utils.trace import whichmodule
from config import Config, getmainconfig
from datadir import getdatadir
from users import users
from plugins import plugs
from persist import Persist
from errors import NoSuchBotType, BotNotEnabled
from threads import start_new_thread
from eventhandler import mainhandler
from jsb.utils.name import stripname
from jsb.lib.factory import BotFactory
from jsb.utils.lazydict import LazyDict

## simplejson imports

from jsb.imports import getjson
json = getjson()

## basic imports

import Queue
import os
import types
import time
import glob
import logging
import threading
import thread
import copy

## defines

cpy = copy.deepcopy

## classes

class FleetBotAlreadyExists(Exception):
    pass

## locks

from jsb.utils.locking import lockdec
lock = thread.allocate_lock()
locked = lockdec(lock)

## Fleet class

class Fleet(Persist):

    """
        a fleet contains multiple bots (list of bots).

    """

    def __init__(self, datadir):
        Persist.__init__(self, datadir + os.sep + 'fleet' + os.sep + 'fleet.main')
        if not self.data.has_key('names'): self.data['names'] = []
        if not self.data.has_key('types'): self.data['types'] = {}
        self.startok = threading.Event()
        self.bots = []

    def addnametype(self, name, type):
        if name not in self.data['names']:
            self.data['names'].append(name)
            self.data['types'][name] = type
            self.save()
        return True

    def getenabled(self, exclude=[]):
        res = []
        for name in self.data.names:
            cfg = Config("fleet" + os.sep + name + os.sep + "config")
            if cfg.type in exclude: continue
            if not cfg.disable: res.append(name)
        return res

    def loadall(self, names=[]):
        """ load all bots. """ 
        target = names or self.data.names or []
        threads = []
        bots = []
        for name in target:
            if not name: logging.warn("name is not set") ; continue
            try:
                bot = self.makebot(self.data.types[name], name)
                if not bot: logging.info("can't load %s bot" % name) ; continue
            except KeyError: logging.error("no type know for %s bot" % name) ; continue
            except Exception, ex: handle_exception()
            if bot and bot not in bots: bots.append(bot)
        return bots

    def avail(self):
        """ return available bots. """
        return self.data['names']

    def getfirstbot(self, type="irc"):
        """ return the first bot in the fleet. """
        for bot in self.bots:
            if type in bot.type: return bot

    def getfirstjabber(self):
        """ return the first jabber bot of the fleet. """
        return self.getfirstbot("xmpp")
        
    def size(self):
        """ return number of bots in fleet. """
        return len(self.bots)

    def settype(self, name, type):
        """ set the type of a bot. """
        cfg = Config('fleet' + os.sep + stripname(name) + os.sep + 'config')
        cfg['name'] = name
        logging.debug("%s - setting type to %s" % (self.cfile, type))
        cfg.type = type
        cfg.save()

    def makebot(self, type, name, config={}, domain="", showerror=False):
        """ create a bot .. use configuration if provided. """
        if not name: logging.error(" name is not correct: %s" % name) ; return
        if not type: type = self.data.types.get(name)
        if not type: logging.error("no type found for %s bot" % name) ; return 
        if config: logging.debug('making %s (%s) bot - %s - from: %s' % (type, name, config.tojson(), whichmodule()))
        bot = None
        if not config: cfg = Config('fleet' + os.sep + stripname(name) + os.sep + 'config')
        else: cfg = config 
        cfg.init()
        if not cfg.name: cfg['name'] = name
        cfg['botname'] = cfg['name']
        if cfg.disable:
            logging.info("%s bot is disabled. see %s" % (name, cfg.cfile))
            return 
        if not cfg.type and type:
            logging.debug("%s - setting type to %s" % (cfg.cfile, type))
            cfg.type = type
        if not cfg['type']:
            try:
                self.data['names'].remove(name)
                self.save()
            except ValueError: pass
            raise Exception("no bot type specified")
        if not cfg.owner:
            logging.debug("%s - owner not set .. using global config." % cfg.name) 
            cfg.owner = getmainconfig().owner
        if not cfg.domain and domain: cfg.domain = domain
        if not cfg: raise Exception("can't make config for %s" % name)
        #cfg.save()
        bot = BotFactory().create(type, cfg)
        return bot

    def save(self):
        """ save fleet data and call save on all the bots. """
        Persist.save(self)
        for i in self.bots:
            try: i.save()
            except Exception, ex: handle_exception()

    def list(self):
        """ return list of bot names. """
        result = []
        for i in self.bots: result.append(i.cfg.name)
        return result

    def stopall(self):
        """ call stop() on all fleet bots. """
        for i in self.bots:
            try: i.stop()
            except: handle_exception()

    def byname(self, name):
        """ return bot by name. """
        for i in self.bots:
            if name == i.cfg.name: return i

    def replace(self, name, bot):
        """ replace bot with a new bot. """
        for i in range(len(self.bots)):
            if name == self.bots[i].cfg.name:
                self.bots[i] = bot
                return True

    def enable(self, cfg):
        """ enable a bot baed of provided config. """
        if cfg.name and cfg.name not in self.data['names']:
            self.data['names'].append(cfg.name)
            self.data['types'][cfg.name] = cfg.type
            self.save()
        return True

    def addbot(self, bot):
        """
            add a bot to the fleet .. remove all existing bots with the 
            same name.
        """
        assert bot
        if not bot in self.bots: self.bots.append(bot)
        else: logging.warn("%s bot is already in fleet" % bot.cfg.name) ; return False
        self.addnametype(bot.cfg.name, bot.type)
        logging.info('added %s' % bot.cfg.name)
        return True

    def delete(self, name):
        """ delete bot with name from fleet. """
        for bot in self.bots:
            if bot.cfg.name == name:
                bot.exit()
                self.remove(bot)
                bot.cfg['disable'] = 1
                bot.cfg.save()
                logging.debug('%s disabled' % bot.cfg.name)
                return True
        return False

    def remove(self, bot):
        """ delete bot by object. """
        try:
            self.bots.remove(bot)
            return True
        except ValueError:
            return False

    def exit(self, name=None, jabber=False):
        """ call exit on all bots. """
        if not name:
            threads = []
            for bot in self.bots:
                if jabber and bot.type != 'sxmpp' and bot.type != 'jabber': continue
                threads.append(start_new_thread(bot.exit, ()))
            for thread in threads: thread.join()
            return
        for bot in self.bots:
            if bot.cfg.name == name:
                if jabber and bot.type != 'sxmpp' and bot.type != 'jabber': continue
                try: bot.exit()
                except: handle_exception()
                self.remove(bot)
                return True
        return False

    def cmnd(self, event, name, cmnd):
        """ do command on a bot. """
        bot = self.byname(name)
        if not bot: return 0
        j = cpy(event)
        j.bot = bot
        j.txt = cmnd
        j.displayname = j.bot.cfg.name
        j.execute()
        return j.wait()

    def cmndall(self, event, cmnd):
        """ do a command on all bots. """
        for bot in self.bots: self.cmnd(event, bot.cfg.name, cmnd)

    def broadcast(self, txt):
        """ broadcast txt to all bots. """
        for bot in self.bots: bot.broadcast(txt)

    def boot(self, botnames=[], exclude=[], all=False):
        if not botnames and all: botnames = self.getenabled(exclude)
        bots = self.loadall(botnames)
        todo = []
        done = []
        for bot in bots:
            if not bot: continue
            logging.debug("%s bot type is %s" % (bot.cfg.name, bot.type))
            if bot.type not in exclude: todo.append(bot) ; done.append(bot.cfg.name)
        if todo: start_new_thread(self.startall, (todo, ))
        if done: logging.warn("fleet bots are %s" % ", ".join(done))
        else: logging.warn("no fleet bots are enabled, see %s" % getdatadir() + os.sep + "config" + os.sep +'fleet')

    def startall(self, bots, usethreads=True):
        threads = []
        target = bots or self.bots
        for bot in target:
            logging.warn('starting %s bot (%s)' % (bot.cfg.name, bot.type))
            if usethreads or bot.type in ["sleek", "tornado"]: threads.append(start_new_thread(bot.boot, ())) ; continue
            try: bot.boot()
            except Excepton, ex: handle_exception()
            time.sleep(1)
        if usethreads:
           for t in threads: t.join(15)
        time.sleep(5)
        self.startok.set()

    def resume(self, sessionfile, exclude=[]):
        """ resume bot from session file. """
        session = json.load(open(sessionfile, 'r'))
        chan = session.get("channel")
        for name, cfg in session['bots'].iteritems():
            dont = False
            for ex in exclude:
                if ex in name: dont = True
            if dont: continue
            cfg = LazyDict(cfg)
            try: 
                if not cfg.disable:
                    logging.info("resuming %s" % cfg)
                    start_new_thread(self.resumebot, (cfg, chan))
            except: handle_exception() ; return
        time.sleep(10)
        self.startok.set()

    def resumebot(self, botcfg, chan=None):
        """ resume single bot. """
        botname = botcfg.name
        logging.warn("resuming %s bot" % botname)
        oldbot = self.byname(botname)
        if oldbot and botcfg['type'] in ["sxmpp", ]: oldbot.exit()
        bot = self.makebot(botcfg.type, botname)
        bot._resume(botcfg, botname)
        bot.start(False)
        self.addbot(bot)
        if chan and chan in bot.state["joinedchannels"]: bot.say(chan, "done!")

## global fleet object

fleet = None

@locked
def getfleet(datadir=None, new=False):
    if not datadir:
        from jsb.lib.datadir import getdatadir 
        datadir = getdatadir()
    global fleet
    if not fleet or new:
        fleet = Fleet(datadir)
    return fleet

def size():
    return getfleet().size()