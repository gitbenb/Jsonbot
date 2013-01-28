# jsb/plugs/core/core.py
#
#

""" core bot commands. """

## jsb imports

from jsb.lib.aliases import setalias
from jsb.lib.config import getmainconfig
from jsb.utils.statdict import StatDict
from jsb.utils.log import setloglevel, getloglevel
from jsb.utils.timeutils import elapsedstring
from jsb.utils.exception import handle_exception
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.plugins import plugs
from jsb.lib.boot import plugin_packages, getpluginlist, boot, getcmndtable, whatcommands, getshorttable
from jsb.lib.persist import Persist
from jsb.lib.reboot import reboot, reboot_stateful
from jsb.lib.eventhandler import mainhandler
from jsb.lib.fleet import getfleet
from jsb.lib.partyline import partyline
from jsb.lib.exit import globalshutdown
from jsb.lib.runner import defaultrunner, cmndrunner, longrunner, apirunner, threadrunner
from jsb.lib.errors import NoSuchPlugin
from jsb.utils.statdict import StatDict
from jsb.contrib.natural import date
from jsb.lib.threadloop import threadloops
from jsb.lib.threads import getname

## basic imports

import time
import threading
import sys
import re
import os
import copy
import cgi
import logging
import functools

## defines

cpy = copy.deepcopy

## reboot command

def handle_reboot(bot, ievent):
    """ no arguments - reboot the bot. """
    ievent.reply("rebooting")
    #time.sleep(3)
    if ievent.rest == "cold": stateful = False
    else: stateful = True
    if stateful:
        if bot.type == "tornado": 
            callback = functools.partial(reboot_stateful, bot, ievent, getfleet(), partyline)
            bot.server.io_loop.add_callback(callback)
        else: mainhandler.put(0, reboot_stateful, bot, ievent, getfleet(), partyline)
    else:
        getfleet().exit()
        mainhandler.put(0, reboot)

cmnds.add("reboot", handle_reboot, "OPER")
examples.add("reboot", "reboot the bot.", "reboot")

## ping command

def handle_ping(bot, event):
    event.reply("pong")

cmnds.add("ping", handle_ping, ["OPER", "USER"])
examples.add("ping", "ping/pong", "ping")

## quit command

def handle_quit(bot, ievent):
    """ no arguments - disconnect from the server. """
    ievent.reply("quiting")
    bot.exit()

cmnds.add("quit", handle_quit, "OPER")
examples.add("quit", "quit the bot.", "quit")

## encoding command

def handle_encoding(bot, ievent):
    """ not arguments - show default encoding. """
    ievent.reply('default encoding is %s' % bot.encoding or sys.getdefaultencoding())

cmnds.add('encoding', handle_encoding, ['USER', 'GUEST'])
examples.add('encoding', 'show default encoding', 'encoding')

## uptime command

def handle_uptime(bot, ievent):
    """ no arguments - show uptime. """
    ievent.reply("<b>uptime is %s</b>" % elapsedstring(time.time()-bot.starttime))

cmnds.add('uptime', handle_uptime, ['USER', 'GUEST'])
examples.add('uptime', 'show uptime of the bot', 'uptime')

## list command

def handle_available(bot, ievent):
    """ no arguments - show available plugins .. to enable use !plug-enable. """
    if ievent.rest: ievent.reply("%s plugin has the following commands: " % ievent.rest, whatcommands(ievent.rest))
    else: ievent.reply("available plugins: ", getpluginlist(), raw=True) ; return

cmnds.add('list', handle_available, ['USER', 'GUEST'])
examples.add('list', 'list available plugins', 'list')

## commands command

def handle_commands(bot, ievent):
    """ arguments: [<plugname>] - show commands of plugin. """
    try: plugin = ievent.args[0].lower()
    except IndexError: plugin = ""
    result = []
    cmnds = getcmndtable()
    for cmnd, plugname in cmnds.iteritems(): 
        if plugname:
            if not plugin or plugin in plugname: result.append(cmnd)
    if result:
        result.sort()
        if not plugin: plugin = "JSONBOT"
        ievent.reply('%s has the following commands: ' % plugin, result)
    else: ievent.reply('no commands found for plugin %s' % plugin)

cmnds.add('commands', handle_commands, ['USER', 'GUEST'])
examples.add('commands', 'show commands of <plugin>', '1) commands core')

## perm command

def handle_perm(bot, ievent):
    """ arguments: <cmnd> - get permission of command. """
    try:cmnd = ievent.args[0]
    except IndexError:
        ievent.missing("<cmnd>")
        return
    try: perms = cmnds.perms(cmnd)
    except KeyError:
        ievent.reply("no %sw command registered")
        return
    if perms: ievent.reply("%s command needs %s permission" % (cmnd, perms))
    else: ievent.reply("can't find perm for %s" % cmnd)

cmnds.add('perm', handle_perm, ['USER', 'GUEST'])
examples.add('perm', 'show permission of command', 'perm quit')

## version command

def handle_version(bot, ievent):
    """ no arguments - show bot's version. """
    from jsb.version import getversion
    version = getversion(bot.type.upper())
    cfg = getmainconfig()
    if cfg.dbenable: version += " " + cfg.dbtype.upper()
    if ievent.rest and ievent.rest == "repo":
        try: 
            from mercurial import context, hg, node, repo, ui
            repository = hg.repository(ui.ui(), '.')
            ctx = context.changectx(repository)
            tip = str(ctx.rev())
        except: tip = None
        if tip: version2 = version + " HG " + tip
    else: version2 = version
    ievent.reply(version2)

cmnds.add('version', handle_version, ['USER', 'GUEST'])
examples.add('version', 'show version of the bot', 'version')
setalias('v', "version")

## short command

def handle_short(bot, ievent):
    """ arguments: <cmnd> - give short possibilities for a command. """
    try: cmnd = ievent.args[0]
    except IndexError: ievent.missing('<cmnd>') ; return
    try: ievent.reply("short commands for %s" % cmnd, getshorttable()[cmnd])
    except KeyError: ievent.reply("no commands found for %s" % cmnd)

cmnds.add('short', handle_short, ['USER', 'GUEST'])
examples.add('short', 'find full comamands', 'short admin-exceptions')

## whereis command

def handle_whereis(bot, ievent):
    """ arguments: <cmnd> - locate a command. """
    try: cmnd = ievent.args[0]
    except IndexError:
        ievent.missing('<cmnd>')
        return
    cmnds.reloadcheck(bot, ievent, cmnd)
    plugin = cmnds.whereis(cmnd)
    if plugin: ievent.reply("%s command is in: %s" %  (cmnd, plugin))
    else: ievent.reply("can't find " + cmnd)

cmnds.add('whereis', handle_whereis, ['USER', 'GUEST'])
examples.add('whereis', 'show in which plugins <what> is', 'whereis test')

## help-plug command

def handle_helpplug(bot, ievent):
    """ arguments: <plugname> - how help on plugin/command or show basic help msg. """
    try: what = ievent.args[0]
    except (IndexError, TypeError):
        ievent.reply("available plugins: ", getpluginlist())
        ievent.reply("see !help <plugin> to get help on a plugin.")
        return
    ievent.untildone = True
    cmnds.reloadcheck(bot, ievent, what)
    plugin = None
    modname = ""
    perms = []
    for package in plugin_packages:
        try:
             modname = "%s.%s" % (package, what)
             try:
                 plugin = plugs.load_mod(modname)
                 if plugin: break
             except NoSuchPlugin: continue
        except(KeyError, ImportError): pass
    if not plugin:
        ievent.reply("no %s plugin loaded" % what)
        return
    try: phelp = plugin.__doc__
    except (KeyError, AttributeError):
        ievent.reply('no description of %s plugin available' % what)
        return
    cmndresult = []
    if phelp:
        counter = 1
        for i, j in cmnds.iteritems():
            if what == j.plugname:
                try:
                    descr = j.func.__doc__
                    if not descr: descr = "no description provided"
                    try: cmndresult.append(u"    <b>!%s</b> - <i>%s</i> - perms: %s" % (i, descr, j.perms))
                    except KeyError: pass
                except AttributeError: pass
                counter += 1
    if cmndresult and phelp:
        res = []
        for r in cmndresult:
            if bot.type in ['web', ]: res.append("%s<br>" % r)
            elif bot.type in ['irc', ]: res.append(r.strip())
            else: res.append(r)
        res.sort()
        what = what.upper()
        ievent.reply('<br><b>plugin %s: </b><br>%s' % (what, phelp))
        ievent.reply("<b>commands: </b>", res, dot="count")
    else:
        if perms: ievent.reply('no commands available for permissions: %s' % ", ".join(perms))
        else: ievent.reply("can't find help on %s" % what)
    ievent.done(silent=True)

cmnds.add('help-plug', handle_helpplug, ['USER', 'GUEST'], how="msg")
examples.add('help-plug', 'get help on <plugin>', '1) help-plug 2) help-plug misc')

## help-site command

def handle_helpsite(bot, event):
    """ arguments: <cmnd> - help commands that gives a url to the docs. """
    if event.rest:
        target = cmnds.whereis(event.rest)
        target = target or event.rest
        where = bot.plugs.getmodule(target)
        if where:
            theplace = os.sep.join(where.split(".")[-2:])
            event.reply("help for %s is at http://jsonbot.org/plugins/%s.html" % (event.rest.upper(), theplace))
        else: event.reply("can't find a help url for %s" % event.rest)
    else:
        event.reply("documentation for jsonbot can be found at http://jsonbot.org or http://jsonbot.appspot.com/docs")
        event.reply('see !list for loaded plugins and "!help plugin" for a url to the plugin docs.')
    cmndhelp = cmnds.gethelp(event.rest)
    if cmndhelp: event.reply("<br><b>%s docstring: </b><br>" % event.rest, cmndhelp.split("\n"))

cmnds.add("help-site", handle_helpsite, ["OPER", "USER", "GUEST"])
examples.add("help-site", "show url pointing to the docs", "1) help 2) help rss")

## help command

def handle_help(bot, event):
    """ arguments: [<cmndname or plugname>] - show help. """
    if not event.args:
        event.reply("documentation for jsonbot can be found at http://jsonbot.org")
        event.reply('see !list for loaded plugins and "!help plugin" for help on the plugin.')
        return
    t = event.args[0]
    logging.warn("help target is %s" % t)
    cmnds.reloadcheck(bot, event, t)
    where = cmnds.whereis(t)
    cmndhelp = cmnds.gethelp(t)
    if not cmndhelp:
        ex = examples.get(t)
        if ex: cmndhelp = ex.descr
    if not cmndhelp: handle_helpplug(bot, event) ; return
    try: ex = examples[t].example
    except KeyError: ex = None
    p = cmnds.perms(t)
    res = "permissions: %s - location: %s - examples: %s" % (", ".join(p), where, ex)
    event.reply('<br><b>%s command:</b> %s' % (event.rest, cmndhelp), res.split(" - "), dot="<br>")

cmnds.add("help", handle_help, ["OPER", "USER", "GUEST"])
examples.add("help", "show help of a command", "help rss-list")

## apro command

def handle_apro(bot, ievent):
    """ arguments: <searchtxt> - apropos (search) for commands. """
    try: what = ievent.args[0]
    except IndexError:
        ievent.missing('<what>')
        return
    result = cmnds.apropos(what)
    result.sort()
    if result:
        ievent.reply("commands matching %s: " % what, result)
    else: ievent.reply('no matching commands found for %s' % what)
     
cmnds.add('apro', handle_apro, ['USER', 'GUEST'])
examples.add('apro', 'apro <what> .. search for commands that contain <what>', 'apro com')

## whatcommands command

def handle_whatcommands(bot, ievent):
    """ arguments: <permission. - show all commands with permission. """
    if not ievent.rest:
        ievent.missing('<perm>')
        return
    result = cmnds
    res = []
    for cmnd in result.values():
        if cmnd and cmnd.perms and ievent.rest in cmnd.perms:
            res.append(cmnd.cmnd)
    res.sort()
    if not res: ievent.reply('no commands known for permission %s' % ievent.rest)
    else: ievent.reply('commands known for permission %s: ' % ievent.rest, res)

cmnds.add('whatcommands', handle_whatcommands, ['USER', 'GUEST'])
examples.add('whatcommands', 'show commands with permission <perm>', 'whatcommands USER')

## versions command

def handle_versions(bot, ievent):
    """ no arguments - show versions of all loaded modules (if available). """
    versions = {}
    allowed = ["jsb.", ]
    for mod in copy.copy(sys.modules):
        for allow in allowed: 
            if mod.startswith(allow):
                try: versions[mod] = sys.modules[mod].__version__
                except AttributeError, ex: pass
        try: versions['python'] = sys.version
        except AttributeError, ex: pass
    ievent.reply("versions ==> %s" % unicode(versions))

cmnds.add('versions', handle_versions, ['USER', 'GUEST'])
examples.add('versions', 'show versions of all loaded modules', 'versions')

## loglevel command

def handle_loglevel(bot, event):
    """ arguments: <loglevel> - change loglevel of the bot. loglevel is on of debug, info, warn or error. """
    if not event.rest: event.reply("loglevel is %s" % getloglevel()) ; return
    from jsb.lib.config import getmainconfig
    mainconfig = getmainconfig()
    mainconfig.loglevel = event.rest
    mainconfig.save()
    #mainhandler.put(4, setloglevel, event.rest)
    setloglevel(event.rest)
    event.done()

cmnds.add("loglevel", handle_loglevel, "OPER")
examples.add("loglevel", "set loglevel ot on of debug, info, warning or error", "loglevel warn")

## activity command

def handle_activity(bot, ievent):
    """ no arguments - show running threads. """
    try: import threading
    except ImportError:
         ievent.reply("threading is not enabled.")
         return
    result = {}
    todo = threadloops
    for thread in threadloops:
        name = "%s_%s" % (getname(type(thread)), thread.name)
        try: result[name] = date.duration(thread.lastiter, plain=True)
        except Exception, ex: logging.warn("%s - %s" % (name, str(ex))) 
    for b in getfleet().bots:
        try: result[b.cfg.name] = date.duration(b.lastiter, plain=True)
        except Exception, ex: logging.warn("%s - %s" % (name, str(ex))) 
        
    ievent.reply("last iterations: ", result)

cmnds.add('activity', handle_activity, ['USER', 'GUEST'])
examples.add('activity', 'show time past last thread iteration', 'activity')

## threads command

def handle_threads(bot, ievent):
    """ no arguments - show running threads. """
    try: import threading
    except ImportError:
         ievent.reply("threading is not enabled.")
         return
    stats = StatDict()
    threadlist = threading.enumerate()
    for thread in threadlist: stats.upitem(thread.getName())
    result = []
    for item in stats.top(): result.append("%s = %s" % (item[0], item[1]))
    result.sort()
    ievent.reply("threads running: ", result)

cmnds.add('threads', handle_threads, ['USER', 'GUEST'])
examples.add('threads', 'show running threads', 'threads')

## loaded command

def handle_loaded(bot, event):
    """ no arguments - show plugins in cache. """
    res = []
    for plug in plugs.keys(): res.append(plug.split(".")[-1])
    event.reply("loaded plugins (cache): ", res)

cmnds.add('loaded', handle_loaded, ['USER', 'GUEST'])
examples.add('loaded', 'show list of loaded plugins', 'loaded')

## statusline command

def handle_statusline(bot, event):
    """ no arguments - show a status line. """
    event.reply("<b>controlchars:</b> %s - <b>perms:</b> %s" % (event.chan.data.cc, ", ".join(event.user.data.perms)))
	
cmnds.add('statusline', handle_statusline, ['USER', 'GUEST'])
examples.add('statusline', 'show status line', 'statusline')

## topper command

def handle_topper(bot, event):
    """ no arguments - show a 'topper' startus line. """
    event.reply("<b>forwards:</b> %s - <b>watched:</b> %s  - <b>feeds:</b> %s" % (", ".join(event.chan.data.forwards) or "none", ", ".join(event.chan.data.watched) or "none", ", ".join([unicode(x) for x in event.chan.data.feeds]) or "none"))

cmnds.add('topper', handle_topper, ['USER', 'GUEST'])
examples.add('topper', 'show topper line', 'topper')

## running command

def handle_running(bot, event):
    """ no arguments - show running tasks. """
    event.reply("<b>callbacks:</b> %s - <b>commands:</b> %s - <b>longrunning:</b> %s - <b>apirunner:</b> %s - <b>threadrunner:</b> %s" % (defaultrunner.running(), cmndrunner.running(), longrunner.running(), apirunner.running(), threadrunner.running()))

cmnds.add('running', handle_running, ['USER', 'GUEST'])
examples.add('running', "show running tasks", "running")

## descriptions command

def handle_descriptions(bot, event):
    """ no arguments - show descriptions of all plugins. """
    bot.plugs.loadall()
    result = []
    target = bot.plugs.keys()
    target.sort()
    for modname in target:
        plug = bot.plugs.get(modname)
        if plug.__doc__: txt = plug.__doc__.replace("\n", "<br>")
        else: txt = "no docstring available"
        result.append("* %s plugin (%s) - %s" % (modname.split(".")[-1], modname, txt))        
    event.reply("descriptions: <br>", result, dot="<br><br>")

cmnds.add('descriptions', handle_descriptions, ['USER', 'GUEST'])
examples.add('descriptions', "show descriptions of all plugins", "descriptions")

## stats command

def handle_stats(bot, event):
    totalstats = StatDict()
    counter = 0
    for modname in sys.modules:
       if modname.startswith("jsb"):
          plugname = modname.split(".")[-1]
          if event.args and plugname not in event.args: continue
          try: modstats = getattr(sys.modules[modname], "stats")
          except AttributeError: continue
          totalstats += modstats
          counter += 1
    event.reply("stats results from %s modules: " % counter, totalstats)

cmnds.add("stats", handle_stats, ["OPER", "USER"])
examples.add("stats", "show stats for all JSONBOT modules/plugins or specify a module/plugin", "1) stats 2) stats rss")
