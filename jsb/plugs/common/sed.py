# Description: Performs a sed-like substitution on the last message by the 
#              calling user
# Author: John Hampton <pacopablo@pacopablo.com>
# Website: http://pacopablo.com
# License: BSD
#
# BHJTW: ported to JSONBOT 27-8-2012

__author__ = 'John Hampton <pacopablo@pacopablo.com>'
__license__ = "BSD"
__status__ = "seen"

## jsb imports

from jsb.lib.callbacks import callbacks
from jsb.lib.commands import cmnds
from jsb.lib.datadir import datadir
from jsb.utils.pdod import Pdod
from jsb.lib.persistconfig import PersistConfig
from jsb.lib.examples import examples

## basic imports

import os
import time
import re
import logging

## defines

cfg = PersistConfig()
cfg.define('cmd_req', 0)
cfg.define('channels', [])
sed_expression = r'^s([/|#.:;])(.*?)\1(.*?)\1?([gi]*)$'
sedre = re.compile(sed_expression)

## LastLine class

class LastLine(Pdod):
    def __init__(self):
        self.datadir = os.path.join(datadir, 'plugs', 'jsb.plugs.common.sed')
        Pdod.__init__(self, os.path.join(self.datadir, 'sed.data'))
        if not self.data:
            self.data = {}

    def handle_sed(self, bot, ievent):
        """ Perform substitution """
        target = [bot.cfg.name, ievent.channel]
        if target not in cfg.channels: logging.warn("sed is not enabled in %s" % str(target)) ; return
        ievent.untildone = True
        channel = ievent.channel.lower()
        nick = ievent.nick.lower()
        try:
            (delim, broke, fix, flags) = ievent.groups
        except ValueError:
            ievent.missing('<delim><broke><delim><fix><delim>')
            return
        try:
            source = self.data[channel][nick]
            if 'g' in flags:
                count = 0
            else:
                count = 1
            if 'i' in flags:
                broke = '(?i)'+broke
            new_text = re.sub(broke, fix, source, count)

            if source != new_text:
                ievent.reply("%s meant: %s" % (nick, new_text))
                return
        except KeyError:
            ievent.reply('I wasn\'t listening to you.  Try saying something first.')
        except Exception, ex:
            ievent.reply('Error processing regex: %s' % str(ex))
        ievent.done(silent=True)

    def precb(self, bot, ievent):
        if ievent.iscommand or ievent.regex: return False
        target = [bot.cfg.name, ievent.channel]
        if target not in cfg.channels: logging.debug("sed is not enabled in %s" % str(target)) ; return
        else: return True 

    def privmsgcb(self, bot, ievent):
        channel = ievent.channel.lower()
        nick = ievent.nick.lower()
        regex = sedre.match(ievent.txt)
        if not cfg.get('cmd_req') and regex:
            try:
                (delim, broke, fix, flags) = regex.groups()
            except ValueError:
                return
            try:
                source = self.data[channel][nick]
                if 'g' in flags:
                    count = 0
                else:
                    count = 1
                if 'i' in flags:
                    broke = '(?i)'+broke
                new_text = re.sub(broke, fix, source, count)
                if source != new_text:
                    ievent.reply("%s meant: %s" % (nick, new_text))
                    return

            except KeyError:
                return
            except Exception, ex:
                ievent.reply('Error processing regex: %s' % str(ex))
        self.data.setdefault(channel, {})
        if not regex: self.data[channel][nick] = ievent.txt

## defines

lastline = None

## sed command

def handle_sed(bot, ievent):
    global lastline
    lastline.handle_sed(bot, ievent)

## init function

def init():
    global lastline
    lastline = LastLine()
    callbacks.add('PRIVMSG', lastline.privmsgcb, lastline.precb)
    callbacks.add('CONSOLE', lastline.privmsgcb, lastline.precb)
    callbacks.add('Message', lastline.privmsgcb, lastline.precb)
    cmnds.add(sed_expression, handle_sed, 'USER', regex=True)
    examples.add('s', 'Perform substitution on last message spoken.', 's/foo/bar/')
    return 1

## sed-enable command

def handle_sedenable(bot, event):
    target = [bot.cfg.name, event.channel]
    if not target in cfg.channels:
        cfg.channels.append(target)
        cfg.save()
        event.reply("sed enabled in %s" % str(target))
    else: event.reply("sed is already enabled in %s" % str(target))

cmnds.add("sed-enable", handle_sedenable, "OPER")
examples.add("sed-enable", "enable the sed plugin in the channel (the command is given in)", "sed-enable")    

## sed-disable command

def handle_seddisable(bot, event):
    target = [bot.cfg.name, event.channel]
    try: 
        cfg.channels.remove(target)
        cfg.save()
        event.reply("sed disabled in %s" % str(target))
    except ValueError: event.reply("sed not enabled in %s" % str(target))

cmnds.add("sed-disable", handle_seddisable, "OPER")
examples.add("sed-disable", "disable the sed plugin in the channel (the command is given in)", "sed-disable")    

## sed-list command

def handle_sedlist(bot, event):
    event.reply("sed enabled channels: ", cfg.channels)

cmnds.add("sed-list", handle_sedlist, "OPER")
examples.add("sed-list", "list sed enabled channels", "sed-list")

## shutdown function

def shutdown():
    if lastline: lastline.save()
    
#### BHJTW 23-01-2012
