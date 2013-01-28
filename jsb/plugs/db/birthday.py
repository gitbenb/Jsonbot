# dbplugs/birthday.py
#
#

""" manage birthdays """

## jsb imports

from jsb.utils.timeutils import getdaymonth, strtotime, elapsedstring, bdmonths
from jsb.utils.generic import getwho
from jsb.utils.exception import handle_exception
from jsb.lib.users import users
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.db import getmaindb

# basic imports

import time
import re

## defines

db = None

## bd-set command

def handle_bdset(bot, ievent):
    """ bd-set <date> .. set birthday """
    global db
    if not db: ievent.reply("plugin isnt initialised yet") ; return
    try:
        what = ievent.args[0]
        if not re.search('\d*\d-\d*\d-\d\d\d\d', what): ievent.reply('i need a date in the format day-month-year') ; return
    except IndexError: ievent.missing('<date>') ; return
    name = bot.users.getname(ievent.userhost)
    try: db.execute(""" INSERT INTO birthday (name, birthday) VALUES(%s, %s) """ , (name, what))
    except:
        try: db.execute(""" UPDATE birthday SET birthday = %s WHERE name = %s """,  (what, name))
        except Exception, ex:
            handle_exception()
            ievent.reply('ERROR: %s' % str(ex))
            return
    ievent.reply('birthday set')

cmnds.add('bd-set', handle_bdset, 'USER')
examples.add('bd-set', 'bd-set <date> .. set birthday', 'bd-set 3-11-1967')

## bd-del command

def handle_bddel(bot, ievent):
    """ bd-del .. delete birthday """
    global db
    if not db: ievent.reply("plugin isnt initialised yet") ; return
    name = bot.users.getname(ievent.userhost)
    result = 0
    try: result = db.execute(""" DELETE FROM birthday WHERE name = %s """, name)
    except Exception, ex: handle_exception() ; return
    if result: ievent.reply('birthday removed')
    else: ievent.reply('no birthday known for %s' % ievent.nick)

cmnds.add('bd-del', handle_bddel, 'USER')
examples.add('bd-del', 'delete birthday data', 'bd-del')

## bd command

def handle_bd(bot, ievent):
    """ bd [<nr|user>] .. show birthday of month or user """
    global db
    if not db: ievent.reply("plugin isnt initialised yet") ; return
    if not ievent.rest: handle_checkbd(bot, ievent) ; return
    try: int(ievent.args[0]) ; handle_checkbd2(bot, ievent) ; return
    except (IndexError, ValueError):
        try: userhost = who = ievent.args[0].lower()
        except IndexError: userhost = who = ievent.userhost
    if not who: who = userhost = getwho(bot, who)
    if not who: ievent.reply("don't know userhost of %s" % who) ; return
    name = bot.users.getname(userhost)
    if not name: ievent.reply("can't find user for %s" % userhost) ; return
    result = db.execute(""" SELECT birthday FROM birthday WHERE name = %s """, name)
    try: birthday = result[0][0]
    except TypeError: ievent.reply("i don't have birthday data for %s" % who) ; return
    ievent.reply('birthday of %s is %s' % (who, birthday))

cmnds.add('bd', handle_bd, ['USER', 'WEB'])
examples.add('bd', 'bd [<nr|user>] .. show birthdays for this month or show birthday of <nick>', '1) bd 2) bd dunker')

## bd-check command

def handle_checkbd(bot, ievent):
    """ bd-check .. check birthdays for current month """
    global db
    if not db: ievent.reply("plugin isnt initialised yet") ; return
    (nowday, nowmonth) = getdaymonth(time.time())
    mstr = ""
    result = []
    bds = db.execute(""" SELECT * FROM birthday """)
    if not bds: ievent.reply('no birthdays this month') ; return
    for i in bds:
        btime = strtotime(i[1])
        if btime == None: continue
        (day, month) = getdaymonth(btime)
        if month == nowmonth:
            result.append((int(day), i[0], i[1]))
            if day == nowday and month == nowmonth: ievent.reply("it's %s's birthday today!" % i[0])
    result.sort(lambda x, y: cmp(x[0], y[0]))
    for i in result: mstr += "%s: %s " % (i[1], i[2])
    if mstr: mstr = "birthdays this month = " + mstr ; ievent.reply(mstr)
    else: ievent.reply('no birthdays this month')


def handle_checkbd2(bot, ievent):
    """ bd-check <nr> .. show birthdays in month (by number) """
    global db
    if not db: ievent.reply("plugin isnt initialised yet") ; return
    try:
        monthnr = int(ievent.args[0])
        if monthnr < 1 or monthnr > 12: ievent.reply("number must be between 1 and 12") ; return
    except (IndexError, ValueError): ievent.missing('<monthnr>') ; return
    mstr = ""
    result = []
    bds = db.execute(""" SELECT * FROM birthday """)
    if not bds: ievent.reply('no birthdays known') ; return
    for i in bds:
        btime = strtotime(i[1])
        if btime == None: continue
        (day, month) = getdaymonth(btime)
        if month == bdmonths[monthnr]: result.append((int(day), i[0], i[1]))
    result.sort(lambda x, y: cmp(x[0], y[0]))
    for i in result: mstr += "%s: %s " % (i[1], i[2])
    if mstr: mstr = "birthdays in %s = " % bdmonths[monthnr] + mstr ; ievent.reply(mstr)
    else: ievent.reply('no birthdays found for %s' % bdmonths[monthnr])

## age command

def handle_age(bot, ievent):
    """ age <nick> .. show age of user """
    global db
    if not db: ievent.reply("plugin isnt initialised yet") ; return
    try: who = ievent.args[0].lower()
    except IndexError: ievent.missing('<nick>') ; return
    userhost = getwho(bot, who)
    if not userhost: ievent.reply("don't know userhost of %s" % who) ; return
    name = bot.users.getname(userhost)
    if not name: ievent.reply("can't find user for %s" % userhost) ; return
    birthday = db.execute(""" SELECT birthday FROM birthday WHERE name = %s """, name)
    try: birthday = birthday[0][0]
    except TypeError: ievent.reply("can't find birthday data for %s" % who) ; return
    btime = strtotime(birthday)
    if btime == None: ievent.reply("can't make a date out of %s" % birthday) ; return
    age = int(time.time()) - int(btime)
    ievent.reply("age of %s is %s" % (who, elapsedstring(age, ywd=True)))

cmnds.add('age', handle_age, ['USER', 'WEB'])
examples.add('age', 'age <nick> .. show how old <nick> is', 'age dunker')

## plugin initialisation

def init():
    global db
    db = getmaindb()
