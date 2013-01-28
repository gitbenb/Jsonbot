# jsb/plugs/core.admin.py
#
#

""" admin related commands. these commands are mainly for maintaining the bot. """

## jsb imports

from jsb.lib.eventhandler import mainhandler
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.persist import Persist
from jsb.lib.boot import savecmndtable, savepluginlist, boot, plugin_packages, clear_tables, getcmndtable, getcallbacktable
from jsb.lib.plugins import plugs
from jsb.lib.botbase import BotBase
from jsb.lib.exit import globalshutdown
from jsb.lib.config import getmainconfig
from jsb.utils.generic import stringsed, getwho
from jsb.utils.exception import handle_exception
from jsb.lib.aliases import setalias
from jsb.lib.fleet import getfleet
from jsb.lib.plugins import plugs
from jsb.lib.datadir import getdatadir
from jsb.utils.log import setlogplug, dellogplug, setlogfilter, dellogfilter

## basic imports

import logging

## admin-logwatch command

def handle_adminlogplug(bot, event):
    """ enable logging of plugin on WARN level. """
    if not event.rest: event.missing("<plugname>") ; return
    if len(event.rest) < 3: event.reply("min 3 chars plz") ; return
    setlogplug(event.rest)
    event.done()
    
cmnds.add("admin-logplug", handle_adminlogplug, "OPER")
examples.add("admin-logplug", "enable logging of plugin on WARN level", "admin-logplug rss")

## admin-dellogwatch command

def handle_admindellogplug(bot, event):
    """ remove plug from logging list. """
    if not event.rest: event.missing("<plugname>") ; return
    dellogplug(event.rest)
    event.done()

cmnds.add("admin-dellogplug", handle_admindellogplug, "OPER")
examples.add("admin-dellogplug", "remove logging of plugin on WARN level", "admin-dellogwatch rss")

## admin-logfilter command

def handle_adminlogfilter(bot, event):
    """ set txt to be filtered from logs """
    if not event.rest: event.missing("<plugname>") ; return
    if len(event.rest) < 3: event.reply("min 3 chars plz") ; return
    setlogfilter(event.rest)
    event.done()

cmnds.add("admin-logfilter", handle_adminlogfilter, "OPER")
examples.add("admin-logfilter", "enable filtering of log message containing provided string", "admin-logfilter cleanup")

## admin-dellogwatch command

def handle_admindellogfilter(bot, event):
    """ remove txt from logfilter. """
    if not event.rest: event.missing("<plugname>") ; return
    dellogfilter(event.rest)
    event.done()

cmnds.add("admin-dellogfilter", handle_admindellogfilter, "OPER")
examples.add("admin-dellogfilter", "remove logging filter", "admin-dellogfilter cleanup")

## admin-listlog command

def handle_adminlistlog(bot, event):
    """ lists log filters. """
    from jsb.utils.log import logplugs, logfilter
    event.reply("plugs: %s filter: %s" % (str(logplugs), str(logfilter)))

cmnds.add("admin-listlog", handle_adminlistlog, "OPER")
examples.add("admin-listlog", "list the log filters", "admin-listlog")

## admin-datadir command

def handle_admindatadir(bot, event):
    event.reply("datadir is %s" % getdatadir())

cmnds.add("admin-datadir", handle_admindatadir, "OPER")
examples.add("admin-datadir", "show datadir used in the bot", "admin-datadir")

## admin-save command

def handle_adminsave(bot, ievent):
    """ no arguments - boot the bot ..  do some initialisation.  """
    ievent.reply("saving mainconfig")
    getmainconfig().save()
    ievent.reply("saving fleet bots")
    getfleet().save()
    ievent.reply("saving all plugins")
    plugs.save()
    ievent.done()

cmnds.add('admin-save', handle_adminsave, 'OPER')
examples.add('admin-save', 'initialize the bot', 'admin-boot')

## admin-boot command

def handle_adminboot(bot, ievent):
    """ no arguments - boot the bot .. do some initialisation. """
    ievent.reply("reloading all plugins")
    if 'saveperms' in ievent.rest: boot(force=True, saveperms=True, clear=True)
    else: boot(force=True, saveperms=False, clear=True)
    ievent.done()

cmnds.add('admin-boot', handle_adminboot, 'OPER')
examples.add('admin-boot', 'initialize the bot', 'admin-boot')

## admin-bootthreaded command

def handle_adminbootthreaded(bot, ievent):
    """ no arguments - boot the bot .. do some initialisation. """
    ievent.untildone = True
    ievent.reply("reloading all plugins")
    if 'saveperms' in ievent.rest: boot(force=True, saveperms=True, clear=True)
    else: boot(force=True, saveperms=False, clear=True)
    ievent.done()

cmnds.add('admin-bootthreaded', handle_adminbootthreaded, 'OPER', threaded=True)
examples.add('admin-bootthreaded', 'initialize the bot in a seperate thread', 'admin-bootthreaded')

## admin-commands command

def handle_admincommands(bot, ievent):
    """ no arguments - load all available plugins. """
    cmnds = getcmndtable()
    if not ievent.rest: ievent.reply("commands: ", cmnds)
    else:
        try: ievent.reply("%s command is found in %s " % (ievent.rest, cmnds[ievent.rest]))
        except KeyError: ievent.reply("no such commands available") 

cmnds.add('admin-commands', handle_admincommands, 'OPER')
examples.add('admin-commands', 'show runtime command table', 'admin-commands')

## admin-callbacks command

def handle_admincallbacks(bot, ievent):
    """ no arguments - load all available plugins. """
    cbs = getcallbacktable()
    if not ievent.rest: ievent.reply("callbacks: ", cbs)
    else:
        try: ievent.reply("%s callbacks: " % ievent.rest, cbs[ievent.rest])
        except KeyError: ievent.reply("no such callbacks available") 

cmnds.add('admin-callbacks', handle_admincallbacks, 'OPER')
examples.add('admin-callbacks', 'show runtime callback table', 'admin-callbacks')

## admin-userhostcache command

def handle_userhostscache(bot, ievent):
    """ no arguments - show userhostscache of the bot the command is given on. """
    ievent.reply("userhostcache of %s: " % ievent.channel, bot.userhosts)

cmnds.add('admin-userhostscache', handle_userhostscache, 'OPER')
examples.add('admin-userhostscache', 'show userhostscache ', 'admin-userhostscache')

## admin-loadall command

def handle_loadall(bot, ievent):
    """ no arguments - load all available plugins. """
    plugs.loadall(plugin_packages, force=True)
    ievent.done()

cmnds.add('admin-loadall', handle_loadall, 'OPER', threaded=True)
examples.add('admin-loadall', 'load all plugins', 'admin-loadall')

## admin-makebot command

def handle_adminmakebot(bot, ievent):
    """ arguments: <botname> <bottype> - create a bot of given type. """
    try: botname, bottype = ievent.args
    except ValueError: ievent.missing("<name> <type>") ; return
    newbot = BotBase()
    newbot.botname = botname
    newbot.type = bottype
    newbot.owner = bot.owner
    newbot.save()
    ievent.done()

cmnds.add('admin-makebot', handle_adminmakebot, 'OPER')
examples.add('admin-makebot', 'create a bot', 'admin-makebot cmndxmpp xmpp')

## admin-stop command

def handle_adminstop(bot, ievent):
    """ no arguments - stop the bot. """
    ievent.untildone = True
    if bot.ownercheck(ievent.userhost): mainhandler.put(0, globalshutdown)
    else: ievent.reply("you are not the owner of the bot") ; return
    ievent.done(silent=True)
    
cmnds.add("admin-stop", handle_adminstop, "OPER")
examples.add("admin-stop", "stop the bot.", "stop")
setalias("qq", "admin-stop")

## admin-setstatus command

def handle_adminsetstatus(bot, event):
    """ arguments: <status> [<statustxt>] - set the status of the bot (xmpp). """
    if bot.type != "sxmpp": event.reply("this command only works on sxmpp bots (for now)") ; return
    if not event.rest: event.missing("<status> [<show>]") ; return
    status = event.args[0]
    try: show = event.args[1]
    except IndexError: show = ""
    bot.setstatus(status, show)

cmnds.add("admin-setstatus", handle_adminsetstatus, ["STATUS", "OPER"])
examples.add("admin-setstatus", "set status of sxmpp bot", "admin-setstatus available Yooo dudes !")

## admin-reloadconfig command

def handle_adminreloadconfig(bot, event):
    """ no arguments - reload bot config and mainconfig files. """
    try:
        bot.cfg.reload()
        getmainconfig().reload()
    except Exception, ex: handle_exception()
    event.done()

cmnds.add("admin-reloadconfig", handle_adminreloadconfig, ["OPER"])
examples.add("admin-reloadconfig", "reload mainconfig", "admin-reloadconfig")

## admin-exceptions command

def handle_adminexceptions(bot, event):
    """ no arguments - show exceptions raised in the bot. """
    from jsb.utils.exception import exceptionlist, exceptionevents
    for e, ex in exceptionevents: logging.warn("%s - exceptions raised is %s" % (e.bot.cfg.name, ex))
    event.reply("exceptions raised: ", exceptionlist)

cmnds.add("admin-exceptions", handle_adminexceptions, ["OPER"])
examples.add("admin-exceptions", "show exceptions raised", "admin-exceptions")

## admin-debugon

def handle_admindebugon(bot, event):
    """ no arguments - enable debug on a channel. """
    event.chan.data.debug = True;
    event.chan.save()
    event.reply("debugging is enabled for %s" % event.channel)

cmnds.add("admin-debugon", handle_admindebugon, ['OPER', ])
examples.add("admin-debugon", "enable debug on a channel.", "admin-debugon")

## admin-debugoff

def handle_admindebugoff(bot, event):
    """ no arguments - disable debug on a channel. """
    event.chan.data.debug = False;
    event.chan.save()
    event.reply("debugging is disabled for %s" % event.channel)

cmnds.add("admin-debugoff", handle_admindebugoff, ['OPER', ])
examples.add("admin-debugoff", "disable debug on a channel.", "admin-debugoff")

## admin-mc command

def handle_adminmc(bot, event):
    """ flush memcached. """
    if event.rest == "stats":
        try:
            from jsb.memcached import mc
            if not mc: event.reply("memcached is not enabled") ; return
            test = mc.get_stats()
            if not test: event.reply("no memcached found")
            else: event.reply("memcached stats: ", test[0][1])
        except Exception, ex:
            event.reply("memcached error: %s" % str(ex))
    elif event.rest == "flushall":
        try:
            from jsb.memcached import mc
            if not mc: event.reply("memcached is not enabled") ; return
            if mc: test = mc.flush_all() ; event.done()
            else: event.reply("no memcached running")
        except Exception, ex:
            event.reply("memcached error: %s" % str(ex))
    else: event.reply("choose one of stats, flushall")

cmnds.add("admin-mc", handle_adminmc, "OPER")
examples.add("admin-mc", "bots interdace to memcached", "1) admin-mc stats 2) admin-mc flushall")

## admin-floodcontrol command

def handle_adminfloodcontrol(bot, event):
    """ no arguments - disable debug on a channel. """
    try:
        who, threshold = event.args
        threshold = int(threshold) 
    except ValueError: event.missing("<userhost> <threshold> [period] [wait]") ; return
    userhost = getwho(bot, who)
    if userhost: user = bot.users.getuser(userhost)
    else: user = bot.users.byname(who)
    if not user: event.reply("i don't know a user %s" % who) ; return
    if "OPER" in user.data.perms: event.reply("no flood control for OPER") ; return
    try: period = event.args[2]
    except IndexError: period = 60
    try: wait = event.args[3]
    except IndexError: wait = 120
    if threshold < 1: threshold = 1
    user.data.floodtime = period
    user.data.floodthreshold = threshold
    user.data.floodwait = wait
    user.data.floodrate = 1
    user.save()
    from jsb.lib.floodcontrol import floodcontrol
    for u in user.data.userhosts: floodcontrol.reset(u)
    event.reply("floodrate for %s set to %s" % (user.data.name, threshold))

cmnds.add("admin-floodcontrol", handle_adminfloodcontrol, ['OPER', ])
examples.add("admin-floodcontrol", "set the floodcontrol parameters of a user", "1) admin-floodcontrol dunker 20 2) admin-floodcontrol dunker 20 300 500")

#### BHJTW 6-03-2012