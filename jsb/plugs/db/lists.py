# dbplugs/lists.py
#
#
#

""" lists per user """

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.users import getusers
from jsb.db.direct import Db

## basic imports

import logging

## defines

db = None

## plugin initialisation

def init():
    global db
    from jsb.db import getmaindb
    db = getmaindb()

## size function

def size():
    """ return number of lists """
    global db
    if not db: logging.error("plugin isnt initialised yet") ; return 0
    result = db.execute(""" SELECT COUNT(*) FROM list """)
    return result[0][0]

## list functions

def getlists(username):
    """ get all lists of user """
    global db
    if not db: logging.error("plugin isnt initialised yet") ; return []
    result = db.execute(""" SELECT * FROM list WHERE username = %s """, username)
    return result

def getlist(username, listname):
    """ get list of user """
    global db
    if not db: logging.error("plugin isnt initialised yet") ; return []
    result = db.execute(""" SELECT * FROM list WHERE username = %s AND listname = %s """, (username, listname))
    return result

def addtolist(username, listname, item):
    """ add item to list """
    global db
    if not db: logging.error("plugin isnt initialised yet") ; return 0
    result = db.execute(""" INSERT INTO list(username, listname, item) VALUES(%s, %s, %s) """, (username, listname, item))
    return result

def delfromlist(username, indx):
    """ delete item from list """
    global db
    if not db: logging.error("plugin isnt initialised yet") ; return 0
    result = db.execute(""" DELETE FROM list WHERE username = %s AND indx = %s """, (username, indx))
    return result

def mergelist(username, listname, l):
    """ merge 2 lists """
    for i in l: addtolist(username, listname, i)

## lists commands

def handle_lists(bot, ievent):
    """ list <listname> [',' <item>] """
    if not ievent.rest: ievent.missing("<listname> [',' <item>]") ; return
    username = getusers().getname(ievent.userhost)
    try: listname, item = ievent.rest.split(',', 1)
    except ValueError:
        l = getlist(username, ievent.rest)
        if not l: ievent.reply('no %s list available' % ievent.rest) ; return
        result = []
        for i in l: result.append("%s) %s" % (i[0], i[3]))
        ievent.reply("results: ", result)
        return
    listname = listname.strip().lower()
    item = item.strip()
    if not listname or not item: ievent.missing("<listname> [',' <item>]") ; return
    ok = 0
    try: ok = addtolist(username, listname, item)
    except Exception, ex:
        handle_exception()
        ievent.reply('ERROR: %s' % str(ex))
        return
    if ok: ievent.reply('%s added to %s list' % (item, listname))
    else: ievent.reply('add failed')

cmnds.add('lists', handle_lists, 'USER')
examples.add('lists', "show content of list or add item to list", '1) lists bla 2) lists bla, mekker')

## lists-del command

def handle_listsdel(bot, ievent):
    """ list-del <listname> ',' <listofnrs> .. remove items with indexnr from list """
    if not ievent.rest: ievent.missing('<listofnrs>') ; return
    try:
        nrs = []
        for i in ievent.rest.split(): nrs.append(int(i))
    except ValueError: ievent.reply('%s is not an integer' % i) ; return
    username = getusers().getname(ievent.userhost)
    nrs.sort()
    failed = []
    itemsdeleted = 0
    try:
        for i in nrs:
            result = delfromlist(username, i)
            if not result: failed.append(str(i))
            else: itemsdeleted += 1
    except Exception, ex:
        handle_exception()
        ievent.reply('ERROR: %s' % str(ex))
        return
    if failed: ievent.reply('failed to delete %s' % ' '.join(failed))
    ievent.reply('%s item(s) removed' % itemsdeleted)

cmnds.add('lists-del', handle_listsdel, 'USER')
examples.add('lists-del', "remove items with indexnr from list", '1) lists-del mekker , 1 2) lists-del mekker , 0 3 6')

## lists-show command

def handle_listsshow(bot, ievent):
    """ show avaiable lists """
    username = getusers().getname(ievent.userhost)
    l = getlists(username)
    if not l: ievent.reply('no lists available') ; return
    else:
        result = []
        for i in l:
            if not i[2] in result: result.append(i[2])
        if result: ievent.reply("lists: ", result)

cmnds.add('lists-show', handle_listsshow, 'USER')
examples.add('lists-show', 'show available channel list' , 'lists-show')

## lists-merge command

def handle_listsmerge(bot, ievent):
    """ merge 2 list """
    try: (fromlist, tolist) = ievent.args
    except ValueError: ievent.missing('<fromlist> <tolist>') ; return
    username = getusers().getname(ievent.userhost)
    res = getlist(username, fromlist)
    if not res:  ievent.reply('no %s list available or empty' % fromlist) ; return
    l = []
    for i in res: l.append(i[3])
    result = 0
    try: result = mergelist(username, tolist, l)
    except Exception, ex:
        handle_exception()
        ievent.reply('ERROR: %s' % str(ex))
        return
    ievent.reply('%s items merged' % result)

cmnds.add('lists-merge', handle_listsmerge, 'USER')
examples.add('lists-merge', 'merge 2 lists', 'lists-merge mekker miep')
