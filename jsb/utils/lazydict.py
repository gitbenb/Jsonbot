# jsb/utils/lazydict.py
#
# thnx to maze

""" a lazydict allows dotted access to a dict .. dict.key. """

## jsb imports

from jsb.utils.locking import lockdec
from jsb.utils.exception import handle_exception
from jsb.utils.trace import whichmodule, where
from jsb.lib.errors import PropertyIgnored
from jsb.imports import getjson
json = getjson()

## basic imports

from  xml.sax.saxutils import unescape
import copy
import logging
import types
import threading
import os
import re
import types

## locks

lock = threading.RLock()
locked = lockdec(lock)

## defines

defaultignore = ['aliases', 'userhosts', 'owner', '_comments', 'result', 'plugs', 'origevent', 'passwords', 'key', 'finished', 'inqueue', 'resqueue', 'outqueue', 'waitlist', 'comments', 'createdfrom', 'webchannels', 'tokens', 'token', 'cmndperms', 'gatekeeper', 'stanza', 'isremote', 'iscmnd', 'orig', 'bot', 'origtxt', 'body', 'subelements', 'args', 'rest', 'pass', 'password', 'fsock', 'sock', 'handlers', 'users', 'plugins']
minignore = ['aliases', '_comments', 'plugs', 'user', 'chan', 'password', 'key', 'passwords', 'threads', 'comments']
dontshow = ['maincfg', 'cfg', 'filename', 'origname', 'origdir', 'cfile', 'dir', 'filename', 'modname', 'dbpasswd', 'dbname', 'dbuser', 'datadir' , 'origdir', 'dbhost']
cpy = copy.deepcopy

## checkignore function

def checkignore(name, ignore):
    """ see whether a element attribute (name) should be ignored. """
    name = unicode(name)
    if name.startswith('_'): return True
    for item in ignore:
        if item == name:
            return True
    return False

## stripignore function

def stripignore(d):
    """ strip to be ignored items from dict, make copy first """
    try: dd = cpy(d)
    except Exception, ex: logging.error("can't copy dict: %s" % str(ex)) ; raise
    for name in defaultignore:
        try: del dd[name]
        except KeyError: pass
    return dd

#@locked
def dumpelement(element, prev={}, withtypes=False, full=False):
    """ check each attribute of element whether it is dumpable. """
    try: elem = cpy(element)
    except Exception, ex: logging.error("can't copy %s" % str(ex)) ; return str(type(element))
    if not elem: elem = element
    try: new = LazyDict(prev) 
    except (TypeError, ValueError): new = LazyDict()
    for name in elem:
        if not full and checkignore(name, defaultignore): continue
        elif checkignore(name, minignore): continue
        try:
            json.dumps(elem[name])
            try: new[name] = stripignore(elem[name])
            except: new[name] = elem[name]
        except TypeError:
            if type(elem[name]) not in jsontypes:
                if withtypes: new[name] = str(type(elem[name]))
            else:
                logging.warn("lazydict - dumpelement - %s" % elem[name])
                new[name] = dumpelement(elem[name], new, full)
    return stripignore(new)

## LazyDict class

class LazyDict(dict):

    """ lazy dict allows dotted access to a dict """


    def __repr__(self):
        return '<%s.%s object at %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self))
        )

    def __deepcopy__(self, a):
        return LazyDict(self) 

    def __unicode__(self):
        return str(self).encode("utf-8")

    def __getattr__(self, attr, default=""):
        """ get attribute. """
        if not self.has_key(attr): return cpy(default)
        return self[attr]

    def __setattr__(self, attr, value):
        """ set attribute. """
        if not self.overload and self.has_key(attr) and type(self[attr]) in [types.FunctionType, types.MethodType]:
            mod = whichmodule(2)
            raise Exception("lazydict - cannot change a function of method: %s - called from %s" % (attr, mod))
        self[attr] = value

    def all(self):
        result = {}
        for key, val in self.iteritems():
            if type(val) not in [types.MethodType,]: result[key] = val
        return result

    def render(self, template):
        temp = open(template, 'r').read()
        for key, value in self.iteritems():
            try: temp = temp.replace("{{ %s }}" % key, value)
            except: pass 
        return temp

    def dostring(self):
        """ return a string representation of the dict """
        res = ""
        cp = dict(self)
        for item, value in cp.iteritems(): res += "%r=%r " % (item, value)
        return res

    def tojson(self, withtypes=False, full=False):
        """ dump the lazydict object to json. """
        try:
            return json.dumps(dumpelement(self, withtypes, full))
        except RuntimeError, ex: raise

    def dump(self, withtypes=False):
        """ just dunp the lazydict object. DON'T convert to json. """
        try: return dumpelement(self, withtypes)
        except RuntimeError, ex: handle_exception()

    def fordisplay(self):
        res = self.dump()
        for i in dontshow:
            try: del res[i]
            except KeyError: pass
        return res.tojson()

    def load(self, input):
        """ load from json string. """  
        try: temp = json.loads(input)
        except ValueError:
            handle_exception()
            logging.error("lazydict - can't decode %s" % input)
            return self
        if type(temp) != dict:
            logging.error("lazydict - %s is not a dict" % str(temp))
            return self
        self.update(temp)
        return self

    def snapshot(self):
        pass

    def merge(self, input):
        pass

    def save(self):
        pass

    def writefile(self, filename):
        f = open(filename + ".tmp", 'w')
        f.write(self.tojson())
        f.close()
        os.rename(filename + '.tmp', filename)

    def readfile(self, filename):
        f = open(filename, "r")
        self.update(json.loads(f.read()))


jsontypes = [types.StringType, types.UnicodeType, types.DictType, types.ListType, types.IntType, LazyDict, types.BooleanType]
