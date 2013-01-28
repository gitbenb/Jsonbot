# plugs/infoitem.py
#
#

"""
    information items .. keyword/description pairs

    learn the bot something with: !<item> = <description>
    question goes with: !<item>?

"""

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.datadir import datadir
from jsb.utils.locking import lockdec
from jsb.lib.callbacks import callbacks
from jsb.lib.users import getusers
from jsb.lib.config import getmainconfig

## basic imports

import thread
import os
import time
import logging

## locks

infolock = thread.allocate_lock()
locked = lockdec(infolock)

## defines

db = None

## InfoItemsDb class

class InfoItemsDb(object):

    """ information items """

    def add(self, item, description, userhost, ttime):
        """ add an item """
        if not db: logging.error("plugin isnt initialised yet") ; return []
        item = item.lower()
        result = db.execute(""" INSERT INTO infoitems(item, description, userhost, time) VALUES(%s, %s, %s, %s) """, (item, description, userhost, ttime))
        return result

    def get(self, item):
        """ get infoitems """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        item = item.lower()
        result = db.execute(""" SELECT description FROM infoitems WHERE item = %s """, item)
        res = []
        if result:
            for i in result: res.append(i[0])
        return res

    def delete(self, indexnr):
        """ delete item with indexnr  """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        result = db.execute(""" DELETE FROM infoitems WHERE indx = %s """, indexnr)
        return result

    def deltxt(self, item, txt):
        """ delete item with matching txt """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        result = db.execute(""" DELETE FROM infoitems WHERE item = %s AND description LIKE %s """, (item, '%%%s%%' % txt))
        return result

    def size(self):
        """ return number of items """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        result = db.execute(""" SELECT COUNT(*) FROM infoitems """)
        return result[0][0]

    def searchitem(self, search):
        """ search items """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        result = db.execute(""" SELECT item, description FROM infoitems WHERE item LIKE %s """, '%%%s%%' % search)
        return result

    def searchdescr(self, search):
        """ search descriptions """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        result = db.execute(""" SELECT item, description FROM infoitems WHERE description LIKE %s """, '%%%s%%' % search)
        return result

## defines

info = InfoItemsDb()

## size function

def size():
    """ return number of infoitems """
    return info.size()

## info callbacks

def infopre(bot, ievent):
    """ see if info callback needs to be called """
    if ievent.iscmnd() and (ievent.txt and ievent.txt[-1] == "?") and not ievent.woulddispatch(): return True

def infocb(bot, ievent):
    """ implement a !infoitem callback """
    if getusers().allowed(ievent.userhost, 'USER'):
        data = info.get(ievent.execstr)
        if data: ievent.reply('%s is: ' % ievent.execstr, data)

callbacks.add('PRIVMSG', infocb, infopre)

## info-size command

def handle_infosize(bot, ievent):
    """ info-size .. show number of information items """
    ievent.reply("we have %s infoitems" % info.size())

cmnds.add('info-size', handle_infosize, ['USER', 'WEB', 'ANON'])
examples.add('info-size', 'show number of infoitems', 'info-size')

## addinfoitem RE

def handle_addinfoitem(bot, ievent):
    """ <keyword> = <description> .. add information item """
    if not ievent.hascc(): return
    try: (what, description) = ievent.groups
    except ValueError: ievent.reply('i need <item> <description>') ; return
    if len(description) < 3: ievent.reply('i need at least 3 chars for the description') ; return
    what = what.strip()[1:]
    info.add(what, description, ievent.userhost, time.time())
    ievent.reply('item added')

cmnds.add('^(.+?)\s+=\s+(.+)$', handle_addinfoitem, ['USER', 'INFOADD'], regex=True, needcc=True)
examples.add('=', 'add description to item', 'dunk = top')

## question RE

def handle_question(bot, ievent):
    """ <keyword>? .. ask for information item description """
    if not ievent.hascc(): return
    try: what = ievent.groups[0]
    except IndexError: ievent.reply('i need a argument') ; return
    what = what.strip().lower()[1:]
    infoitems = info.get(what)
    if infoitems: ievent.reply("%s is: " % what, infoitems)
    else: ievent.reply('nothing known about %s' % what) ; return

cmnds.add('^(.+)\?$', handle_question, ['USER', 'WEB', 'JCOLL', 'ANON'], regex=True, needcc=True)
cmnds.add('^\?(.+)$', handle_question, ['USER', 'WEB', 'JCOLL', 'ANON'], regex=True, needcc=True)
examples.add('?', 'show infoitems of <what>', '1) test? 2) ?test')

## info-forget command

def handle_forget(bot, ievent):
    """ forget <keyword> <txttomatch> .. remove information item where \
        description matches txt given """
    if len(ievent.args) > 1: what = ' '.join(ievent.args[:-1]) ; txt = ievent.args[-1]
    else: ievent.missing('<item> <txttomatch> (min 3 chars)') ; return
    if len(txt) < 3: ievent.reply('i need txt with at least 3 characters') ; return
    what = what.strip().lower()
    try: nrtimes = info.deltxt(what, txt)
    except KeyError: ievent.reply('no records matching %s found' % what) ; return
    if nrtimes: ievent.reply('item deleted')
    else: ievent.reply('delete %s of %s failed' % (txt, what))

cmnds.add('info-forget', handle_forget, ['FORGET', 'OPER'])
examples.add('info-forget', 'forget <item> containing <txt>', 'info-forget dunk bla')

## info-sd command

def handle_searchdescr(bot, ievent):
    """ info-sd <txttosearchfor> .. search information items descriptions """
    if not ievent.rest: ievent.missing('<txt>') ; return
    else: what = ievent.rest
    what = what.strip().lower()
    result = info.searchdescr(what)
    if result: 
        res = []
        for i in result: res.append("[%s] %s" % (i[0], i[1]))
        ievent.reply("the following matches %s: " % what, res)
    else: ievent.reply('none found')

cmnds.add('info-sd', handle_searchdescr, ['USER', 'WEB', 'ANON'])
examples.add('info-sd', 'info-sd <txt> ..  search description of infoitems', 'info-sd http')

## info-si command

def handle_searchitem(bot, ievent):
    """ info-si <txt> .. search information keywords """
    if not ievent.rest: ievent.missing('<txt>') ; return
    else: what = ievent.rest
    what = what.strip().lower()
    result = info.searchitem(what)
    if result:
        res = []
        for i in result: res.append("[%s] %s" % (i[0], i[1]))
        ievent.reply("the following matches %s: " % what, res)
    else: ievent.reply('none found')

cmnds.add('info-si', handle_searchitem, ['USER', 'WEB', 'ANON'])
examples.add('info-si', 'info-si <txt> ..  search the infoitems keys', 'info-si test')

## plugin initialisation

def init():
    global db
    from jsb.db import getmaindb
    db = getmaindb()
