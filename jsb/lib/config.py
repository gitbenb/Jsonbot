# jsb/lib/config.py
#
#

""" config module. config is stored as item = JSON pairs. """

## jsb imports

from jsb.utils.trace import whichmodule, calledfrom
from jsb.utils.lazydict import LazyDict
from jsb.utils.exception import handle_exception
from jsb.utils.name import stripname
from datadir import getdatadir
from errors import CantSaveConfig, NoSuchFile, WrongFileName
from jsb.utils.locking import lockdec

## simplejson imports

from jsb.imports import getjson
json = getjson()

## basic imports

import sys
import os
import types
import thread
import logging
import uuid
import thread
import getpass
import copy
import time

## locks

savelock = thread.allocate_lock()
savelocked = lockdec(savelock)

## defines

cpy = copy.deepcopy

## classes

class Config(LazyDict):

    """ 
        config class is a dict containing json strings. is writable to file 
        and human editable.

    """

    def __init__(self, filename, verbose=False, input={}, ddir=None, nolog=False, *args, **kw):
        assert filename
        LazyDict.__init__(self, input, *args, **kw)
        a = "%s%s" % (os.sep, os.sep)
        filename = filename.replace(a, os.sep)
        self.origname = filename
        self.origdir = ddir or getdatadir()
        self.setcfile(ddir or getdatadir(), filename)
        self.jsondb = None
        if not self._comments: self._comments = {}
        logging.info("fromfile - %s from %s" % (self.origname, whichmodule(2)))
        self.fromfile(self.cfile)
        self.origdir = ddir or getdatadir()
        self.setcfile(ddir or getdatadir(), filename)
        self.init()
        if self.owner: logging.info("owner is %s" % self.owner)
        if not self.has_key("uuid"): self.setuuid()
        if not self.has_key("cfile"): self.cfile = self.setcfile(self.origdir, self.origname) 
        assert self.cfile
        if not self.origdir in self.cfile: raise WrongFileName("%s not in %s" % (self.origdir, self.cfile))

    def setcfile(self, ddir, filename):
        self.filename = filename or 'mainconfig'
        self.datadir = ddir or getdatadir()
        self.dir = self.datadir + os.sep + 'config'
        self.cfile = self.dir + os.sep + filename

    def setuuid(self, save=True):
        logging.debug("setting uuid")
        self.uuid = str(uuid.uuid4())
        if save: self.save()

    def __deepcopy__(self, a):
        """ accessor function. """
        cfg = Config(self.filename, input=self, nolog=True)
        return cfg

    def __getitem__(self, item):
        """ accessor function. """
        if not self.has_key(item): return None
        else: return LazyDict.__getitem__(self, item)

    def merge(self, cfg):
        """ merge in another cfg. """
        self.update(cfg)

    def set(self, item, value):
        """ set item to value. """
        LazyDict.__setitem__(self, item, value)

    def fromdb(self):
        """ read config from database. """
        from jsb.lib.persist import Persist
        tmp = Persist(self.cfile)
        logging.debug("fromdb - %s - %s" % (self.cfile, tmp.data.tojson()))
        self.update(tmp.data)

    def todb(self):
        """ save config to database. """
        cp = dict(self)
        del cp['jsondb']
        if not self.jsondb:
            from jsb.lib.persist import Persist
            self.jsondb = Persist(self.cfile)
        self.jsondb.data = cp
        self.jsondb.save()

    def fromfile(self, filename=None):
        """ read config object from filename. """
        curline = ""
        fname = filename or self.cfile
        if not fname: raise Exception(" %s - %s" % (self.cfile, self.dump()))
        if not os.path.exists(fname): logging.warn("config file %s doesn't exist yet" % fname) ; return False 
        comment = ""
        for line in open(fname, 'r'):
            curline = line
            curline = curline.strip()
            if curline == "": continue
            if curline.startswith('#'): comment = curline; continue
            if True:
                try:
                    key, value = curline.split('=', 1)
                    kkey = key.strip()
                    self[kkey] = json.loads(unicode(value.strip()))
                    if comment: self._comments[kkey] = comment 
                    comment = ""
                except ValueError: logging.error("skipping line - unable to parse: %s" % line)
        #self.cfile = fname
        return

    def tofile(self, filename=None, stdout=False):
        """ save config object to file. """
        if not filename: filename = self.cfile
        if not filename: raise Exception("no cfile found  - %s" % whichmodule(3))
        logging.warn("saving %s" %  self.origname)
        if filename.startswith(os.sep): d = [os.sep,]
        else: d = []
        for p in filename.split(os.sep)[:-1]:
            if not p: continue
            d.append(p)
            ddir = os.sep.join(d)
            if not os.path.isdir(ddir):
                logging.debug("persist - creating %s dir" % ddir)
                try: os.mkdir(ddir)
                except OSError, ex:
                    logging.error("persist - not saving - failed to make %s - %s" % (ddir, str(ex)))
                    return
        written = []
        curitem = None
        later = []
        try:
            if stdout: configtmp = sys.stdout
            else: configtmp = open(filename + '.tmp', 'w')
            configtmp.write('# ===========================================================\n#\n')
            configtmp.write("# JSONBOT CONFIGURATION FILE - %s\n" % filename)
            configtmp.write("#\n")
            configtmp.write('# last changed on %s\n#\n' % time.ctime(time.time()))
            configtmp.write("# This file contains configration data for the JSONBOT.\n")
            configtmp.write('# Variables are defined by "name = json value" pairs.\n')
            configtmp.write('# Make sure to use " in strings.\n#\n')
            configtmp.write('# The bot can edit this file!.\n#\n')
            configtmp.write('# ===========================================================\n\n')
            teller = 0
            keywords = self.keys()
            keywords.sort()
            for keyword in keywords:
                value = self[keyword]
                if keyword in written: continue
                if keyword in ['origdir', 'origname', 'issaved', 'blacklist', 'whitelist', 'followlist', 'uuid', 'whitelist', 'datadir', 'name', 'createdfrom', 'cfile', 'filename', 'dir', 'isdb']: later.append(keyword) ; continue
                if keyword == 'jsondb': continue
                if keyword == 'optionslist': continue
                if keyword == 'gatekeeper': continue
                if keyword == "_comments": continue
                if self._comments and self._comments.has_key(keyword):
                    configtmp.write(self._comments[keyword] + u"\n")
                curitem = keyword
                try: configtmp.write('%s = %s\n' % (keyword, json.dumps(value)))
                except TypeError: logging.error("%s - can't serialize %s" % (filename, keyword)) ; continue
                teller += 1
                #configtmp.write("\n")
            configtmp.write('\n\n# ============================================================\n#\n')
            configtmp.write("# bot generated stuff.\n#\n")
            configtmp.write('# ============================================================\n\n')
            for keyword in later:
                if self._comments and self._comments.has_key(keyword):
                    configtmp.write(self._comments[keyword] + u"\n")
                curitem = keyword
                value = self[keyword]
                try: configtmp.write(keyword + " = " + json.dumps(value) + "\n")
                except TypeError: logging.error("%s - can't serialize %s" % (filename, keyword)) ; continue
                teller += 1
                #configtmp.write("\n")
            if not "mainconfig" in filename and self._comments:
                try:
                    configtmp.write('\n\n# ============================================================\n#\n')
                    configtmp.write("# possible other config variables.\n#\n")
                    configtmp.write('# ============================================================\n\n')
                    items = self._comments.keys()
                    keys = self.keys()
                    do = []
                    for var in items:
                        if var not in keys: do.append(var)
                    do.sort()
                    for var in do:
                         configtmp.write(u"# %s -=- %s\n" % (var, self._comments[var]))
                    configtmp.write("\n\n")
                except Exception, ex: handle_exception()
            else: configtmp.write("\n\n# jsonbot can run multiple bots at once. see %s/config/fleet for their configurations.\n\n" % self.origdir)
            if not stdout: 
                configtmp.close()
                os.rename(filename + '.tmp', filename)
            return teller

        except Exception, ex:
            handle_exception()
            logging.error("ERROR WRITING %s CONFIG FILE: %s .. %s" % (self.cfile, str(ex), curitem))

    @savelocked
    def save(self):
        """ save the config. """
        logging.info("save called from %s" % calledfrom(sys._getframe(2)))
        self.issaved = True
        if self.isdb: self.todb()
        else: self.tofile(self.cfile)
     
    def load_config(self, verbose=False):
        """ load the config file. """
        if self.isdb: self.fromdb()
        else: self.fromfile(self.filename)
        self.init()
        if verbose: logging.debug('%s' % self.dump())

    def init(self):
        """ initialize the config object. """
        if not self._comments: self._comments = {}
        if self.filename == 'mainconfig':
            self._comments["whitelist"] = "# - whitelist used to allow ips .. bot maintains this"
            self.setdefault("whitelist", [])
            self._comments["blacklist"] = "# - blacklist used to deny ips .. bot maintains this"
            self.setdefault("blacklist", [])
            self.setdefault('owner', [])
            self._comments["loglist"] = "# - loglist .. maintained by the bot."
            self.setdefault('loglist',  [])
            self._comments["loglevel"] = "# - loglevel of all bots"
            self.setdefault('loglevel',  "warn")
            self._comments["loadlist"] = "# - loadlist .. not used yet."
            self.setdefault('loadlist', [])
            self._comments["quitmsg"] = "# - message to send on quit"
            self.setdefault('quitmsg', "http://jsonbot.googlecode.com")
            self._comments["dotchars"] = "# - characters to used as seperator."
            self.setdefault('dotchars',  ", ")
            self._comments["floodallow"] = "# - whether the bot is allowed to flood."
            self.setdefault('floodallow', 1)
            self._comments["auto_register"] = "# - enable automatic registration of new users."
            self.setdefault('auto_register', 0)
            self._comments["guestasuser"] = "# - enable this to give new users the USER permission besides GUEST."
            self.setdefault('guestasuser', 0)
            self._comments["globalcc"] = "# - global control character"
            self.setdefault('globalcc', "")
            self._comments["app_id"] = "# - application id used by appengine."
            self.setdefault('app_id', "jsonbot")
            self._comments["appname"] = "# - application name as used by the bot."
            self.setdefault('appname', "JSONBOT")
            self._comments["domain"] = "# - domain .. used for WAVE."
            self.setdefault('domain', "")
            self._comments["color"] = "# - color used in the webconsole."
            self.setdefault('color', "")
            self._comments["colors"] = "# - enable colors in logging."
            self.setdefault('colors', "")
            self._comments["memcached"] = "# - enable memcached."
            self.setdefault('memcached', 0)
            self._comments["allowrc"] = "# - allow execution of rc files."
            self.setdefault('allowrc', 0)
            self._comments["allowremoterc"] = "# - allow execution of remote rc files."
            self.setdefault('allowremoterc', 0)
            self._comments['dbenable'] = "# - enable database support"
            self.setdefault('dbenable', 0)
            self._comments['dbtype'] = "# - type of database .. sqlite or mysql at this time."
            self.setdefault('dbtype', 'sqlite')
            self._comments['dbname'] = "# - database name"
            self.setdefault('dbname', "main.db")
            self._comments['dbhost'] = "# - database hostname"
            self.setdefault('dbhost', "localhost") 
            self._comments['dbuser'] = "# - database user"
            self.setdefault('dbuser', "bart")
            self._comments['dbpasswd'] = "# - database password"
            self.setdefault('dbpasswd', "mekker2")
            self._comments['ticksleep'] = "# - nr of seconds to sleep before creating a TICK event."
            self.setdefault('ticksleep', 1)
            self._comments['bindhost'] = "# - host to bind to"
            self.setdefault("bindhost", "")
        self['createdfrom'] = whichmodule()
        if 'xmpp' in self.cfile: self.setdefault('fulljids', 1)
        if 'fleet' in self.cfile:
            self.setdefault('disable', 1)
            self.setdefault("owner", [])
            self.setdefault("user", "")
            self.setdefault("host", "")
            self.setdefault("server", "")
            self.setdefault("ssl", 0)
            self.setdefault("ipv6", 0)
            self.setdefault("channels", [])
        self.setdefault("port", "")
        self.setdefault("password", "")
        self._comments['datadir'] = "# - directory to store bot data in."
        self._comments["owner"] = "# - owner of the bot."
        self._comments["uuid"] = "# - bot generated uuid for this config file."
        self._comments["user"] = "# - user used to login on xmpp networks."
        self._comments["host"] = "# - host part of the user, derived from user var."
        self._comments["server"] = "# - server to connect to (only when different from users host)."
        self._comments["password"] = "# - password to use in authing the bot."
        self._comments["port"] = "# - port to connect to (IRC)."
        self._comments["ssl"] = "# - whether to enable ssl (set to 1 to enable)."
        self._comments["ipv6"] = "# - whether to enable ssl (set to 1 to enable)."
        self._comments["name"] = "# - the name of the bot."
        self._comments["disable"] = "# - set this to 0 to enable the bot."
        self._comments["followlist"] = "# - who to follow on the bot .. bot maintains this list."
        self._comments["networkname"] = "# - networkname .. not used right now."
        self._comments["type"] = "# - the bot's type."
        self._comments["nick"] = "# - the bot's nick."
        self._comments["channels"] = "# - channels to join."
        self._comments["cfile"] = "# - filename of this config file. edit this when you move this file."
        self._comments["createdfrom"] = "# - function that created this config file. bot generated"
        self._comments["dir"] = "# - directory in which this config file lives."
        self._comments["isdb"] = "# - whether this config file lives in the database and not on file."
        self._comments["filename"] = "# - filename of this config file."
        self._comments["username"] = "# - username of the bot."
        self._comments["fulljids"] = "# - use fulljids of bot users (used in non anonymous conferences."
        self._comments["servermodes"] = "# - string of modes to send to the server after connect."
        self._comments["realname"] = "# - name used in the ident of the bot."
        self._comments["onconnect"] = "# - string to send to server after connect."
        self._comments["onconnectmode"] = "# - MODE string to send to server after connect."
        self._comments["realname"] = "# - mode string to send to the server after connect."
        self._comments["issaved"] = "# - whether this config file has been saved. "
        self._comments["origdir"] = "# - original datadir for this configfile. "
        self._comments["origname"] = "# - displayable name of the config file name. "
        return self
        
    def reload(self):
        """ reload the config file. """
        self.load_config()
        return self

def ownercheck(userhost):
    """ check whether userhost is a owner. """
    if not userhost: return False
    if userhost in cfg['owner']: return True
    return False

mainconfig = None

def getmainconfig(ddir=None):
    global mainconfig
    if not mainconfig: mainconfig = Config("mainconfig", ddir=ddir)
    if not mainconfig.has_key("issaved"): mainconfig.save()
    return mainconfig

irctemplate = """# =====================================================
#
# JSONBOT CONFIGURATION FILE - 
#
# last changed on 
#
# This file contains configration data for the JSONBOT.
# Variables are defined by "name = json value" pairs.
# Make sure to use " in strings.
# The bot can edit this file!
#
# =====================================================


# - to enable put this to 0
disable = 1

# - the bot's nick.
nick = "jsb"

# - owner of the bot.
owner = []

# - port to connect to (IRC).
port = 6667

# - server to connect to (on jabber only when different that host.
server = "localhost"

# - the bot's type.
type = "irc"

# - username of the bot.
username = "jsonbot"

# - ssl enabled or not
ssl = 0

# - ipv6 enabled or not 
ipv6 = 0

# - name use in ident of the bot
realname = "jsonbot"

# - string of modes send to the server on connect
servermodes = ""

# =====================================================
#
# bot generated stuff.
#
# =====================================================

"""

xmpptemplate = """# =====================================================
#
# JSONBOT CONFIGURATION FILE - 
#
# last changed on 
#
# This file contains configration data for the JSONBOT.
# Variables are defined by "name = json value" pairs.
# Make sure to use " in strings.
# The bot can edit this file!
#
# =====================================================

# - channels to join
channels = []

# - to enable put this to 0
disable = 1

# - the bot's nick.
nick = "jsb"

# - owner of the bot.
owner = []

# - use fulljids of bot users (used in non anonymous conferences.
fulljids = 1

# password used to auth on the server.
password = ""

# - server to connect to (on jabber only when different that users host.
server = ""

# - the bot's type.
type = "sxmpp"

# - user used to login on xmpp networks.
user = ""

# =====================================================
#
# bot generated stuff.
#
# =====================================================

"""

sleektemplate = """# =====================================================
#
# JSONBOT CONFIGURATION FILE - 
#
# last changed on 
#
# This file contains configration data for the JSONBOT.
# Variables are defined by "name = json value" pairs.
# Make sure to use " in strings.
# The bot can edit this file!
#
# =====================================================

# - channels to join
channels = []

# - to enable put this to 0
disable = 1

# - the bot's nick.
nick = "jsb"

# - owner of the bot.
owner = []

# - use fulljids of bot users (used in non anonymous conferences.
fulljids = 1

# password used to auth on the server.
password = ""

# - server to connect to (on jabber only when different that users host.
server = ""

# - the bot's type.
type = "sleek"

# - user used to login on xmpp networks.
user = ""

# =====================================================
#
# bot generated stuff.
#
# =====================================================

"""

def makedefaultconfig(type, ddir=None):
    filename = 'config'
    datadir = ddir or getdatadir()
    dir = datadir + os.sep + 'config'
    ttype = "default-%s" % type
    cfile = dir + os.sep + "fleet" + os.sep + ttype + os.sep + filename
    logging.warn("creating default config for type %s in %s" % (type, cfile))
    splitted = cfile.split(os.sep)
    mdir = "" 
    for i in splitted[:-1]:
        mdir += "%s%s" % (i, os.sep)
        if not os.path.isdir(mdir): os.mkdir(mdir)
    logging.debug("filename is %s" % cfile)
    f = open(cfile, "w")
    if type == "irc": f.write(irctemplate) ; f.close()
    elif type == "sxmpp": f.write(xmpptemplate) ; f.close()
    elif type == "sleek": f.write(sleektemplate) ; f.close()
    else: raise Exception("no such bot type: %s" % type)
