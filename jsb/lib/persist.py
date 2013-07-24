# jsb/persist.py
#
#

"""
    allow data to be written to disk or BigTable in JSON format. creating 
    the persisted object restores data. 

"""

## jsb imports

from jsb.utils.trace import whichmodule, calledfrom, callstack, where
from jsb.utils.lazydict import LazyDict
from jsb.utils.exception import handle_exception
from jsb.utils.name import stripname
from jsb.utils.locking import lockdec
from jsb.utils.timeutils import elapsedstring
from jsb.lib.callbacks import callbacks
from jsb.lib.errors import MemcachedCounterError, JSONParseError, WrongFileName

from datadir import getdatadir

## simplejson imports

from jsb.imports import getjson
json = getjson()

## basic imports

from collections import deque
import thread
import logging
import os
import os.path
import types
import copy
import sys
import time

## defines

cpy = copy.deepcopy

## locks


persistlock = thread.allocate_lock()
persistlocked = lockdec(persistlock)

## global list to keeptrack of what persist objects need to be saved

needsaving = deque()

def cleanup(bot=None, event=None):
    global needsaving
    #todo = cpy(needsaving)
    r = []
    for p in needsaving:
        try: p.dosave() ; r.append(p) ; logging.warn("saved on retry - %s" % p.fn)
        except (OSError, IOError), ex: logging.error("failed to save %s - %s" % (p, str(ex)))
    for p in r:
        try: needsaving.remove(p)
        except ValueError: pass
    return needsaving


got = False
from jsb.memcached import getmc
mc = getmc()
if mc:
    status = mc.get_stats()
    if status:
        logging.warn("memcached uptime is %s" % elapsedstring(status[0][1]['uptime']))
        got = True
else: logging.debug("no memcached found - using own cache")
from cache import get, set, delete

import fcntl

## classes

class Persist(object):

    """ persist data attribute to JSON file. """
        
    def __init__(self, filename, default=None, init=True, postfix=None, needexist=False):
        """ Persist constructor """
        if postfix: self.fn = str(filename.strip()) + str("-%s" % postfix)
        else: self.fn = str(filename.strip())
        if needexist and not os.path.exists(self.fn): raise WrongFileName(self.fn)
        self.lock = thread.allocate_lock() # lock used when saving)
        self.data = LazyDict(default=default) # attribute to hold the data
        self.setlogname()
        self.countername = self.fn + "_" + "counter"
        if got:
            count = mc.get(self.countername)
            try:
                self.mcounter = self.counter = int(count)
            except (ValueError, TypeError):
                self.mcounter = self.counter = mc.set(self.countername, "1") or 0
        else:
            self.mcounter = self.counter = 0
        self.ssize = 0
        self.jsontxt = ""
        self.dontsave = False
        if init:
            self.init(default)
            if default == None: default = LazyDict()
        self.setlogname()

    def setlogname(self):
        try:
            res = []
            target = getdatadir().split(os.sep)
            if not target[-1]: target = target[-2]
            else: target = target[-1] 
            for i in self.fn.split(os.sep)[::-1]:
                if target in i: break
                if i.endswith(os.sep): i = i[:-1]
                res.append(i)
            self.logname = os.sep.join(res[::-1])
            if not self.logname: self.logname = self.fn
        except: handle_exception() ; self.logname = self.fn

    def size(self):
        return "%s (%s)" % (len(self.data), len(self.jsontxt))

    def init(self, default={}, filename=None):
        """ initialize the data. """
        gotcache = False
        cachetype = "cache"
        try:
            logging.debug("using name %s" % self.fn)
            a = get(self.fn)
            if a: self.data = a
            else: self.data = None
            if self.data != None:
                logging.debug("got data from local cache")
                return self
            if got: self.jsontxt = mc.get(self.fn) ; cachetype = "cache"
            if not self.jsontxt:
               datafile = open(self.fn, 'r')
               self.jsontxt = datafile.read()
               datafile.close()
               self.ssize = len(self.jsontxt)
               cachetype = "file"
               if got: mc.set(self.fn, self.jsontxt)
        except IOError, ex:
            if not 'No such file' in str(ex):
                logging.error('failed to read %s: %s' % (self.fn, str(ex)))
                raise
            else:
                logging.debug("%s doesn't exist yet" % self.fn)
                self.jsontxt = json.dumps(default)
        try:
            if self.jsontxt:
                logging.debug(u"loading: %s" % type(self.jsontxt))
                try: self.data = json.loads(str(self.jsontxt))
                except Exception, ex: logging.error("couldn't parse %s in the %s file" % (self.jsontxt, self.fn)) ; self.data = None ; self.dontsave = True
            if not self.data: self.data = LazyDict()
            elif type(self.data) == types.DictType:
                logging.debug("converting dict to LazyDict")
                d = LazyDict()
                d.update(self.data)
                self.data = d
            set(self.fn, self.data)
            logging.debug("loaded %s - %s" % (self.logname, cachetype))
        except Exception, ex:
            logging.error('ERROR: %s' % self.fn)
            raise

    def upgrade(self, filename):
        self.init(self.data, filename=filename)
        self.save(filename)

    def get(self):
        logging.debug("getting %s from local cache" % self.fn)
        a = get(self.fn)
        logging.debug("got %s from local cache" % type(a))
        return a

    def sync(self):
        logging.debug("syncing %s" % self.fn)
        if got: mc.set(self.fn, json.dumps(self.data))
        set(self.fn, self.data)
        return self

    def save(self):
        cleanup()
        global needsaving
        try: self.dosave()
        except (IOError, OSError):
            self.sync()
            if self not in needsaving: needsaving.append(self)

    @persistlocked
    def dosave(self):
        """ persist data attribute. """
        try:
            if self.dontsave: logging.error("dontsave is set on  %s - not saving" % self.fn) ; return
            fn = self.fn
            if got: self.mcounter = int(mc.incr(self.countername))
            if got and (self.mcounter - self.counter) > 1:
                tmp = json.loads(mc.get(fn))
                if tmp:
                    try: tmp.update(self.data) ; self.data = LazyDict(tmp) ; logging.warn("updated %s" % fn)
                    except AttributeError: pass
                self.counter = self.mcounter
            d = []
            if fn.startswith(os.sep): d = [os.sep,]
            for p in fn.split(os.sep)[:-1]:
                if not p: continue
                d.append(p)
                pp = os.sep.join(d)
                if not os.path.isdir(pp):
                    logging.warn("creating %s dir" % pp)
                    os.mkdir(pp)
            tmp = fn + '.tmp' # tmp file to save to
            datafile = open(tmp, 'w')
            fcntl.flock(datafile, fcntl.LOCK_EX | fcntl.LOCK_NB)
            json.dump(self.data, datafile, indent=True)
            fcntl.flock(datafile, fcntl.LOCK_UN)
            datafile.close()
            try: os.rename(tmp, fn)
            except (IOError, OSError):
                os.remove(fn)
                os.rename(tmp, fn)
            jsontxt = json.dumps(self.data)
            logging.debug("setting cache %s - %s" % (fn, jsontxt))
            self.jsontxt = jsontxt
            set(fn, self.data)
            if got: mc.set(fn, jsontxt)
            if 'sleeptime' in self.fn: logging.info('%s saved' % self.logname)
            else: logging.info('%s saved' % self.logname)
        except IOError, ex: logging.error("not saving %s: %s" % (self.fn, str(ex))) ; raise
        except: raise
        finally: pass

## findfilenames function 

def findfilenames(target, filter=[], skip=[]):
    logging.debug("finding files in %s - filter: %s - skip: %s" % (target, filter, skip))
    res = []
    result = []
    if not os.path.isdir(target): return res
    if not target.endswith(os.sep): target += os.sep
    for f in os.listdir(target):
        for s in skip:
            if s in f: continue
        fname = target + f
        if os.path.isdir(fname): res.extend(findfilenames(fname, filter, skip))
        go = True
        for fil in filter:
            if fil.lower() not in fname.lower(): go = False ; break
        if not go: continue
        res.append(fname)
    return res

def findnames(target, filter=[], skip=[]):
    res = []
    for f in findfilenames(target, filter, skip):
        res.append(f.split(os.sep)[-1])
    return res


class PlugPersist(Persist):

    """ persist plug related data. data is stored in jsondata/plugs/{plugname}/{filename}. """

    def __init__(self, filename, default={}, *args, **kwargs):
        plugname = calledfrom(sys._getframe())
        Persist.__init__(self, getdatadir() + os.sep + 'plugs' + os.sep + stripname(plugname) + os.sep + stripname(filename), default=default, *args, **kwargs)

class GlobalPersist(Persist):

    """ persist plug related data. data is stored in jsondata/plugs/{plugname}/{filename}. """

    def __init__(self, filename, default={}, *args, **kwargs):
        if not filename: raise Exception("filename not set in GlobalPersist")
        logging.warn("filename is %s" % filename)
        Persist.__init__(self, getdatadir() + os.sep + 'globals' + os.sep + stripname(filename), default=default, *args, **kwargs)

## PersistCollection class

class PersistCollection(object):

    """ maintain a collection of Persist objects. """

    def __init__(self, path, *args, **kwargs):
        assert path
        self.path = path
        d = [os.sep, ]
        logging.warn("path is %s" % self.path)
        for p in path.split(os.sep):
            if not p: continue
            d.append(p)
            pp = os.sep.join(d)
            try:
                os.mkdir(pp)
                logging.warn("creating %s dir" % pp)
            except OSError, ex:
                if 'Errno 13' in str(ex) or 'Errno 2' in str(ex) or "Errno 17" in str(ex): continue
                logging.warn("can't make %s - %s" % (pp,str(ex))) ; continue
                
    def filenames(self, filter=[], path=None, skip=[], result=[]):
        target = path or self.path
        res = findfilenames(target, filter, skip)
        logging.warn("filenames are %s" % str(res))
        return res

    def names(self, filter=[], path=None, skip=[], result=[]):
        target = path or self.path
        res = findnames(target, filter, skip)
        return res

    def search(self, field, target):
        res = []
        for obj in self.objects().values():
            try: item = getattr(obj.data, field)
            except AttributeError: handle_exception() ; continue
            if not item: continue
            if target in item: res.append(obj)
        return res
            
    def objects(self, filter=[], path=None):
        if type(filter) != types.ListType: filter = [filter, ] 
        res = {}
        target = path or self.path
        for f in self.filenames(filter, target):
             res[f] = Persist(f)
        return res

## PlugPersistCollection class

class PlugPersistCollection(PersistCollection):

    def __init__(self):
        plugname = calledfrom(sys._getframe())
        logging.warn("plugin is %s" % plugname)
        self.path =  getdatadir() + os.sep + 'plugs' + os.sep + stripname(plugname) + os.sep
        PersistCollection.__init__(self, self.path)

## GlobalPersistCollection class

class GlobalPersistCollection(PersistCollection):

    def __init__(self):
        self.path =  getdatadir() + os.sep + 'globals'
        GlobalCollection(self, self.path)


callbacks.add("TICK60", cleanup)
