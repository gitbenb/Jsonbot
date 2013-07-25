# jsb/lib/O.py
#
#

"""

    -=- O.py

"""

## =============
## BASIC IMPORTS 
## =============

import collections
import traceback
import threading
import datetime
import getpass
import logging
import hashlib
import optparse
import thread
import random
import socket
import string
import fcntl
import types
import errno
import Queue
import uuid
import json
import time
import imp
import sys
import os
import re

## ======= 
## defines 
## ======= 

basic_types= [ str, int, float, bool, None]

__version__ = 0.2

""" shining bright. """

## ============
## SHELL COLORS
## ============

ERASE_LINE = '\033[2K'
BOLD='\033[1m'     
RED = '\033[91m'   
YELLOW = '\033[93m'
GREEN = '\033[92m' 
BLUE = '\033[94m'
BLA = '\033[95m'
ENDC = '\033[0m'

## =========
## VARIABLES
## =========

homedir = os.path.expanduser("~")

# check wether ocontrib is available

if os.path.isdir("contrib"): sys.path.append("contrib")

## ===============
## OPTION HANDLING 
## ===============

## make_opts function

def make_opts():
    parser = optparse.OptionParser(usage='usage: %prog [options]', version=make_version())
    for option in options:
        type, default, dest, help = option[2:]
        if "store" in type:
            try: parser.add_option(option[0], option[1], action=type, default=default, dest=dest, help=help)
            except Exception as ex: logging.error("error: %s - option: %s" % (str(ex), option)) ; continue
        else:
            try: parser.add_option(option[0], option[1], type=type, default=default, dest=dest, help=help)
            except Exception as ex: logging.error("error: %s - option: %s" % (str(ex), option)) ; continue
    # return a (opts, args) pair
    return parser.parse_args()

## ==========
## EXCEPTIONS
## ==========

class Error(BaseException): pass

class OverloadError(Error): pass

class MissingArgument(Error): pass

class MissingOutFunction(Error): pass

class NoText(Error): pass

class NoEvent(Error): pass

class SignatureError(Error): pass

class RemoteDisconnect(Error): pass

## smooth function

def smooth(a):
    if type(a) not in basic_types: return get_name(a)
    else: return a

## get_timed function

def get_timed(ttime=None): return j(today(), hms(ttime or time.time()))

## get_day function

def get_day(ttime=None): return today(ttime)

## get_hms function

def get_hms(ttime=None): return hms(ttime)

## get_stamp function

def get_stamp(ttime=None): return stamp(ttime)

## ==========
## CORE STUFF
## ==========

## Big O class

class O(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, **kwargs)
        if args: self._value = args[0]
        
    def __getattribute__(self, *args, **kwargs):
        name = args[0]
        if name == "what": return get_clsname(self)
        if name == "modname": return called_from(2)
        if name == "typed": return str(type(self))
        if "_value" in self: return self["_value"].__getattribute__(*args, **kwargs)
        else: return dict.__getattribute__(self, *args, **kwargs)

    def __getattr__(self, name):
        try: return self[name]
        except KeyError:
            if name == "tags": self["tags"] = []
            if name == "cbtype": self["cbtype"] = self.what
            if name == "ctime": self["ctime"] = time.time()
            if name == "day": self["day"] = get_day(self.ctime)
            if name == "time": self["time"] = get_hms(self.ctime)
            if name == "stamp": self["stamp"] = get_stamp(self.ctime)
            if name == "_target":
                from jsb.drivers.console.bot import ConsoleBot
                return ConsoleBot()
            if name == "result": self["result"] = O()
        try: return self[name]
        except KeyError: return ""

    def __setattr__(self, name, value): return dict.__setitem__(self, name, value)

    def __exists__(self, a):
        try: return self[a]
        except KeyError: False

    def __lt__(self, a): return self.ctime < a.ctime

    def save(self, *args, **kwargs): return self.save_file(self.get_path())

    def save_list(self, *args, **kwargs):
        slist = args[0]
        for fn in slist: self.save_file(self.get_filename(fn))

    def save_file(self, *args, **kwargs):
        path = args[0]
        logging.warn("save %s" % path)
        todisk = O()
        todisk.data = self.reduced()
        todisk.create_type = self.typed
        todisk.modname = self.modname
        todisk.version = __version__
        try: result = todisk.make_json(indent=2)
        except TypeError: raise NoJSON(todisk)
        todisk.signature = make_signature(result)
        make_dir(path)
        datafile = open(path + ".tmp", 'w')
        fcntl.flock(datafile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        datafile.write(headertxt % (self.get_path(), __version__, "%s characters" % len(result)))
        datafile.write(result)
        datafile.write("\n")
        fcntl.flock(datafile, fcntl.LOCK_UN)
        datafile.close()
        os.rename(path + ".tmp", path)
        return self

    def get_tags(self):
        result = []
        if self.txt:
            for arg in self.txt.split():
                if arg.startswith("#"): result.append(arg)
        return result

    def get_root(self): return j(homedir, config.workdir, "")

    def get_module(self): return mj(self.modname or "core", self.what)

    def get_local(self): return dj(mj(self.time, self.stamp), self.get_module(), self.cbtype)

    def get_mark(self): return j(self.day, self.get_local())

    def get_path(self): return j(self.get_root(), self.get_mark())

    def get_filename(self, fn): return j(self.get_root(), mj(self.get_mark(), fn))

    def get_typed(self): return mj(self.__module__, self.__class__)

    def get_typednames(self, typed=None, want=""):
        res = []
        for name in self.names(want):
            value = self[name]
            try: bases = type(value).__bases__
            except AttributeError: continue
            if typed and typed not in bases: continue
            res.append(value)
        return res

    def get_fn(self, want="", exclude="", *args, **kwargs):
        path = self.get_path()
        if not os.path.isdir(path): return    
        for fn in os.listdir(path):
            if not fn: continue
            if exclude and fn.startswith(exclude): continue
            if want and want not in fn: continue
            yield(fn)

    def add(self, value): self.result[time.time()] = value

    def remove(self, ttime): del self[ttime]

    def prepare(self):
        try: self.first, self.rest = self.txt.split(" ", 1)
        except: self.first = self.txt
        if self.rest: self.args = self.rest.split()
        if self.first and self.first[0] == ".": self.user_cmnd = self.first[1:]

    def ready(self):
        self._ready = self._ready or threading.Event()
        self._ready.set()

    def wait(self, sec=3.0):
        self._ready = self._ready or threading.Event()
        self._ready.wait(sec)
        return self

    def show(self):
        return ["%s=%s" % (a, b) for a, b in self.items() if b]

    def show_me(self, sep):
        return sep.join(self.show())

    def register(self, *args, **kwargs):
        name = args[0]
        obj = args[1]
        logging.warn("register %s.%s" % (name, get_name(obj)))
        self[name] = obj

    def names(self, want=""):
        for key in self.keys():
            k = str(key)
            if k.startswith("_"): continue
            if want and want not in k: continue
            yield key

    def reduced(self):
        res = O()
        for name in self.names():
            if name in ["args", "rest", "first"]: continue
            res[name] = self[name]
        return res

    def make_json(self, *args, **kwargs): return json.dumps(self.reduced(), default=smooth, *args, **kwargs)

    def make_full(self, *args, **kwargs): return json.dumps(self, default=smooth, *args, **kwargs)

    def make_signature(self, sig=None): return str(hashlib.sha1(bytes(str(sig or self), "utf-8")).hexdigest())

    def objects(self, *args, **kwargs):
        path = self.get_root()
        if args: path = j(path, args[0])
        res = []
        for fn in os.listdir(path):
            fnn = j(path, fn)
            if os.path.isdir(fnn): res.extend(self.objects(fnn)) ; continue
            obj = O().load_file(fnn)
            res.append(obj)
        return res

    def read(self, *args, **kwargs):
        logging.debug("read %s" % args[0])
        path = args[0]
        try: f = open(path, "r")
        except IOError as ex:
            if ex.errno == errno.ENOENT: return "{}"
            raise
        if self.do_test: f.line_buffering = False
        res = ""
        for line in f:
            if not line.strip().startswith("#"): res += line
        if not res.strip(): return "{}"
        f.close()
        return res

    def load(self, *args, **kwargs):
        if args: path = args[0]
        else: path = j(self.get_path(), self.latest())
        return self.load_file(path)

    def load_file(self, *args, **kwargs):
        path = args[0]
        ondisk = self.read(path) 
        fromdisk = json.loads(ondisk)
        if "signature" in fromdisk:
            if self.make_signature(fromdisk["data"]) != fromdisk["signature"]: raise SignatureError(path)
        if "data" in fromdisk: self.update(fromdisk["data"])
        return self

    def latest(self):
        last = 0
        latest_fn = ""
        for fn in self.get_fn():
            try: t = float(fn.split(os.sep)[-1])
            except: logging.debug("no time in %s" % fn) ; continue
            if t > last: latest_fn = fn ; last = t
        logging.info("last detected time is %s" % time.ctime(last))
        return latest_fn

    def reply(self, txt): self.add(txt)

    def done(self, txt=None): self.ready()

    def direct(self, txt):
        try: self._target.say(self.channel or self.origin, txt)
        except: error()

    def raw(self, txt):
        try: self._target._raw(txt)
        except: error()

    def say(self, channel, txt): self._target.say(channel, txt)

    def display(self, *args, **kwargs):
        try: target = args[0]
        except IndexError: target = self.result
        keytype = [float, ]
        try: keys = sorted(target.keys())
        except AttributeError: self.direct(target) ; return
        for key in keys:
            if type(key) not in keytype: continue
            self.say(self.channel, target[key])

    def make_xmpp(self):
        import sleekxmpp
        from sleekxmpp.xmlstream.tostring import xml_escape
        res = dict(self)
        try: del res["from"]
        except: pass
        elem = self['element']
        main = "<%s" % self['element']
        for attribute in attributes[elem]:
            if attribute in res:
                if res[attribute]: main += " %s='%s'" % (attribute, xml_escape(stripbadchar(str(res[attribute]))))
                continue
        main += ">"
        if "xmlns" in res: main += "<x xmlns='%s'/>" % res["xmlns"] ; gotsub = True
        else: gotsub = False
        if 'html' in res:   
            if res['html']: 
                main += '<html xmlns="http://jabber.org/protocol/xhtml-im"><body xmlns="http://www.w3.org/1999/xhtml">%s</body></html>' % res['html']
                gotsub = True
        if 'txt' in res:     
            if res['txt']:
                txt = res['txt']   
                main += "<body>%s</body>" % stripbadchar(xml_escape(txt))
                gotsub = True
        for subelement in subelements[elem]:   
            if subelement == "body": continue  
            if subelement == "thread": continue
            try:
                data = res[subelement]
                if data:
                    try:
                        main += "<%s>%s</%s>" % (subelement, xml_escape(data), subelement)
                        gotsub = True
                    except AttributeError as ex: logging.warn("skipping %s" % subelement)
            except KeyError: pass
        if gotsub: main += "</%s>" % elem
        else: main = main[:-1] ; main += " />"
        return main

## Collection class

class Collection(O):

    def find(self, search):
       result = []
       for item in self.objects():
           if search in item.txt: result.append(item)
       return result

## ============================
## TASK RELATED STUFF (THREADS)
## ============================

## TaskRunner class

class TaskRunner(threading.Thread):

    count_threads = 0

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, None, self._loop, "thread.%s" % str(time.time()), args, kwargs)
        self.setDaemon(True)
        self._queue = Queue.Queue()
        self._state = "idle"

    def _loop(self):
        self._state = "running"
        while self._state in ["running", "idle", "callback"]:
            try: args, kwargs = self._queue.get()
            except IndexError: error() ; time.sleep(0.1) ; continue
            try:
                task = args[0]
                logging.debug("got task %s" % task.get_local())
                if self._state == "stop": break
                task._state = "dispatch"
                task.dispatch()
                task._state = "callback"
                cb.handle_cb(*args, **kwargs)
                task._state = "display"
                task.display()
                task._state = "idle"
                task.ready()
            except: error()
        logging.warn("stopping loop (%s)" % self._state)

    def put(self, *args, **kwargs):
        self._state = "running"
        self._queue.put((args, kwargs))
        return 

    def stop(self):
        logging.warn("stopping %s in %s state" % (self.name, self._state))
        self._state = "stop"

## dynamically grow threads where needed 

class Dispatcher(O):

    max = 50
    runners = collections.deque() 

    def stop(self, name=None):
        for taskrunner in self.runners:
            if name and name not in taskrunner.name: continue
            taskrunner.stop()

    def put(self, *args, **kwargs):
        if not args: raise NoTask()
        logging.debug("put %s" % str(args[0]))
        target = self.get_target()
        target.put(*args, **kwargs)
        return args[0]

    def get_target(self):
        target = None
        for taskrunner in self.runners:
            if taskrunner._queue and taskrunner._state == "idle": target = taskrunner
        if not target: target = self.makenew()
        return target

    def makenew(self, *args, **kwargs):
        if len(self._runners) < self.max:
            taskrunner = TaskRunner(*args, **kwargs)
            taskrunner.start()
            self.runners.append(taskrunner)
        else: taskrunner = random.choice(self._runners)
        return taskrunner

    def cleanup(self, dojoin=False):
        todo = []
        for taskrunner in self.runners:
            if taskrunner.stopped or not len(taskrunner.queue): todo.append(taskrunner)
        for taskrunner in todo: taskrunner.stop()
        for taskrunner in todo: self.runners.remove(taskrunner)

## =============
## BASIC CLASSES
## =============

## Event class

class Event(O): 

    def dispatch(self, *args, **kwargs):
        if self.no_dispatch: logging.debug("no dispatch set") ; return
        self.prepare()
        if args: cmnd = args[0]
        else: cmnd = self.user_cmnd
        if not cmnd: logging.debug("no cmnd found") ; return
        try: func = cmnds[cmnd]
        except KeyError: logging.debug("no %s cmnd" % cmnd) ; return
        self.how = get_name(func)
        logging.debug("dispatch %s -=- %s -=- %s" % (cmnd, self.how, self.show()))
        if not self._status: self._status = O()
        try:  res = func(self, **kwargs) ; self._status.add(res)
        except: error()
        return self

## Bot class

class Bot(Dispatcher): 

    def connect(self, *args, **kwargs): pass

    def _raw(self, *args, **kwargs): pass

    def exit(self, *args, **kwargs): pass

    def say(self, *args, **kwargs): pass

    def get_one(self): pass

    def read_some(self): pass

    def handle_once(self, *args, **kwargs):
        if args: event = args[0]
        else: event = self.get_one()
        logging.debug("got event %s" % str(event))
        event._target = self
        self.put(event)
        event.wait()

    def run(self, *args, **kwargs):
        logging.warn("starting %s" % get_clsname(self))
        self.wait()
        try: self.connect()
        except socket.gaierror: error() ; self._state = "error"
        else: self._state = "running"
        while self._state in ["running", "callback", "idle", "empty", "once"]:
            try: self.handle_once()
            except (KeyboardInterrupt, EOFError): pass
            except RemoteDisconnect: break
            except: error()
        logging.warn("stopping %s (%s)" % (self.what, self._state))

## Plugin class

class Plugins(O):

    def get_names(self, plugsdir): return [x[:-3] for x in os.listdir(plugsdir) if x.endswith(".py")] 

    def load_plugs(self):
        p, fn = os.path.split(os.path.abspath(__file__))
        path, fn = os.path.split(os.path.abspath(p))
        plugsdir = j(path, "plugs", "O")
        logging.info("loading plugins from %s" % plugsdir)
        for plugname in self.get_names(plugsdir):
            if "__" in plugname: continue
            try: mod = self.load_mod(plugname, plugsdir, force=True)
            except: error() ; continue

    def load_mod(self, plugname, pdir="", force=False):
        logging.warn("load %s.%s" % (self.what, plugname))
        if plugname in self:
            if not force: return self[plugname]
            self[plugname] = imp.reload(self[plugname])
        else:
            if not pdir: pdir = j(self.root, "plugs")
            search = imp.find_module(plugname, [pdir,])
            self[plugname] = imp.load_module(plugname, *search)
        self.plug_exec(plugname, "init")
        return self[plugname]

    def plug_exec(self, plugname, item): 
        try: todo = getattr(self[plugname], item) ; todo()
        except AttributeError: logging.debug("can't find %s in %s" % (item, plugname))
 
    def unload(self, plugname):
        self.plug_exec(plugname, "shutdown")
        del self[plugname]

    def reload(self, plugname, force=False):
        self.unload(plugname)
        mod = self.load_mod(plugname, force)
        return mod

## Fleet class

class Fleet(O):

    def start(self, *args, **kwargs):
        event = Event()
        if args:
            config = args[0]
            event.txt = "."
            for arg in config.args:
                event.txt += "%s " % arg
        if not self.bots: self.bots = []
        for bot in self.get_typednames(Bot):
            try: thread.start_new_thread(bot.run, ())
            except: error()
            self.bots.append(bot)
            if event.txt: bot.put(event)
        if self.bots and "once" not in kwargs:
            logging.warn("bots in fleet: %s" % ", ".join([get_clsname(bot) for bot in self.bots]))
            logging.warn("")
            logging.warn("R E A D Y")
            logging.warn(" ")
            logging.warn("commands are: %s" % ", ".join(cmnds.keys()))
            for bot in self.bots: bot.ready()
            while 1:
                try: time.sleep(1)
                except KeyboardInterrupt: break
                except Exception: error() ; break
        shutdown()

    def exit(self):
        for bot in self.bots:
            try: bot.exit()
            except AttributeError: continue
            except: error()

## Config class

class Config(O): pass

## Commands class

class Commands(O): pass

## Callbacks class

class Callbacks(Dispatcher):

    def register(self, cbtype, cb):
        logging.warn("register %s.%s" % (cbtype, get_name(cb)))
        if cbtype not in self: self[cbtype] = []
        self[cbtype].append(cb)

    def handle_cb(self, *args, **kwargs):
        event = args[0]
        event.prepare()
        logging.debug("cb %s" % event.cbtype or event.what)
        functions = []
        try: functions = self["ALL"]
        except KeyError: pass
        try: functions.extend(self[event.cbtype or event.what])
        except KeyError: pass
        for func in functions:
            try: pre = getattr(func, "pre")
            except AttributeError: pre = None
            if pre and not pre(event): logging.debug("pre failed on %s" % str(func)) ; return
            try: result = func(event) ; self.how = get_name(func)
            except: error()
        event.ready()
        return event

## get_classes function

def get_classes(mod):
    module = __import__(mod, fromlist=[mod,])
    res = O()
    for name in dir(module):
        obj = getattr(module, name)
        t = str(type(obj))
        if "class" in t: res.register(t, type(obj))
    return res

## =========
## GREETINGS
## =========

## make_version function

def make_version(): return "%sBOTJE v%s   -=- %s%s" % (RED, __version__, time.ctime(time.time()), ENDC)

## hello function

def hello(): print(make_version() + "\n")

## ==========
## start/stop
## ==========

## boot function

def Oboot():
    print("")
    global config
    try: config.opts, config.args = make_opts()
    except SystemExit: os._exit(1)
    config.update(vars(config.opts))
    for arg in config.args:
        try: var, val = arg.split("=") ; config[var] = val ; continue
        except ValueError: pass
    if config.do_local: config.workdir = j(os.getcwd(), "odata") 
    if not config.workdir: config.workdir = "odata"
    make_dir(config.workdir)
    if not config.loglevel: config.loglevel = "error"
    log_config(config.loglevel)
    if config.loglevel:
        logging.warn("C O N F I G")
        logging.warn("")
        for line in config.show():
            logging.warn(line)
        logging.warn("")
    if config.loglevel:
        logging.warn("B O O T")
        logging.warn("")
    set_core()
    plugins.load_plugs()
    return config

## shutdown function

def shutdown():
    print("")
    logging.warn("shutdown has arrived")
    fleet.exit()
    os._exit(0)

## +++++++++++++++++++++
## BASIC RUNTIME OBJECTS
## +++++++++++++++++++++

cb = Callbacks()
cmnds = Commands()
fleet = Fleet()
config = Config()
plugins = Plugins()

## core holder

core = O()

def set_core():
    core.register("cb", cb)
    core.register("cmnds", cmnds)
    core.register("fleet", fleet)
    core.register("config", config)
    core.register("plugins", plugins)

## =========
## CONSTANTS
## =========

attributes = {}
subelements = {}

attributes['message'] = ['type', 'from', 'to', 'id']
subelements['message'] = ['subject', 'body', 'error', 'thread', 'x']

attributes['presence'] = ['type', 'from', 'to', 'id']
subelements['presence'] = ['show', 'status', 'priority', 'x']


attributes['iq'] = ['type', 'from', 'to', 'id']
subelements['iq'] = ['query', 'error']

## ===========
## DEFINITIONS
## ===========

## time related 

timere = re.compile('(\S+)\s+(\S+)\s+(\d+)\s+(\d+):(\d+):(\d+)\s+(\d+)')
bdmonths = ['Bo', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

## dir manipulation variables

dirmask = 0o700 
filemask = 0o600
allowedchars = string.ascii_letters + string.digits + "_,-. \n" + string.punctuation

options = [
              ('-a', '--api', 'store_true', False, 'api',  "enable api server"),
              ('-t', '--test', 'store_true', False, 'do_test',  "enable test mode"),
              ('', '--local', 'store_true', False, 'do_local',  "use local directory as the working directory"),
              ('', '--apiport', 'string', "", 'apiport', "port on which the api server will run"),
              ('-d', '--dir', 'string', "", 'workdir',  "directory to work with"),   
              ('-l', '--loglevel', 'string', "", 'loglevel',  "loglevel"),
              ('-c', '--channel', 'string', "", 'channel',  "channel"),
          ]

## ==================
## SIGNATURE FUNCTION
## ==================

def make_signature(data): return str(hashlib.sha1(bytes(str(data))).hexdigest())

## ===============
## ERROR FUNCTIONS
## ===============

def error(*args, **kwargs):
    msg = exceptionmsg()
    logging.error("error detected:\n\n%s\n" % msg)
    return msg

## exceptionmsg function

def exceptionmsg(*args, **kwargs):
    exctype, excvalue, tb = sys.exc_info()
    trace = traceback.extract_tb(tb)
    result = ""
    for i in trace:
        fname = i[0]
        linenr = i[1]
        func = i[2]  
        plugfile = fname[:-3].split(os.sep)
        mod = []
        for i in plugfile[::-1]: mod.append(i)
        ownname = '.'.join(mod[::-1])
        result += "%s:%s %s | " % (ownname, linenr, func)
    del trace
    return "%s%s: %s" % (result, exctype, excvalue)

## ===============
## PRIMARY HELPERS
## ===============

## isvar function

def isO(obj): return isinstance(obj, O) 

## splitted function

def stripped(input):
    try: return input.split("/")[0]
    except: return input

## get_subs function

def get_subs(input, regex): return re.findall(regex, input)

## get_method function

def get_method(obj):
    txt = str(obj)
    return ".".join(get_subs(txt, "method (.*?) of"))

## get_classfromstring function

def get_clsfromstring(typestr):
    subs = get_subs(typestr, "'(.*?)'")
    return subs[0].split(".")[-1]

## get_clsname function

def get_clsname(obj):
    name = get_name(obj)
    return name.split(".")[-1]

## get_name function - retrieve usable name from repr

def get_name(obj):
    txt = str(obj)
    res = ".".join(get_subs(txt, "(method .*?) of"))
    if not res: res = ".".join(get_subs(txt, "(function .*?) at"))
    if not res: txt = str(type(obj)) ; res = ".".join(get_subs(txt, "'(.*?)'"))
    return res.replace(" ", ".")

## j function - joining lists into paths

def j(*args):
     if not args: return
     todo = list(map(str, filter(None, args)))
     return os.path.join(*todo)

def mj(*args):
     if not args: return
     todo = list(map(str, filter(None, args)))
     return os.path.join(*todo).replace(os.sep, ".")

def dj(*args):
     if not args: return
     todo = list(map(str, filter(None, args)))
     return os.path.join(*todo).replace(os.sep, "-")

## aj function - absolute paths

def aj(sep=None, *args): return os.path.abspath(*j(sep, *args))

## =================
## RESOLVE FUNCTIONS
## =================

## resolve_ip function

def resolve_ip(hostname=None, timeout=1.0):
    oldtimeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try: ip = socket.gethostbyname(hostname or socket.gethostname())
    except socket.timeout: ip = None
    socket.setdefaulttimeout(oldtimeout)
    return ip

## resolve_host function

def resolve_host(ip=None, timeout=1.0):
    """ determine the ip address we are running on, we use this for creatin an id. """
    oldtimeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try: host = socket.gethostbyaddr(ip or resolve_ip())[0]
    except socket.timeout: host = None
    socket.setdefaulttimeout(oldtimeout)
    return host

## ===================
## DIRECTORY FUNCTIONS
## ===================

## touch function

def touch(fname):
    try: fd = os.open(fname, os.O_RDONLY | os.O_CREAT) ; os.close(fd)
    except: error()

## check_permission function

def check_permissions(ddir, dirmask=dirmask, filemask=filemask):
    uid = os.getuid()
    gid = os.getgid()
    try: stat = os.stat(ddir)
    except OSError: make_dir(ddir) ; stat = os.stat(ddir) 
    if stat.st_uid != uid: os.chown(ddir, uid, gid)
    if os.path.isfile(ddir): mask = filemask
    else: mask = dirmask
    if stat.st_mode != mask: os.chmod(ddir, mask)

## make_dir function

def make_dir(path):
    if not path.endswith(os.sep): path, fn = os.path.split(path)
    target = os.sep
    for item in path.split(os.sep):
        if not item: continue
        target = j(target, item, "")
        if not os.path.isdir(target):
            try:
                os.mkdir(target)
                check_permissions(target)
            except OSError as ex: logging.debug(ex) ; continue 
    return path

## ====================
## STACKFRAME FUNCTIONS
## ====================

## dump_frame function

def dump_frame(search="code"):
    result = {}
    frame = sys._getframe(1)
    search = str(search)
    for i in dir(frame):
        if search in i:
            target = getattr(frame, i)
            for j in dir(target):
                result[j] = getattr(target, j)
    return result

## called_from function

def called_from(level=2):
    """ walk the callstack until string is found. stop when toplevel wtf package is found. """
    result = ""  
    loopframe = sys._getframe(level)
    if not loopframe: return result
    marker = ""
    pre = "core"
    while 1:
        try: back = loopframe.f_back
        except AttributeError: break
        if not back: break
        filename = back.f_code.co_filename
        if "plugs" in filename: result = filename.split(os.sep)[-1][:-3] ; pre = "plugs" ; break
        loopframe = back
    del loopframe   
    if result: return "%s.%s" % (pre, result)

## =============
## FILE LOCATION
## =============

## get_source function

def get_source(mod):
    """ return the directory a module is coming from. """
    if not os.getcwd() in sys.path: sys.path.insert(0, os.getcwd())
    source = None
    splitted = mod.split(".")
    if len(splitted) == 1: splitted.append("")
    thedir, file = os.path.split(mod.replace(".", os.sep))
    if os.path.isdir(thedir): source = thedir
    if source and os.path.exists(source): logging.info("source is %s" % source) ; return source
    if not source:
        try: import pkg_resources
        except (ImportError, ValueError): import wtf.contrib.pkg_resources
        source = p.resource_filename()
    logging.info("source is %s" % source)
    return source

## ==============
## FILENAME STUFF
## ==============

## stripbadchar function

def stripbadchar(s): return "".join([c for c in s if ord(c) > 31 or c in allowedchars])

## enc_char function

def enc_char(s):
    result = []
    for c in s:
        if c in allowedchars: result.append(c)
        else: result.append(enc_name(c))
    return "".join(result)

## enc_needed function

def enc_needed(s): return [c for c in s if c not in allowedchars]

## enc_name function

def enc_name(input): return str(base64.urlsafe_b64encode(bytes(input, "utf-8")), "utf-8")

## split_txt function - make portions 

def split_txt(what, l=375):
    txtlist = []
    start = 0
    end = l
    length = len(what)
    for i in range(int(length/end+1)):
        starttag = what.find("</", end)
        if starttag != -1: endword = what.find('>', end) + 1
        else:
            endword = what.find(' ', end)
            if endword == -1: endword = length
        res = what[start:endword]
        if res: txtlist.append(res)
        start = endword
        end = start + l
    return txtlist

## lock_dec function

def lock_dec(lock):
    def locked(func):
        """ locking function """
        def lockedfunc(*args, **kwargs):
            """ the locked function. """
            lock.acquire()
            try: return func(*args, **kwargs)
            finally: lock.release()

        return lockedfunc

    return locked

## completa function

completions = {}

def completer(text, state):
    try: matches = completions[text]
    except KeyError: matches[state] = cmnds.list_keys(want=text)
    try: return matches[state]
    except: return None

## =====================
## TIME RELATED FUCTIONS
## =====================

## striptime function

def striptime(what):  
    what = str(what)
    what = re.sub('\d+-\d+-\d+', '', what)
    what = re.sub('\d+-\d+', '', what)
    what = re.sub('\d+:\d+', '', what)
    what = re.sub('\s+', ' ', what)
    return what.strip()  

## now function

def now():
    if time.daylight: ttime = time.ctime(time.time() + int(time.timezone) + 3600)
    else: ttime = time.ctime(time.time() + int(time.timezone))
    return ttime

## stamp function

def stamp(timestamp=None):
    now = datetime.datetime.now()
    return str(now.microsecond)

## hms function

def hms(timestamp=None):
    now = datetime.datetime.now()
    return "%s:%s:%s" % (now.hour, now.minute, now.second)

## today function

def today(timestamp=None):
    if time.daylight: ttime = time.ctime(timestamp or time.time() + int(time.timezone) + 3600)
    else: ttime = time.ctime(timestamp or time.time() + int(time.timezone))
    matched = re.search(timere, ttime)
    if matched: return "%s-%s-%s" % (matched.group(3), matched.group(2), matched.group(7))

## today_stamp function

def today_stamp(timestamp=None):
    if time.daylight: ttime = time.ctime(time.time() + int(time.timezone) + 3600)
    else: ttime = time.ctime(time.time() + int(time.timezone))
    matched = re.search(timere, ttime)
    if matched:
        temp = "%s %s %s" % (matched.group(3), matched.group(2), matched.group(7))
        timestring = time.strptime(temp, "%d %b %Y")
        result = time.mktime(timestring)
        return result

## strtorepeate function

def strtorepeat(what):
    splitted = what.split()
    for s in splitted:
        try: repeat = int(s[1:]) ; return repeat
        except: pass

## strtotime function

def strtotime(what):
    daymonthyear = 0
    hoursmin = 0
    try:
        dmyre = re.search('(\d+)-(\d+)-(\d+)', str(what))
        if dmyre:
            (day, month, year) = dmyre.groups()
            day = int(day)
            month = int(month)
            year = int(year)
            if day <= calendar.monthrange(year, month)[1]:
                date = "%s %s %s" % (day, bdmonths[month], year)
                daymonthyear = time.mktime(time.strptime(date, "%d %b %Y"))
            else: return None
        else:
            dmre = re.search('(\d+)-(\d+)', str(what))
            if dmre:
                year = time.localtime()[0]
                (day, month) = dmre.groups()
                day = int(day)
                month = int(month)
                if day <= calendar.monthrange(year, month)[1]: 
                    date = "%s %s %s" % (day, bdmonths[month], year)
                    daymonthyear = time.mktime(time.strptime(date, "%d %b %Y"))
                else: return None
        hmsre = re.search('(\d+):(\d+):(\d+)', str(what))
        if hmsre:
            (h, m, s) = hmsre.groups()
            h = int(h)
            m = int(m)
            s = int(s)
            if h > 24 or h < 0 or m > 60 or m < 0 or s > 60 or s < 0: return None
            hours = 60 * 60 * (int(hmsre.group(1)))
            hoursmin = hours  + int(hmsre.group(2)) * 60
            hms = hoursmin + int(hmsre.group(3))
        else:
            hmre = re.search('(\d+):(\d+)', str(what))
            if hmre:
                (h, m) = hmre.groups()
                h = int(h)
                m = int(m)
                if h > 24 or h < 0 or m > 60 or m < 0: return None
                hours = 60 * 60 * (int(hmre.group(1)))
                hms = hours  + int(hmre.group(2)) * 60
            else: hms = 0
        if not daymonthyear and not hms: return None
        if daymonthyear == 0: heute = today()
        else: heute = daymonthyear
        return heute + hms
    except Exception: error()

## headertxt variable

headertxt = '''# %s
#
# this is a botlib (v%s) file, %s
#
# botlib can edit this file !!

'''

## runtime logging variables

logfilter = ["looponce", "PING", "PONG"]
logplugs = []

## defines

datefmt = BOLD + BLUE + '%H:%M:%S' + ENDC
format = "%(asctime)-8s -=- %(message)-84s -=- (%(module)s.%(lineno)s)" 
format_small = "%(asctime)-8s -=- %(message)-84s"

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'warn': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL
        }

## Formatter class

class Formatter(logging.Formatter):

     """ hooks into the logging system. """

     def format(self, record):
        target = str(record.msg)
        if not target: target = " "
        if target[0] in [">", ]: target = "%s%s%s%s" % (RED, target[0], ENDC, target[1:])
        elif target[0] in ["<", ]: target = "%s%s%s%s" % (GREEN, target[0], ENDC, target[1:])
        else: target = "%s%s%s %s" % (GREEN, "!", ENDC, target)
        record.msg = "%s" % target
        return logging.Formatter.format(self, record)

## MyFilter class

class Filter(logging.Filter):

    def filter(self, record):
        for f in logfilter:
            if f in record.msg: return False
        for modname in logplugs:
            if modname in record.module: record.levelno = logging.WARN ; return True
        return True

## provide a factory function returning a logger ready for use

def log_config(loglevel):
    """ return a properly configured logger. """
    logger = logging.getLogger("")
    formatter = Formatter(format, datefmt=datefmt)
    formatter_short = Formatter(format_small, datefmt=datefmt)
    level = LEVELS.get(str(loglevel).lower(), logging.NOTSET)
    filehandler = None
    logger.setLevel(level)
    if logger.handlers:
        for handler in logger.handlers: logger.removeHandler(handler)
    try: filehandler = logging.handlers.TimedRotatingFileHandler(j(homedir, "ologs", "botlib.log"), 'midnight')
    except: pass
    ch = logging.StreamHandler()
    ch.setLevel(level)
    if level < logging.WARNING: ch.setFormatter(formatter)
    else: ch.setFormatter(formatter_short)
    ch.addFilter(Filter())
    logger.addHandler(ch)
    if filehandler:
        filehandler.setLevel(level)
        logger.addHandler(filehandler)
    return logger
