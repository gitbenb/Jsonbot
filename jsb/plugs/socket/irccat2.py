# jsb/plugs/socket/irccat2.py
#
#

"""
irccat.py - jsonbot "irccat" Module
Copyright 2011, Richard Bateman
Licensed under the New BSD License.

Written to be used in the #firebreath IRC channel: http://www.firebreath.org

To test, set up the host and port, then use something like:

echo "@taxilian I am awesome" | netcat -g0 localhost 54321

echo "#channel I am awesome" | netcat -g0 localhost 54321

you can specify multiple users (with @) and channels (with #) by seperating them
with commas.  Not that with jabber, channels tend to be treated as users
unless you set up an alias in your channel:

!irccat_add_alias #channel

BHJTW - 28-02-2012 .. move to irccat2.py to use the normal irccat-cfg functions


"""

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.lib.threads import start_new_thread
from jsb.lib.persist import PlugPersist
from jsb.lib.fleet import getfleet
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.callbacks import callbacks
from jsb.lib.persistconfig import PersistConfig
from jsb.utils.generic import fromenc, toenc
from jsb.lib.errors import BotNotEnabled

## basic imports

import logging
import time
import socket

## defines

cfg = PersistConfig()
cfg.define("botnames", ["default-sxmpp","default-irc"])
cfg.define("host", "localhost")
cfg.define("port", "54321")
cfg.define("aliases", {})
cfg.define("enable", False)

## SocketServer imports

import SocketServer
from SocketServer import ThreadingMixIn, StreamRequestHandler

## defines

shared_data = {}

server = None

## IrcCatListener class

class IrcCatListener(ThreadingMixIn, StreamRequestHandler):
    def handle(self):
        try:
            fleet = getfleet()
            msg = unicode(self.rfile.readline().strip())
            logging.warn("received %s" % msg)
            dest, msg = self.splitMsg(msg)
            for chan in dest:
                logging.info("sending to %s" % chan)
                for botname in fleet.list():
                    if botname not in cfg.botnames: continue
                    bot = fleet.byname(botname)
                    if bot: bot.say(chan, msg)
                    else: logging.error("can't find %s bot in fleet" % botname)
        except Exception, ex: handle_exception()

    def splitMsg(self, message):
        if message[0] not in ('#', '@'): return [], message
        if not message: return [], message
        if message.startswith('"'): messsage = message[1:-1]
        dest, message = message.split(" ", 1)
        dest = dest.split(",")
        finalDest = []
        for d in dest:
            if not d: continue
            d = d.strip().strip("@")
            finalDest.append(d)
            if d in cfg["aliases"].keys():
                for alias in cfg["aliases"][d]:
                    finalDest.append(alias)
        return finalDest, message

def dummycb(bot, event): pass

callbacks.add("START", dummycb)

def init_threaded():
    global server
    if server: logging.warn("irccat2 server is already running.") ; return
    if not cfg.enable: logging.warn("irccat2 is not enabled.") ; return 
    time.sleep(2)
    cfg["host"] = cfg["host"] or "localhost"
    cfg["port"] = cfg["port"] or 54321
    cfg["botnames"] = cfg["botnames"] or ["default-sxmpp",]
    cfg["aliases"] = cfg["aliases"] or {}
    if not cfg.aliases: cfg.aliases = {}
    cfg.save()
    try:
        server = SocketServer.TCPServer((cfg["host"], int(cfg["port"])), IrcCatListener)
    except socket.error, ex: logging.error("socket error occured: %s" % str(ex)) ; return
    except BotNotEnabled, ex: logging.warn("%s bot is not enabled" % str(ex)) ; return
    except Exception, ex: handle_exception() ; return
    logging.warn("starting irccat2 server on %s:%s" % (cfg["host"], cfg["port"]))
    thr = start_new_thread(server.serve_forever, ())
    thr.join(3)

def shutdown():
    global server
    if server:
        logging.warn("shutting down the irccat2 server")
        start_new_thread(server.shutdown, ())
        time.sleep(2)

## irccat2_add_alias command

def handle_irccat2_add_alias(bot, ievent):
    if len(ievent.args) != 1:
        ievent.reply("syntax: irccat2_add_alias <alias> (where <alias> is the channel you want notifications for)")
        return
    dest = ievent.args[0]
    if not cfg.aliases: cfg.aliases = {}
    if dest not in cfg["aliases"]:
        cfg["aliases"][dest] = []
    if ievent.channel not in cfg["aliases"][dest]:
        cfg["aliases"][dest].append(ievent.channel)
    cfg.save()
    ievent.reply("%s will now receive irccat2 messages directed at %s" % (ievent.channel, dest))
cmnds.add("irccat2_add_alias", handle_irccat2_add_alias, ['OPER'])
examples.add("irccat2_add_alias", "add an alias to the current channel from the specified one", "irccat2_add_alias #firebreath")

## irccat2_list_aliases command

def handle_irccat2_list_aliases(bot, ievent):
    """ List all aliases defined for the current channel """
    aliases = [dest for dest, chanlist in cfg["aliases"].iteritems() if ievent.channel in chanlist]

    ievent.reply("%s is receiving irccat2 messages directed at: %s" % (ievent.channel, ", ".join(aliases)))
cmnds.add("irccat2_list_aliases", handle_irccat2_list_aliases, ['OPER'])
examples.add("irccat2_list_aliases", "lists the aliases for the current channel", "irccat2_list_aliases")

## irccat2_del_alias command

def handle_irccat2_del_alias(bot, ievent):
    if len(ievent.args) != 1:
        ievent.reply("syntax: irccat2_del_alias <alias> (where <alias> is the channel you no longer want notifications for)")
        return
    dest = ievent.args[0]
    if dest not in cfg["aliases"]or ievent.channel not in cfg["aliases"][dest]:
        ievent.reply("%s is not an alias for %s" % (ievent.channel, dest))
        return
    cfg["aliases"][dest].remove(ievent.channel)
    ievent.reply("%s will no longer receive irccat2 messages directed at %s" % (ievent.channel, dest))
    cfg.save()
cmnds.add("irccat2_del_alias", handle_irccat2_del_alias, ['OPER'])
examples.add("irccat2_del_alias", "add an alias to the current channel from the specified one", "irccat2_del_alias #firebreath")

## irccat2_enable command

def handle_irccat2_enable(bot, event):
    cfg.enable = True ; cfg.save() ; event.done()
    init_threaded()
    
cmnds.add("irccat2-enable", handle_irccat2_enable, "OPER")
examples.add("irccat2-enable", "enable irccat2 server", "irccat2-enable")

## irccat2_disable command

def handle_irccat2_disable(bot, event):
    cfg.enable = False ; cfg.save() ; event.done()
    shutdown()
    
cmnds.add("irccat2-disable", handle_irccat2_disable, "OPER")
examples.add("irccat2-disable", "disable irccat2 server", "irccat2-disable")
