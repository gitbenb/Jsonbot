# jsb/plugs/common/learn.py
#
#

""" learn information items .. facts .. factoids. """

## jsb imports

from jsb.lib.callbacks import callbacks
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.utils.lazydict import LazyDict
from jsb.lib.persist import PlugPersist, GlobalPersist

## basic imports

import logging

## learn command

def handle_learn(bot, event):
    """" arguments: <item> is <description> - set an information item. """
    if not event.rest: event.missing("<item> is <description>") ; return
    try: (what, description) = event.rest.split(" is ", 1)
    except ValueError: event.missing("<item> is <description>") ; return
    what = what.lower()
    items = GlobalPersist("learndb")
    if not items.data: items.data = LazyDict()
    if not items.data.has_key(what): items.data[what] = []
    if description not in items.data[what]: items.data[what].append(description)
    items.save()
    event.reply("%s item added to global database" % what)

cmnds.add('learn', handle_learn, ['OPER', 'USER', 'GUEST'])
examples.add('learn', 'learn the bot a description of an item.', "learn dunk is botpapa")

## learn-chan command

def handle_learnchan(bot, event):
    """" arguments: <item> is <description> - set an information item. """
    if not event.rest: event.missing("<item> is <description>") ; return
    try: (what, description) = event.rest.split(" is ", 1)
    except ValueError: event.missing("<item> is <description>") ; return
    what = what.lower()
    items = PlugPersist(event.channel)
    if not items.data: items.data = LazyDict()
    if not items.data.has_key(what): items.data[what] = []
    if description not in items.data[what]: items.data[what].append(description)
    items.save()
    event.reply("%s item added to %s database" % (what, event.channel))

cmnds.add('learn-chan', handle_learnchan, ['OPER', 'USER', 'GUEST'])
examples.add('learn-chan', 'learn the bot a description of an item. (channel specific)', "learn-chan dunk is botpapa")

## forget command

def handle_forget(bot, event):
    """" arguments: <item> and <matchstring> - set an information item. """
    if not event.rest: event.missing("<item> and <match>") ; return
    try: (what, match) = event.rest.split(" and ", 2)
    except ValueError: what = event.rest ; match = None
    what = what.lower()
    items = GlobalPersist("learndb")
    got = False
    if not items.data: items.data = LazyDict()
    if items.data.has_key(what):
        if match == None: del items.data[what] ; got = True
        else:
            for i in range(len(items.data[what])):
                if match in items.data[what][i]:
                    del items.data[what][i]                
                    got = True
                    break
    if got: items.save() ; event.reply("item removed from global database")
    else: event.reply("no %s item in global database" % what)

cmnds.add('forget', handle_forget, ['OPER', 'USER'])
examples.add('forget', 'forget a description of an item.', "forget dunk and botpapa")

## forget-chan command

def handle_forgetchan(bot, event):
    """" arguments: <item> and <matchstring> - set an information item. """
    if not event.rest: event.missing("<item> and <match>") ; return
    try: (what, match) = event.rest.split(" and ", 2)
    except ValueError: what = event.rest ; match = None
    what = what.lower()
    items = PlugPersist(event.channel)
    got = False
    if not items.data: items.data = LazyDict()
    if items.data.has_key(what):
        if match == None: del items.data[what] ; got = True
        else:
            for i in range(len(items.data[what])):
                if match in items.data[what][i]:
                    del items.data[what][i]                
                    got = True
                    break
    if got: items.save() ; event.reply("item removed from %s database" % event.channel)
    else: event.reply("no %s item in channel database" % what)

cmnds.add('forget-chan', handle_forgetchan, ['OPER', 'USER'])
examples.add('forget-chan', 'forget a description of an item. (channel specific)', "forget-chan dunk and botpapa")

## whatis command

def handle_whatis(bot, event):
    """ arguments: <item> - show what the bot has learned about a factoid. """
    if not event.rest: event.missing("<what>") ; return
    items = PlugPersist(event.channel)
    what = event.rest.lower().split('!')[0].strip()
    result = []
    if what in items.data and items.data[what]: result = items.data[what]
    globalitems = GlobalPersist("learndb")
    if what in globalitems.data and globalitems.data[what]: result.extend(globalitems.data[what])
    if result: event.reply("%s is " % event.rest, result, dot=", ")
    else: event.reply("no information known about %s" % what)

cmnds.add('whatis', handle_whatis, ['OPER', 'USER', 'GUEST'])
examples.add("whatis", "whatis learned about a subject", "whatis jsb")

## items command

def handle_items(bot, event):
    """ no arguments - show what items the bot has learned. """
    items = PlugPersist(event.channel).data.keys()
    globalitems = GlobalPersist("learndb").data.keys()
    result = items + globalitems
    event.reply("i know %s items: " % len(result), result)

cmnds.add('items', handle_items, ['OPER', 'USER', 'GUEST'])
examples.add("items", "show what items the bot knows", "items")

# searchitems command

def handle_searchitems(bot, event):
    """ argument: <searchtxt>  - search the items the bot has learned. """
    if not event.rest: event.missing("<searchtxt>") ; return
    items = PlugPersist(event.channel).data.keys()
    globalitems = GlobalPersist("learndb").data.keys()
    got = []
    for i in items + globalitems:
        if event.rest in i: got.append(i)
    event.reply("found %s items: " % len(got), got)

cmnds.add('searchitems', handle_searchitems, ['OPER', 'USER', 'GUEST'])
examples.add("searchitems", "search the items the bot knows", "searchitems jsonbot")

## learn-toglobal command

def handle_learntoglobal(bot, event):
    """ argument: <searchtxt>  - search the items the bot has learned. """
    items = PlugPersist(event.channel)
    globalitems = GlobalPersist("learndb")
    for i in items.data.keys():
        if not globalitems.data.has_key(i): globalitems.data[i] = []
        globalitems.data[i].extend(items.data)
    globalitems.save()
    event.reply("%s items copy to the global database. " % len(items.data))

cmnds.add('learn-toglobal', handle_learntoglobal, ['OPER', ])
examples.add("learn-toglobal", "move channel specific learn data to the global database.", "learn-toglobal")

## callbacks

def prelearn(bot, event):
    """ learn precondition. """
    if event.iscommand: return False
    if len(event.txt) < 2: return False
    if event.txt and (event.txt[0] == "?" or event.txt[-1] == "?") and not event.forwarded: return True
    return False

def learncb(bot, event):
    """ learn callback, is for catching ? queries. """
    event.bind(bot)
    result = []
    items = PlugPersist(event.channel)
    target = event.txt.lower()
    if target[0] == "?": target = target[1:]
    if target[-1] == "?": target = target[:-1]
    if target in items.data: result = items.data[target]
    globalitems = GlobalPersist("learndb")
    if target in globalitems.data:
        if not target in result: result.extend(globalitems.data[target])    
    if result: event.reply("%s is " % target, result, dot=", ")
    event.ready()

callbacks.add("PRIVMSG", learncb, prelearn)
callbacks.add("MESSAGE", learncb, prelearn)
callbacks.add("DISPATCH", learncb, prelearn)
callbacks.add("CONSOLE", learncb, prelearn)
callbacks.add("CMND", learncb, prelearn)
callbacks.add("TORNADO", learncb, prelearn)
