# jsb/plugs/db/todo.py
#
#

""" provide todo related commands """

## jsb imports

from jsb.utils.timeutils import strtotime, striptime, today 
from jsb.utils.locking import lockdec
from jsb.utils.generic import getwho
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.users import getusers
from jsb.lib.datadir import datadir
from jsb.lib.persist import Persist
from jsb.lib.aliases import setalias
from jsb.lib.config import getmainconfig
from jsb.lib.plugins import plugs
from jsb.db import getmaindb

## basic imports

import time
import thread
import os
import logging

## locks

todolock = thread.allocate_lock()
locked = lockdec(todolock)

## defines

db = None

## TodoItem class

class TodoItem:

    """ a todo item """

    def __init__(self, name, descr, ttime=None, duration=None, warnsec=None, priority=None, num=0):
        self.name = name
        self.time = ttime
        self.duration = duration
        self.warnsec = warnsec
        self.descr = descr
        self.priority = priority
        self.num = num

## TodoDb class

class TodoDb(object):

    """ database todo interface """

    def reset(self, name): 
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return 0
        result = db.execute(""" DELETE FROM todo WHERE name == %s """, name)
        return result

    def size(self):
        """ return number of todo's """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return 0
        result = db.execute(""" SELECT COUNT(*) FROM todo """)
        return result[0][0]
        
    def get(self, name):
        """ get todo list of <name> """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        name = name.lower()
        result = db.execute(""" SELECT * FROM todo WHERE name = %s ORDER BY priority DESC, indx ASC """, name)
        res = []
        if result:
            for i in result:
                args = [i[1],i[5], i[2], i[3], i[4], i[6], i[0]]
                res.append(TodoItem(*args))
        return res

    def getid(self, idnr):
        """ get todo data of <idnr> """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        result = db.execute(""" SELECT * FROM todo WHERE indx = %s """, idnr)
        res = []
        if result:
            for i in result:
                args = [i[1],i[5], i[2], i[3], i[4], i[6], i[0]]
                res.append(TodoItem(*args))
        return res

    def setprio(self, who, todonr, prio):
        """ set priority of todonr """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return 0
        result = db.execute(""" UPDATE todo SET priority = %s WHERE indx = %s """, (prio, todonr))
        return result

    def getprio(self, who, todonr):
        """ get priority of todonr """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        result = db.execute(""" SELECT name, priority FROM todo WHERE indx = %s """, todonr)
        return result

    def getwarnsec(self, todonr):
        """ get priority of todonr """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        result = db.execute(""" SELECT warnsec FROM todo WHERE indx = %s """, todonr)
        return result

    def settime(self, who, todonr, ttime):
        """ set time of todonr """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return 0
        result = db.execute(""" UPDATE todo SET time = %s WHERE indx = %s """, (ttime, todonr))
        return result

    def add(self, name, txt, ttime, alarmnr=None):
        """ add a todo """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return 0
        name = name.lower()
        txt = txt.strip()
        if ttime:
            if not alarmnr:
                result = db.execute(""" INSERT INTO todo(name, time, descr) VALUES (%s, %s, %s) """, (name, ttime, txt))
            else:
                result = db.execute(""" INSERT INTO todo(name, time, descr, warnsec) VALUES (%s, %s, %s, %s) """, (name, ttime, txt, 0-alarmnr))

        else:
            result = db.execute(""" INSERT INTO todo(name, descr) VALUES (%s, %s) """, (name, txt))
        return result

    def delete(self, name, indexnr):
        """ delete todo item """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return 0
        name = name.lower()
        try:
            warnsec = self.getwarnsec(indexnr)[0][0]
            if warnsec:
                alarmnr = 0 - warnsec
                if alarmnr > 0:
                    alarms = plugs.get("jsb.plugs.common.alarm")
                    if alarms: alarms.alarms.delete(alarmnr)
        except (IndexError, TypeError):
            pass
        result = db.execute(""" DELETE FROM todo WHERE name = %s AND indx = %s """, (name, indexnr))
        return result

    def toolate(self, name):
        """ show if there are any time related todoos that are too late """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        name = name.lower()
        now = time.time()
        result = db.execute(""" SELECT * FROM todo WHERE name = %s AND time < %s """, (name, now))
        res = []
        if result:
            for i in result:
                args = [i[1],i[5], i[2], i[3], i[4], i[6], i[0]]
                res.append(TodoItem(*args))
        return res

    def withintime(self, name, time1, time2):
        """ show todo list within time frame """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        name = name.lower()
        result = db.execute(""" SELECT * FROM todo WHERE name = %s AND time > %s AND time < %s """, (name, time1, time2))
        res = []
        if result:
            for i in result:
                args = [i[1],i[5], i[2], i[3], i[4], i[6], i[0]]
                res.append(TodoItem(*args))
        return res

    def timetodo(self, name):
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return []
        name = name.lower()
        now = time.time()
        result = db.execute(""" SELECT * FROM todo WHERE time AND name = %s """, name)
        res = []
        if result:
            for i in result:
                args = [i[1],i[5], i[2], i[3], i[4], i[6], i[0]]
                res.append(TodoItem(*args))
        return res

    def reset(self, name):
        """ reset todo items of user with <name> """
        global db
        if not db: logging.error("plugin isnt initialised yet") ; return 0
        name = name.lower()
        result = db.execute(""" DELETE FROM todo WHERE name = %s """, (name, ))
        return result

## defines

todo = TodoDb()

def size():
    """ return number of todo entries """
    return todo.size()

## plugin init

def init():
    global db
    if not db: db = getmaindb()
    setalias('d', 't-done')
    setalias('tt', 't-time')

# t command

def handle_todo(bot, ievent):
    """ todo [<item>] .. show todo's or set todo item .. a time/date can be given. """
    if len(ievent.args) > 0: handle_todo2(bot, ievent) ; return
    name = getusers().getname(ievent.userhost)
    try: todoos = todo.get(name)
    except KeyError: ievent.reply('i dont have todo info for %s' % user.name) ; return
    saytodo(bot, ievent, todoos)

def handle_todo2(bot, ievent):
    """ set todo item """
    if not ievent.rest: ievent.missing("<what>") ; return
    else: what = ievent.rest
    name = getusers().getname(ievent.userhost)
    ttime = strtotime(what)
    nr = 0
    if not ttime  == None:
        ievent.reply('time detected ' + time.ctime(ttime))
        what = striptime(what)
        alarms = plugs.get("jsb.plugs.common.alarm")
        if alarms : alarmnr = alarms.alarms.add(bot.name, ievent.nick, ttime, what)
        else: alarmnr = None
        nr = todo.add(name, what, ttime, alarmnr)
    else: nr = todo.add(name, what, None)
    ievent.reply('todo item %s added' % nr)

cmnds.add('t', handle_todo, 'USER')
examples.add('t', 'todo [<item>] .. show todo items or add a todo item', '1) todo 2) todo program the bot 3) todo 22:00 sleep')

## t-done command

def handle_tododone(bot, ievent):
    """ t-done <listofnrs> .. remove todo items """
    if len(ievent.args) == 0: ievent.missing('<list of nrs>') ; return
    try:
        nrs = []
        for i in ievent.args: nrs.append(int(i))
    except ValueError: ievent.reply('%s is not an integer' % i) ; return
    name = getusers().getname(ievent.userhost)
    nrdone = 0
    for i in nrs: nrdone += todo.delete(name, i)
    if nrdone == 1: ievent.reply('%s item deleted' % nrdone)
    elif nrdone == 0: ievent.reply('no items deleted')
    else: ievent.reply('%s items deleted' % nrdone)

cmnds.add('t-done', handle_tododone, 'USER')
examples.add('t-done', 'remove items from todo list', '1) t-done 1 2) t-done 3 5 8')

## t-chan command

def handle_chantodo(bot, ievent):
    """ t-chan [<item>] .. show channel todo's or set todo item for channel"""
    if ievent.rest: handle_chantodo2(bot, ievent) ; return
    todoos = todo.get(ievent.channel)
    saytodo(bot, ievent, todoos, chan=True)

def handle_chantodo2(bot, ievent):
    """ set todo item for channel"""
    what = ievent.rest
    ttime = strtotime(what)
    nr = 0
    if not ttime  == None:
        ievent.reply('time detected ' + time.ctime(ttime))
        result = '(%s) ' % ievent.nick + striptime(what)
        alarms = plugs.get("jsb.plugs.common.alarm")
        if alarms : alarmnr = alarms.add(bot.name, ievent.channel, ttime, result)
        else: alarmnr = None
        nr = todo.add(ievent.channel, result, ttime, alarmnr)
    else:
        result = '(%s) ' % ievent.nick + what
        nr = todo.add(ievent.channel, result, None)
    ievent.reply('todo item %s added' % nr)

cmnds.add('t-chan', handle_chantodo, 'USER')
examples.add('t-chan', 't-chan [<item>] .. add channel todo', 't-chan fix bla')

## t-chandone command

def handle_todochandone(bot, ievent):
    """ t-chandone <listofnrs> .. remove channel todo item """
    if not ievent.rest: ievent.missing('<list of nrs>') ; return
    data = ievent.rest.split()
    try:
        nrs = []
        for i in data: nrs.append(int(i))
    except ValueError: ievent.reply('%s is not an integer' % i) ; return
    nrdone = 0
    for i in nrs: nrdone += todo.delete(ievent.channel, i)
    if nrdone == 1: ievent.reply('%s item deleted' % nrdone)
    elif nrdone == 0: ievent.reply('no items deleted')
    else: ievent.reply('%s items deleted' % nrdone)

cmnds.add('t-chandone', handle_todochandone, 'USER')
examples.add('t-chandone', 't-chandone <listofnrs> .. remove item from channel todo list', 't-chandone 2')

## t-set command

def handle_settodo(bot, ievent):
    """ t-set <name> <txt> .. add a todo to another user's todo list"""
    try:
        who = ievent.args[0]
        what = ' '.join(ievent.args[1:])
    except IndexError: ievent.missing('<nick> <what>') ;return
    if not what: ievent.missing('<nick> <what>') ; return
    userhost = getwho(bot, who)
    if not userhost: ievent.reply("can't find userhost for %s" % who) ; return
    whouser = getusers().getname(userhost)
    if not whouser: ievent.reply("can't find user for %s" % userhost) ; return
    name = getusers().getname(ievent.userhost)
    if not getusers().permitted(userhost, name, 'todo'): ievent.reply("%s doesn't permit todo sharing for %s " % (who, name)) ; return
    what = "%s: %s" % (ievent.nick, what)
    ttime = strtotime(what)
    nr = 0
    if not ttime  == None:
        ievent.reply('time detected ' + time.ctime(ttime))
        what = striptime(what)
        karma = plugs.get("jsb.plugs.db.karma2")
        if karma: alarmnr = alarms.add(bot.name, who, ttime, what)
        else: alarmnr = None
        nr = todo.add(whouser, what, ttime, alarmnr)
    else: nr = todo.add(whouser, what, None)
    ievent.reply('todo item %s added' % nr)

cmnds.add('t-set', handle_settodo, 'USER')
examples.add('t-set', 'set todo item of <nick>', 't-set dunker bot proggen')

## t-get command

def handle_gettodo(bot, ievent):
    """ t-get <nick> .. get todo of another user """
    try: who = ievent.args[0]
    except IndexError: ievent.missing('<nick>') ; return
    userhost = getwho(bot, who)
    if not userhost: ievent.reply("can't find userhost for %s" % who) ; return
    users = getusers()
    whouser = users.getname(userhost)
    if not whouser: ievent.reply("can't find user for %s" % userhost) ; return
    name = users.getname(ievent.userhost)
    if not users.permitted(userhost, name, 'todo'): ievent.reply("%s doesn't permit todo sharing for %s " % (who, name)) ; return
    todoos = todo.get(whouser)
    saytodo(bot, ievent, todoos)

cmnds.add('t-get', handle_gettodo, ['USER', 'WEB'])
examples.add('t-get', 't-get <nick> .. get the todo list of <nick>', 't-get dunker')

## t-time command

def handle_todotime(bot, ievent):
    """ t-time .. show time related todoos """
    name = getusers().getname(ievent.userhost)
    todoos = todo.timetodo(name)
    saytodo(bot, ievent, todoos)

cmnds.add('t-time', handle_todotime, 'USER')
examples.add('t-time', 'todo-time .. show todo items with time fields', 't-time')

## t-week command

def handle_todoweek(bot, ievent):
    """ todo-week .. show time related todo items for this week """
    name = getusers().getname(ievent.userhost)
    todoos = todo.withintime(name, today(), today()+7*24*60*60)
    saytodo(bot, ievent, todoos)

cmnds.add('t-week', handle_todoweek, 'USER')
examples.add('t-week', 't-week .. todo items for this week', 't-week')

## t-today command

def handle_today(bot, ievent):
    """ t-today .. show time related todo items for today """
    name = getusers().getname(ievent.userhost)
    todoos = todo.withintime(name, today(), today()+24*60*60)
    saytodo(bot, ievent, todoos)

cmnds.add('t-today', handle_today, 'USER')
examples.add('t-today', 'todo-today .. todo items for today', 't-today')

## t-tomorrow command

def handle_tomorrow(bot, ievent):
    """ t-tomorrow .. show time related todo items for tomorrow """
    username = getusers().getname(ievent.userhost)
    if ievent.rest:
        what = ievent.rest
        ttime = strtotime(what)
        if ttime != None:
            if ttime < today() or ttime > today() + 24*60*60:
                ievent.reply("%s is not tomorrow" % time.ctime(ttime + 24*60*60))
                return
            ttime += 24*60*60
            ievent.reply('time detected ' + time.ctime(ttime))
            what = striptime(what)
        else: ttime = today() + 42*60*60
        todo.add(username, what, ttime)   
        ievent.reply('todo added')    
        return
    todoos = todo.withintime(username, today()+24*60*60, today()+2*24*60*60)
    saytodo(bot, ievent, todoos)

cmnds.add('t-tomorrow', handle_tomorrow, 'USER')
examples.add('t-tomorrow', 't-tomorrow .. todo items for tomorrow', 't-tomorrow')

## t-setprio command

def handle_setpriority(bot, ievent):
    """ t-setprio [<channel|name>] <itemnr> <prio> .. show priority on todo item """
    try: (who, itemnr, prio) = ievent.args
    except ValueError:
        try:
            (itemnr, prio) = ievent.args
            who = getusers().getname(ievent.userhost)
        except ValueError: ievent.missing('[<channe|namel>] <itemnr> <priority>') ; return
    try:
        itemnr = int(itemnr)
        prio = int(prio)
    except ValueError: ievent.missing('[<channel|name>] <itemnr> <priority>') ; return
    who = who.lower()
    if not todo.setprio(who, itemnr, prio): ievent.reply('no todo %s found for %s' % (itemnr, who)) ; return
    ievent.reply('priority set')

cmnds.add('t-setprio', handle_setpriority, 'USER')
examples.add('t-setprio', 'todo-setprio [<channel|name>] <itemnr> <prio> .. set todo priority', '1) todo-setprio #dunkbots 2 5 2) todo-setprio owner 3 10 3) todo-setprio 2 10')

## t-settime command

def handle_todosettime(bot, ievent):
    """ todo-settime [<channel|name>] <itemnr> <timestring> .. set time \
        on todo item """
    ttime = strtotime(ievent.txt)
    if ttime == None: ievent.reply("can't detect time") ; return   
    txt = striptime(ievent.txt)
    try: (who, itemnr) = txt.split()
    except ValueError:
        try:
            (itemnr, ) = txt.split()
            who = getusers().getname(ievent.userhost)
        except ValueError: ievent.missing('[<channe|namel>] <itemnr> <timestring>') ; return
    try: itemnr = int(itemnr)
    except ValueError: ievent.missing('[<channel|name>] <itemnr> <timestring>') ; return
    who = who.lower()
    if not todo.settime(who, itemnr, ttime): ievent.reply('no todo %s found for %s' % (itemnr, who)) ; return
    ievent.reply('time of todo %s set to %s' % (itemnr, time.ctime(ttime)))

cmnds.add('t-settime', handle_todosettime, 'USER')
examples.add('t-settime', 't-settime [<channel|name>] <itemnr> <timestring> .. set todo time', '1) todo-settime #dunkbots 2 13:00 2) todo-settime owner 3 2-2-2010 3) todo-settime 2 22:00')

## t-getprio command

def handle_getpriority(bot, ievent):
    """ todo-getprio <[channel|name]> <itemnr> .. get priority of todo item """
    try: (who, itemnr) = ievent.args
    except ValueError:
        try:
            itemnr = ievent.args[0]
            who = getusers().getname(ievent.userhost)
        except IndexError: ievent.missing('[<channel|name>] <itemnr>') ; return
    try: itemnr = int(itemnr)
    except ValueError: ievent.missing('[<channel|name>] <itemnr>') ; return
    who = who.lower()
    todoitems = todo.get(who)
    if not todoitems: ievent.reply('no todoitems known for %s' % who) ; return
    try: prio = todoitems[itemnr].priority
    except (IndexError, KeyError): ievent.reply('no todo item %s known for %s' % (itemnr, who)) ; return
    ievent.reply('priority is %s' % prio)

cmnds.add('t-getprio', handle_getpriority, 'USER')
examples.add('t-getprio', 'todo-getprio [<channel|name>] <itemnr> .. get todo priority', '1) todo-getprio #dunkbots 5 2) todo-getprio 3')

def saytodo(bot, ievent, todoos, chan=False):
    """ output todo items of <name> """
    result = []
    now = time.time()
    if not todoos: ievent.reply('nothing todo ;]') ; return
    for i in todoos:
        res = ""
        res += "%s) " % i.num
        if i.time:
            if i.time < now: res += 'TOO LATE: '
            if i.time: res += "%s %s " % (time.ctime(strtotime(i.time)), i.descr)
        else: res += "%s " % i.descr
        if i.priority: res += "[%+d] " % i.priority
        result.append(res.strip())
    if not chan: ievent.reply("todolist of %s: " % ievent.nick, result, nritems=True)
    if chan: ievent.reply("todolist of %s: " % ievent.channel, result, nritems=True)
