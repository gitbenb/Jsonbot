# jsb/utils/log.py
#
#

""" log module. """

## jsb import

from jsb.lib.datadir import getdatadir

## basic imports

import logging
import logging.handlers
import os
import os.path
import getpass

## defines

logfilter = ["looponce", "PING"]
logplugs = []

TAGS = { 
         'dosync': logging.INFO,
         'TICK': logging.DEBUG,
         'TICK60': logging.DEBUG,
         'runner.cleanup': logging.INFO,
         'sleeptime': logging.INFO,
         'lastpoll': logging.INFO
       }           

ERASE_LINE = '\033[2K'
BOLD='\033[1m'
RED = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
ENDC = '\033[0m'


LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'warn': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL
         }

RLEVELS = {logging.DEBUG: 'debug',
           logging.INFO: 'info',
           logging.WARNING: 'warn',
           logging.ERROR: 'error',
           logging.CRITICAL: 'critical'
          }

## init fuction

def init(d):
    LOGDIR = d + os.sep + "botlogs" # BHJTW change this for debian
    try:
        ddir = os.sep.join(LOGDIR.split(os.sep)[:-1])
        if not os.path.isdir(ddir): os.mkdir(ddir)
    except: pass

    try:
        if not os.path.isdir(LOGDIR): os.mkdir(LOGDIR)
    except: pass
    return LOGDIR

## core shit

level = logging.WARNING
filehandler = None

## MyFilter class

class MyFilter(logging.Filter):

    def filter(self, record):
        for f in logfilter:
            if f in record.msg: return False
        for modname in logplugs:
            if modname in record.module: record.levelno = logging.WARN ; return True
        for tag, l in TAGS.iteritems():
           if tag in record.msg:
                try: record.levelno = LEVELS[l]
                except KeyError, ex: pass
        return True

## setloglevel function

def setloglevel(level_name="warn", colors=True, datadir=None):
    """ set loglevel to level_name. """
    if not level_name: return
    global level
    global filehandler
    LOGDIR = init(getdatadir())
    format_short = "\033[1m%(asctime)-8s\033[0m -=- %(levelname)-8s -=- \033[93m%(message)-75s\033[0m -=- \033[92m%(module)s.%(funcName)s.%(lineno)s\033[0m -=- \033[94m%(threadName)s\033[0m"
    format_short_plain = "%(asctime)-8s -=- %(levelname)-8s -=- %(message)-75s -=- %(module)s.%(funcName)s.%(lineno)s -=- %(threadName)s"
    datefmt = '%H:%M:%S'
    formatter_short = logging.Formatter(format_short, datefmt=datefmt)
    formatter_short_plain = logging.Formatter(format_short_plain, datefmt=datefmt)
    try:
        filehandler = logging.handlers.TimedRotatingFileHandler(LOGDIR + os.sep + "jsb.log", 'midnight')
    except (IOError, AttributeError), ex:
        logging.error("can't create file loggger %s" % str(ex))
        filehandler = None
    docolors = colors or False
    level = LEVELS.get(str(level_name).lower(), logging.NOTSET)
    root = logging.getLogger()
    root.addFilter(MyFilter())
    root.setLevel(level)
    if root and root.handlers:
        for handler in root.handlers: root.removeHandler(handler)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    if True:
         ch.addFilter(MyFilter())
         if docolors: ch.setFormatter(formatter_short)
         else: ch.setFormatter(formatter_short_plain)
         if filehandler: filehandler.setFormatter(formatter_short_plain)
    root.addHandler(ch)
    if filehandler: root.addHandler(filehandler)
    logging.warn("loglevel is %s (%s)" % (str(level), level_name))

def getloglevel(name=""):
    import logging
    root = logging.getLogger(name)
    return RLEVELS.get(root.getEffectiveLevel())

def setlogplug(modname):
    global logplugs
    if len(modname) < 3: logging.warn("plugin name must be at least 3 chars") ; return False
    if not modname in logplugs: logplugs.append(modname)
    return True

def dellogplug(modname):
    global logplugs
    try: logplugs.remove(modname)
    except ValueError: logging.warn("%s is not in logplugs" % modname) ; return False
    return True

def setlogfilter(filtertxt):
    global logfilter
    if len(filtertxt) < 3: logging.warn("plugin name must be at least 3 chars") ; return False
    if not filtertxt in logfilter: logfilter.append(filtertxt)
    return True

def dellogfilter(filtertxt):
    global logfilter
    try: logfilter.remove(filtertxt)
    except ValueError: logging.warn("%s is not in logfilter" % filtertxt) ; return False
    return True
