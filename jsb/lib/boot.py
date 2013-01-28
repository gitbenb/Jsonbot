# jsb/boot.py
#
#

""" admin related data and functions. """

## jsb imports

from jsb.utils.generic import checkpermissions, isdebian, botuser
from jsb.lib.persist import Persist
from jsb.lib.aliases import savealiases
from jsb.utils.exception import handle_exception
from jsb.lib.datadir import makedirs, getdatadir
from jsb.lib.config import Config, getmainconfig
from jsb.lib.jsbimport import _import
from jsb.utils.lazydict import LazyDict
from jsb.memcached import startmcdaemon
from jsb.lib.runner import threadrunner

## basic imports

import logging
import os
import sys
import types
import copy

## paths

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.getcwd() + os.sep + '..')

## defines

plugin_packages = ['jsb.plugs.core', 'jsb.plugs.common', 'jsb.plugs.socket', 'myplugs', 'myplugs.socket', 'myplugs.common']
default_plugins = ['jsb.plugs.core.admin', 'jsb.plugs.core.dispatch', 'jsb.plugs.core.plug', 'jsb.lib.periodical']
default_deny = ["jsb.plugs.socket.fish", ]

logging.info("default plugins are %s" % str(default_plugins))

loaded = False
cmndtable = None 
pluginlist = None
callbacktable = None
retable = None
cmndperms = None
shorttable = None
timestamps = None
plugwhitelist = None
plugblacklist = None
cpy = copy.deepcopy

## scandir function

def scandir(d, dbenable=False):
    from jsb.lib.plugins import plugs
    changed = []
    try:
        changed = checktimestamps(d, dbenable)
        mods = []
        if changed:
            logging.debug("files changed %s" % str(changed))
            for plugfile in changed:
                if not dbenable and os.sep + 'db' in plugfile: logging.warn("db not enabled .. skipping %s" % plugfile) ; continue 
        return changed
    except Exception, ex: logging.error("boot - can't read %s dir." % d) ; handle_exception()
    if changed: logging.debug("%s files changed -=- %s" % (len(changed), str(changed)))
    return changed

## boot function

def boot(ddir=None, force=False, encoding="utf-8", umask=None, saveperms=True, fast=False, clear=False, loadall=False):
    """ initialize the bot. """
    global plugin_packages
    try:
        if os.getuid() == 0:
            print "don't run the bot as root"
            os._exit(1)
    except AttributeError: pass
    logging.warn("starting!")
    from jsb.lib.datadir import getdatadir, setdatadir
    if ddir: setdatadir(ddir)
    origdir = ddir 
    ddir = ddir or getdatadir()
    if not ddir: logging.error("can't determine datadir to boot from") ; raise Exception("can't determine datadir")
    if not ddir in sys.path: sys.path.append(ddir)
    makedirs(ddir)
    if os.path.isdir("/var/run/jsb") and botuser() == "jsb": rundir = "/var/run/jsb"
    else: rundir = ddir + os.sep + "run"
    try:
        k = open(rundir + os.sep + 'jsb.pid','w')
        k.write(str(os.getpid()))
        k.close()
    except IOError: pass
    try:
        reload(sys)
        sys.setdefaultencoding(encoding)
    except (AttributeError, IOError): handle_exception()
    try:
        if not umask: checkpermissions(getdatadir(), 0700) 
        else: checkpermissions(getdatadir(), umask)  
    except: handle_exception()
    from jsb.lib.plugins import plugs
    global loaded
    global cmndtable
    global retable
    global pluginlist
    global callbacktable
    global shorttable
    global cmndperms
    global timestamps
    global plugwhitelist
    global plugblacklist
    if not retable: retable = Persist(rundir + os.sep + 'retable')
    if clear: retable.data = {}
    if not cmndtable: cmndtable = Persist(rundir + os.sep + 'cmndtable')
    if clear: cmndtable.data = {}
    if not pluginlist: pluginlist = Persist(rundir + os.sep + 'pluginlist')
    if clear: pluginlist.data = []
    if not callbacktable: callbacktable = Persist(rundir + os.sep + 'callbacktable')
    if clear: callbacktable.data = {}
    if not shorttable: shorttable = Persist(rundir + os.sep + 'shorttable')
    if clear: shorttable.data = {}
    if not timestamps: timestamps = Persist(rundir + os.sep + 'timestamps')
    #if clear: timestamps.data = {}
    if not plugwhitelist: plugwhitelist = Persist(rundir + os.sep + 'plugwhitelist')
    if not plugwhitelist.data: plugwhitelist.data = []
    if not plugblacklist: plugblacklist = Persist(rundir + os.sep + 'plugblacklist')
    if not plugblacklist.data: plugblacklist.data = []
    if not cmndperms: cmndperms = Config('cmndperms', ddir=ddir)
    changed = []
    gotlocal = False
    dosave = clear or False
    maincfg = getmainconfig(ddir=ddir)
    logging.warn("mainconfig used is %s" % maincfg.cfile)
    if os.path.isdir('jsb'):
        gotlocal = True
        packages = find_packages("jsb" + os.sep + "plugs")
        pluglist = [x for x in packages if not 'db' in x]
        for p in pluglist:
            if p not in plugin_packages: plugin_packages.append(p)
    for plug in default_plugins:
        plugs.reload(plug, showerror=True, force=True)
    changed = scandir(getdatadir() + os.sep + 'myplugs', dbenable=maincfg.dbenable)
    if changed:
        logging.debug("myplugs has changed -=- %s" % str(changed))
        for plugfile in changed:
            if "gae" in plugfile: continue
            try: plugs.reloadfile(plugfile, force=True)
            except Exception, ex: handle_exception()
        dosave = True
    configchanges = checkconfig()
    if configchanges:
        logging.info("there are configuration changes: %s" % str(configchanges))
        for f in configchanges:
            if 'mainconfig' in f: force = True ; dosave = True
    if os.path.isdir('jsb'):
        corechanges = scandir("jsb" + os.sep + "plugs", dbenable=maincfg.dbenable)
        if corechanges:
            logging.debug("core changed -=- %s" % str(corechanges))
            for plugfile in corechanges:
                if not maincfg.dbenable and "db" in plugfile: continue
                if "gae" in plugfile: continue
                try: plugs.reloadfile(plugfile, force=True)
                except Exception, ex: handle_exception()
            dosave = True
    if maincfg.dbenable:
        if not 'jsb.plugs.db' in plugin_packages: plugin_packages.append("jsb.plugs.db") 
        try:
            from jsb.db import getmaindb
            from jsb.db.tables import tablestxt
            db = getmaindb()
            if db: db.define(tablestxt)
        except Exception, ex: logging.warn("could not initialize database %s" % str(ex))
    else:
        logging.warn("db not enabled, set dbenable = 1 in %s to enable" % getmainconfig().cfile)
        try: plugin_packages.remove("jsb.plugs.db")
        except ValueError: pass
    if force or dosave or not cmndtable.data or len(cmndtable.data) < 100:
        logging.debug("using target %s" % str(plugin_packages))
        plugs.loadall(plugin_packages, force=True)
        savecmndtable(saveperms=saveperms)
        savepluginlist()
        savecallbacktable()
        savealiases()
    logging.warn("ready")

## filestamps stuff

def checkconfig():
    changed = []
    d = getdatadir() + os.sep + "config"
    for f in os.listdir(d):
        if os.path.isdir(d + os.sep + f):
            dname = d + os.sep + f
            changed.extend(checktimestamps(d + os.sep + f))
            continue
        m = d + os.sep + f
        if os.path.isdir(m): continue
        if "__init__" in f: continue
        global timestamps
        try:
            t = os.path.getmtime(m)
            if t > timestamps.data[m]: changed.append(m) ; timestamps.data[m] = t ; 
        except KeyError: timestamps.data[m] = os.path.getmtime(m) ; changed.append(m)
    if changed: timestamps.save()
    return changed 

def checktimestamps(d=None, dbenable=False):
    changed = []
    for f in os.listdir(d):
        if os.path.isdir(d + os.sep + f):
            if "gae" in f: continue
            if f.startswith("."): logging.warn("skipping %s" % f) ; continue
            dname = d + os.sep + f
            if not dbenable and 'db' in dname: continue
            splitted = dname.split(os.sep)
            target = []
            for s in splitted[::-1]:
                target.append(s)
                if 'jsb' in s: break
                elif 'myplugs' in s: break
            package = ".".join(target[::-1])
            if not "config" in dname and package not in plugin_packages: logging.warn("adding %s to plugin_packages" % package) ; plugin_packages.append(package)
            changed.extend(checktimestamps(d + os.sep + f))
        if not f.endswith(".py"): continue 
        m = d + os.sep + f
        global timestamps
        try:
            t = os.path.getmtime(m)
            if t > timestamps.data[m]: changed.append(m) ; timestamps.data[m] = t ; 
        except KeyError: timestamps.data[m] = os.path.getmtime(m) ; changed.append(m)
    if changed: timestamps.save()
    return changed 

def find_packages(d=None):
    packages = []
    for f in os.listdir(d):
        if os.path.isdir(d + os.sep + f):
            if "gae" in f: continue
            if f.startswith("."): logging.warn("skipping %s" % f) ; continue
            dname = d + os.sep + f
            splitted = dname.split(os.sep)
            target = []
            for s in splitted[::-1]:
                target.append(s)
                if 'jsb' in s: break
                elif 'myplugs' in s: break
            package = ".".join(target[::-1])
            if package not in plugin_packages: logging.info("adding %s to plugin_packages" % package) ; packages.append(package)
            packages.extend(find_packages(d + os.sep + f))
    return packages
    
## commands related commands

def savecmndtable(modname=None, saveperms=True):
    """ save command -> plugin list to db backend. """
    global cmndtable
    if not cmndtable.data: cmndtable.data = {}
    if modname: target = LazyDict(cmndtable.data)
    else: target = LazyDict()
    global shorttable
    if not shorttable.data: shorttable.data = {}
    if modname: short = LazyDict(shorttable.data)
    else: short = LazyDict()
    global cmndperms
    from jsb.lib.commands import cmnds
    assert cmnds
    for cmndname, c in cmnds.iteritems():
        if modname and c.modname != modname or cmndname == "subs": continue
        if cmndname and c:
            target[cmndname] = c.modname  
            cmndperms[cmndname] = c.perms
            try:
                 s = cmndname.split("-")[1]
                 if not target.has_key(s):
                     if not short.has_key(s): short[s] = [cmndname, ]
                     if cmndname not in short[s]: short[s].append(cmndname)
            except (ValueError, IndexError): pass
    logging.warn("saving command table")
    assert cmndtable
    assert target
    cmndtable.data = target
    cmndtable.save()
    logging.warn("saving short table")
    assert shorttable
    assert short
    shorttable.data = short
    shorttable.save()
    logging.warn("saving RE table")
    for command in cmnds.regex:
        retable.data[command.regex] = command.modname
    assert retable
    retable.save()
    if saveperms:
        logging.warn("saving command perms")
        cmndperms.save()

def removecmnds(modname):
    """ remove commands belonging to modname form cmndtable. """
    global cmndtable
    assert cmndtable
    from jsb.lib.commands import cmnds
    assert cmnds
    for cmndname, c in cmnds.iteritems():
        if c.modname == modname: del cmndtable.data[cmndname]
    cmndtable.save()

def getcmndtable():
    """ save command -> plugin list to db backend. """
    global cmndtable
    if not cmndtable: boot()
    return cmndtable.data

def getshorttable():
    """ save command -> plugin list to db backend. """
    global shorttable
    if not shorttable: boot()
    return shorttable.data

## callbacks related commands

def savecallbacktable(modname=None):
    """ save command -> plugin list to db backend. """
    if modname: logging.warn("boot - module name is %s" % modname)
    global callbacktable
    assert callbacktable
    if not callbacktable.data: callbacktable.data = {}
    if modname: target = LazyDict(callbacktable.data)
    else: target = LazyDict()
    from jsb.lib.callbacks import first_callbacks, callbacks, last_callbacks, remote_callbacks
    for cb in [first_callbacks, callbacks, last_callbacks, remote_callbacks]:
        for type, cbs in cb.cbs.iteritems():
            for c in cbs:
                if modname and c.modname != modname: continue
                if not target.has_key(type): target[type] = []
                if not c.modname in target[type]: target[type].append(c.modname)
    logging.warn("saving callback table")
    assert callbacktable
    assert target
    callbacktable.data = target
    callbacktable.save()

def removecallbacks(modname):
    """ remove callbacks belonging to modname form cmndtable. """
    global callbacktable
    assert callbacktable
    from jsb.lib.callbacks import first_callbacks, callbacks, last_callbacks, remote_callbacks
    for cb in [first_callbacks, callbacks, last_callbacks, remote_callbacks]:
        for type, cbs in cb.cbs.iteritems():
            for c in cbs:
                if not c.modname == modname: continue
                if not callbacktable.data.has_key(type): callbacktable.data[type] = []
                if c.modname in callbacktable.data[type]: callbacktable.data[type].remove(c.modname)
    logging.warn("saving callback table")
    assert callbacktable
    callbacktable.save()

def getcallbacktable():
    """ save command -> plugin list to db backend. """
    global callbacktable
    if not callbacktable: boot()
    return callbacktable.data

def getretable():
    """ save command -> plugin list to db backend. """
    global retable
    if not retable: boot()
    return retable.data

## plugin list related commands

def savepluginlist(modname=None):
    """ save a list of available plugins to db backend. """
    global pluginlist
    if not pluginlist.data: pluginlist.data = []
    if modname: target = cpy(pluginlist.data)
    else: target = []
    from jsb.lib.commands import cmnds
    assert cmnds
    for cmndname, c in cmnds.iteritems():
        if modname and c.modname != modname: continue
        if c and not c.plugname: logging.info("boot - not adding %s to pluginlist" % cmndname) ; continue
        if c and c.plugname not in target and c.enable: target.append(c.plugname)
    assert target
    target.sort()
    logging.warn("saving plugin list")
    assert pluginlist
    pluginlist.data = target
    pluginlist.save()

def remove_plugin(modname):
    removecmnds(modname)
    removecallbacks(modname)
    global pluginlist
    try: pluginlist.data.remove(modname.split(".")[-1]) ; pluginlist.save()
    except: pass

def clear_tables():
    global cmndtable
    global callbacktable
    global pluginlist
    cmndtable.data = {} ; cmndtable.save()
    callbacktable.data = {} ; callbacktable.save()
    pluginlist.data = [] ; pluginlist.save()

def getpluginlist():
    """ get the plugin list. """
    global pluginlist
    if not pluginlist: boot()
    l = plugwhitelist.data or pluginlist.data
    result = []
    denied = []
    for plug in plugblacklist.data:
        denied.append(plug.split(".")[-1])
    for plug in l:
        if plug not in denied: result.append(plug)
    return result

## update_mod command

def update_mod(modname):
    """ update the tables with new module. """
    savecallbacktable(modname)
    savecmndtable(modname, saveperms=False)
    savepluginlist(modname)

def whatcommands(plug):
    tbl = getcmndtable()
    result = []
    for cmnd, mod in tbl.iteritems():
        if not mod: continue
        modfile = mod.split(".")[-1]
        if plug in modfile:
            result.append(cmnd)
    return result

def getcmndperms():
    return cmndperms

def plugenable(mod):
    if plugwhitelist.data and not mod in plugwhitelist.data: plugwhitelist.data.append(mod) ; plugwhtelist.save() ; return
    if mod in plugblacklist.data: plugblacklist.data.remove(mod) ; plugblacklist.save()

def plugdisable(mod):
    if plugwhitelist.data and mod in plugwhitelist.data: plugwhitelist.data.remove(mod) ; plugwhtelist.save() ; return
    if not mod in plugblacklist.data: plugblacklist.data.append(mod) ; plugblacklist.save()

def isenabled(mod):
    if mod in default_deny and mod not in plugwhitelist.data: return False
    if mod in plugblacklist.data: return False
    return True

def size():
    global cmndtable
    global pluginlist
    global callbacktable
    global cmndperms
    global timestamps 
    global plugwhitelist
    global plugblacklist 
    return "cmndtable: %s - pluginlist: %s - callbacks: %s - timestamps: %s - whitelist: %s - blacklist: %s" % (cmndtable.size(), pluginlist.size(), callbacktable.size(), timestamps.size(), plugwhitelist.size(), plugblacklist.size())
   