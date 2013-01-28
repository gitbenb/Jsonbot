# plugins/autovoice.py
#
#

""" do voice on join """

__copyright__ = 'this file is in the public domain'

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.lib.commands import cmnds
from jsb.lib.callbacks import callbacks
from jsb.lib.examples import examples

## basic imports

import re
import logging

## autovoice precondition

def preautovoice(bot, ievent):
    if ievent.forwarded or ievent.relayed: return False
    return True

## autovoice callback

def cbautovoice(bot, ievent):
    """ autovoice callback """
    chandata = 0
    if not ievent.chan: ievent.bind(bot, force=True)
    try: chandata = ievent.chan.data.autovoice
    except KeyError: return
    try:
        for regex in ievent.chan.data.autovoiceblacklist:
            r = regex.replace("*", ".*?")
            if re.search(r, ievent.userhost): logging.warn("%s in autovoice blacklist .. not giving voice." % ievent.userhost) ; return
    except: handle_exception() 
    if chandata: bot.voice(ievent.channel, ievent.nick)

callbacks.add('JOIN', cbautovoice, preautovoice)

## autovoice-on command

def handle_autovoiceon(bot, ievent):
    """ autovoice-on .. enable autovoice for channel the command was given in """
    try: ievent.chan.data.autovoice  = 1
    except TypeError: ievent.reply('no %s in channel database' % ievent.channel) ; return
    ievent.reply('autovoice enabled on %s' % ievent.channel)

cmnds.add('autovoice-on', handle_autovoiceon, 'OPER')
examples.add('autovoice-on', 'enable autovoice on channel in which the command is given', 'autovoice-on')

## autovoice-off command

def handle_autovoiceoff(bot, ievent):
    """ autovoice-off .. disable autovoice for the channel the command was given in """
    try:
        ievent.chan.data.autovoice = 0
        ievent.reply('autovoice disabled on %s' % ievent.channel)
    except TypeError: ievent.reply('no %s channel in database' % ievent.channel)

cmnds.add('autovoice-off', handle_autovoiceoff, 'OPER')
examples.add('autovoice-off', 'disable autovoice on channel in which the command is given', 'autovoice-off')

## autovoice-blacklistadd command

def handle_autovoice_blacklistadd(bot, event):
    if not event.rest: event.missing("<hostmask>") ; return
    if not event.chan.data.autovoiceblacklist: event.chan.data.autovoiceblacklist = []
    event.chan.data.autovoiceblacklist.append(event.rest)
    event.chan.save()
    event.done()

cmnds.add("autovoice-blacklistadd", handle_autovoice_blacklistadd, "OPER")
examples.add("autovoice-blacklistadd", "add a userhost mask to the autovoiceblacklist for users that should not get voice.", "autovoice-blacklistadd bart@127*")

## autovoice-blacklistdel command

def handle_autovoice_blacklistdel(bot, event):
    if not event.rest: event.missing("<hostmask>") ; return
    if not event.chan.data.autovoiceblacklist or not event.rest in event.chan.data.autovoiceblacklist: event.reply("%s is not in blacklist" % event.rest) 
    if event.chan.data.autovoiceblacklist: event.chan.data.autovoiceblacklist.remove(event.rest)
    event.chan.save()
    event.done()

cmnds.add("autovoice-blacklistdel", handle_autovoice_blacklistdel, "OPER")
examples.add("autovoice-blacklistdel", "delete a userhost mask from the autovoice blacklist", "autovoice-blacklistdel bart@127*")
