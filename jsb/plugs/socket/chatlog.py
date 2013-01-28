# jsb/plugs/socket/chatlog.py
#
#

""" log channels to [hour:min] <nick> txt format, only logging to files is supported right now.  """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.callbacks import callbacks, remote_callbacks, last_callbacks, first_callbacks
from jsb.lib.persistconfig import PersistConfig
from jsb.utils.locking import lockdec
from jsb.utils.timeutils import hourmin
from jsb.lib.examples import examples
from jsb.utils.exception import handle_exception
from jsb.utils.lazydict import LazyDict
from jsb.lib.datadir import getdatadir
from jsb.utils.name import stripname
from jsb.utils.url import striphtml
from jsb.utils.format import formatevent, format_opt
from jsb.utils.log import init
from jsb.utils.statdict import StatDict
from jsb.utils.timeutils import striptime, strtotime2
from jsb.api.hooks import get_hooks
from jsb.lib.fleet import getfleet

## basic imports

import time
import os
import logging
import thread
from os import path
from datetime import datetime

## locks

outlock = thread.allocate_lock()
outlocked = lockdec(outlock)

## defines

cfg = PersistConfig()
cfg.define('channels', [])
cfg.define('format', 'log')
cfg.define('basepath', getdatadir())
cfg.define('nologprefix', '[nolog]')
cfg.define('nologmsg', '-= THIS MESSAGE NOT LOGGED =-')
cfg.define('backend', 'log')

loggers = {}
logfiles = {}
backends = {}
stopped = False
db = None
eventstolog = ["OUTPUT", "PRIVMSG", "CONSOLE", "PART", "JOIN", "QUIT", "PRESENCE", "MESSAGE", "NOTICE", "MODE", "TOPIC", "KICK", "TORNADO"]

## logging part

# BHJTW 21-02-2011 revamped to work with standard python logger

loggers = {}

def initlog(d):
    """ create the necesary directories to enable logging. """
    try: LOGDIR = d + os.sep + "chatlogs"
    except ImportError: LOGDIR = d + os.sep + "chatlogs"

    try:
        ddir = os.sep.join(LOGDIR.split(os.sep)[:-1])
        if not os.path.isdir(ddir): os.mkdir(ddir)   
    except: pass  
    try:
        if not os.path.isdir(LOGDIR): os.mkdir(LOGDIR)
    except: pass
    return LOGDIR

format = "%(message)s"

def timestr(dt):
    """ convert datatime object to a time string. """
    return dt.strftime(format_opt('timestamp_format'))   

## api_log function

def api_log(bot, event):
    channel = event.upath.split("/")[-1]
    if not channel: event.error(500) ; return
    logging.warn("in api_log function .. channel is %s" % channel)
    LOGDIR = initlog(getdatadir())
    channel = stripname(channel)
    logname = "%s_-%s.log" % ("default-irc", channel)
    logfile = LOGDIR + os.sep + logname
    f = open(logfile, "r")
    logdata = f.read()
    event.reply(logdata)      
    event.finish()
    f.close()

## enablelogging function

def enablelogging(botname, channel):
    """ set loglevel to level_name. """
    global loggers
    global logfiles
    LOGDIR = initlog(getdatadir())
    logging.warn("enabling on (%s,%s)" % (botname, channel))
    channel = stripname(channel)
    logname = "%s_%s" % (botname, channel)
    #if logname in loggers: logging.warn("there is already a logger for %s" % logname) ; return
    logfile = LOGDIR + os.sep + logname + ".log"
    try:
        filehandler = logging.handlers.TimedRotatingFileHandler(logfile, 'midnight')
        formatter = logging.Formatter(format)
        filehandler.setFormatter(formatter)
        logfiles[logfile] = time.time()
    except IOError:
        filehandler = None
    chatlogger = logging.getLoggerClass()(logname)
    chatlogger.setLevel(logging.INFO)
    if chatlogger.handlers:
        for handler in chatlogger.handlers: chatlogger.removeHandler(handler)
    if filehandler: chatlogger.addHandler(filehandler) ; logging.warn("%s - logging enabled on %s" % (botname, channel))
    else: logging.error("no file handler found - not enabling logging.")
    global lastlogger
    lastlogger = chatlogger
    loggers[logname] = lastlogger

## do tha actual logging

@outlocked
def write(m): 
    """
      m is a dict with the following properties:
      datetime
      type : (comment, nick, topic etc..)
      target : (#channel, bot etc..)
      txt : actual message
      network
    """
    backend_name = cfg.get('backend', 'log')
    backend = backends.get(backend_name, log_write)
    if m.txt.startswith(cfg.get('nologprefix')): m.txt = cfg.get('nologmsg')
    backend(m)

def log_write(m):
    if stopped: return
    logname = "%s_%s" % (m.botname, stripname(m.target))
    if logname not in loggers: return
    timestamp = timestr(m.datetime)
    m.type = m.type.upper()
    line = '%(timestamp)s%(separator)s %(txt)s\n'%({
        'timestamp': timestamp, 
        'separator': format_opt('separator'),
         'nick': m.nick,
        'txt': m.txt,
        'nick': m.nick,
        'type': m.type
    })
    try: loggers[logname].info(line.strip())
    except KeyError: logging.error("no logger available for channel %s" % logname)
    except Exception, ex: handle_exception()

backends['log'] = log_write

## log function

def log(bot, event):
    """ format an event and send it to the logging backend. """
    m = formatevent(bot, event, cfg.get("channels") or [])
    if m["txt"]: write(m)

## chatlog precondition

def prechatlogcb(bot, ievent):
    """
        Check if event should be logged.  QUIT and NICK are not channel
        specific, so we will check each channel in log().

    """
    if not ievent.channel: logging.debug("channel not set .. not logging.") ; return False
    if not cfg.channels: logging.debug("no channels set") ; return False
    if [bot.cfg.name, ievent.channel] in cfg.get('channels'): logging.info("%s %s in channels .. logging" % (bot.cfg.name, ievent.channel)) ; return True
    if not ievent.cbtype in eventstolog: logging.debug("%s ut not in eventstolog list." % ievent.cbtype) ; return False
    if ievent.msg: logging.debug("is messsage .. not logging") ; return False
    if ievent.cmnd in ('QUIT', 'NICK'): return True
    if ievent.cmnd == 'NOTICE':
        if [bot.cfg.name, ievent.arguments[0]] in cfg.get('channels'): return True
    logging.debug("not match for logging.")
    return False

## chatlog callbacks

def chatlogcb(bot, ievent):
    """ logging callback. """
    log(bot, ievent)

## plugin-start

def init():
    """ called upon plugin registration. """
    global stopped
    stopped = False
    global loggers
    fleet = getfleet()
    got = False
    for (botname, channel) in cfg.get("channels"):
        if fleet.byname(botname): enablelogging(botname, channel) ; got = True 
    #if not got: return 
    callbacks.add("PRIVMSG", chatlogcb, prechatlogcb)
    callbacks.add("JOIN", chatlogcb, prechatlogcb)
    callbacks.add("PART", chatlogcb, prechatlogcb)
    callbacks.add("NOTICE", chatlogcb, prechatlogcb)
    callbacks.add("QUIT", chatlogcb, prechatlogcb)
    callbacks.add("NICK", chatlogcb, prechatlogcb)
    callbacks.add("PRESENCE", chatlogcb, prechatlogcb)
    callbacks.add("MESSAGE", chatlogcb, prechatlogcb)
    callbacks.add("CONSOLE", chatlogcb, prechatlogcb)
    first_callbacks.add("OUTPUT", chatlogcb, prechatlogcb)
    get_hooks.register("/api/log", api_log)
    return 1

## plugin-stop

def shutdown():
    """ shutdown the plugin. """
    global stopped
    global logfiles
    stopped = True
    for file in logfiles.values():
        file.close()
    get_hooks.unregister("/api/log")
    return 1

## size

def size():
    global logfiles
    sizes = []
    for file in logfiles:
        sizes.append("%s: %s" % (file.split(os.sep)[-1], os.path.getsize(file)))
    return " - ".join(sizes)

## chatlog-on command

def handle_chatlogon(bot, ievent):
    """ no arguments - enable chatlog. """
    chan = ievent.channel
    enablelogging(bot.cfg.name, chan)
    if [bot.cfg.name, chan] not in cfg.get('channels'):
        cfg['channels'].append([bot.cfg.name, chan])
        cfg.save()
    ievent.reply('chatlog enabled on (%s,%s)' % (bot.cfg.name, chan))

cmnds.add('chatlog-on', handle_chatlogon, 'OPER')
examples.add('chatlog-on', 'enable chatlog on the channel the commands is given in', 'chatlog-on')

## chatlog-off command

def handle_chatlogoff(bot, ievent):
    """ no arguments - disable chatlog. """
    try: cfg['channels'].remove([bot.cfg.name, ievent.channel]) ; cfg.save()
    except ValueError: ievent.reply('chatlog is not enabled in (%s,%s)' % (bot.cfg.name, ievent.channel)) ; return
    try: del loggers["%s-%s" % (bot.cfg.name, stripname(ievent.channel))]
    except KeyError: pass
    except Exception, ex: handle_exception()
    ievent.reply('chatlog disabled on (%s,%s)' % (bot.cfg.name, ievent.channel))

cmnds.add('chatlog-off', handle_chatlogoff, 'OPER')
examples.add('chatlog-off', 'disable chatlog on the channel the commands is given in', 'chatlog-off')

## chatlog-searh command

def handle_chatlogsearch(bot, event):
    """ arguments: <searchtxt> - search in the logs. """
    if not event.rest: event.missing("<searchtxt>") ; return
    result = []
    chatlogdir = getdatadir() + os.sep + "chatlogs"
    if event.options and event.options.channel: chan = event.options.channel
    else: chan = event.channel
    logs = os.listdir(chatlogdir)
    logs.sort()
    for f in logs:
        filename = stripname(f)
        if not chan[1:] in filename: continue
        for line in open(chatlogdir + os.sep + filename, 'r'):
            if event.rest in line: result.append(line)
    if result: event.reply("search results for %s: " % event.rest, result, dot= " || ")
    else: event.reply("no result found for %s" % chan)

cmnds.add("chatlog-search", handle_chatlogsearch, ["OPER", "USER", "GUEST"], threaded=True)
examples.add("chatlog-search", "search the chatlogs of a channel.", "chatlog-search jsonbot")

## chatlog-stats command

def handle_chatlogstats(bot, event):
    """ no arguments - create log stats of the channel, possible options: --chan <channel> """
    what = event.rest.strip()
    chatlogdir = getdatadir() + os.sep + "chatlogs"
    if event.options and event.options.channel: chan = event.options.channel
    else: chan = event.channel
    logs = os.listdir(chatlogdir)
    if not logs: event.reply("no logs available for %s" % chan) ; return
    now = time.time()
    if what: timetarget = strtotime2(what) ; what = striptime(what)
    else: timetarget = 0 ; what = None
    event.reply("creating stats for channel %s (%s)" % (chan, time.ctime(timetarget)))
    userstats = StatDict()
    wordstats = StatDict()
    stop = False
    for f in logs[::-1]:
        filename = stripname(f)
        channel = stripname(chan[1:])
        if not channel in filename: continue
        for line in open(chatlogdir + os.sep + filename, 'r'):
            splitted = line.strip().split()
            if len(splitted) < 2: continue
            who = "unknown"
            for i in splitted:
               if i.startswith("<"): who = i[1:-1]
            if what and who != what: continue
            timestr = "%s %s" % (splitted[0], splitted[1])
            logtime = strtotime2(timestr)
            if logtime:
                if logtime > timetarget: userstats.upitem(who)
                else: continue
            else: userstats.upitem(who)
            for word in splitted[4:]: wordstats.upitem(word)
    if what: result = wordstats.top()
    else: result = userstats.top()
    if result:
        res = ["%s: %s" % item for item in result]
        event.reply("stat results for %s: " % (what or chan), res)
    else: event.reply("no result found for %s" % (what or chan))

cmnds.add("chatlog-stats", handle_chatlogstats, ["OPER", "USER", "GUEST"], threaded=True)
examples.add("chatlog-stats", "stats of a channel.", "chatlog-stats")
