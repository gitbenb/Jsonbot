# jsb/utils/generic.py
#
#

""" generic functions. """

## lib imports 

from exception import handle_exception
from trace import calledfrom, whichmodule
from lazydict import LazyDict
from jsb.imports import getjson
json = getjson()

## generic imports

from stat import ST_UID, ST_MODE, S_IMODE
import time
import sys
import re
import getopt
import types
import os
import os.path
import random
import Queue 
import logging
import StringIO

## istr class

class istr(str):
    pass   

## fix_format function

def fix_format(s):
    counters = {
        chr(2): 0,
        chr(3): 0
        }
    for letter in s:
        if letter in counters:
            counters[letter] += 1
    for char in counters:
        if counters[char] % 2:
            s += char
    return s


## isdebian function

def isdebian():
    """ checks if we are on debian. """
    return os.path.isfile("/etc/debian_version")

## isjsbuser function

def botuser():
    """ checks if the user is jsb. """
    try:
        import getpass
        return getpass.getuser() 
    except ImportError: return ""

## checkpermission function

def checkpermissions(ddir, umode):
    """ see if ddir has umode permission and if not set them. """
    try:
        uid = os.getuid()
        gid = os.getgid()
    except AttributeError: return
    try: stat = os.stat(ddir)
    except OSError: return
    if stat[ST_UID] != uid:
        try: os.chown(ddir, uid, gid)
        except: pass
    if S_IMODE(stat[ST_MODE]) != umode:
        try: os.chmod(ddir, umode)
        except: handle_exception()

## jsonstring function

def jsonstring(s):
    """ convert s to a jsonstring. """
    if type(s) == types.TupleType: s = list(s)
    return json.dumps(s)

## getwho function

def getwho(bot, who, channel=None):
    """ get userhost from bots userhost cache """
    who = who.lower()
    try:
        if bot.type in ["xmpp", "sxmpp", "sleek"]: return stripped(bot.userhosts[who])
        else: return bot.userhosts[who]
    except KeyError: pass
    
def getnick(bot, userhost):
    """ get nick from bots userhost cache """
    userhost = userhost.lower()
    try: return bot.nicks[userhost]
    except KeyError: pass
    
## splitxt function

def splittxt(what, l=375):
    """ split output into seperate chunks. """
    txtlist = []
    start = 0
    end = l
    length = len(what)
    for i in range(length/end+1):
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

## getrandomnick function
    
def getrandomnick():
    """ return a random nick. """
    return "jsb-" + str(random.randint(0, 100))

## decodeperchar function

def decodeperchar(txt, encoding='utf-8', what=""):
    """ decode a string char by char. strip chars that can't be decoded. """
    res = []
    nogo = []
    for i in txt:
        try: res.append(i.decode(encoding))
        except UnicodeDecodeError:
            if i not in nogo: nogo.append(i)
    if nogo:
        if what: logging.debug("%s: can't decode %s characters to %s" % (what, nogo, encoding))
        else: logging.debug("%s - can't decode %s characters to %s" % (whichmodule(), nogo, encoding))
    return u"".join(res)

## toenc function

def toenc(what, encoding='utf-8'):
    """ convert to encoding. """
    if not what: what=  u""
    try:
        w = unicode(what)
        return w.encode(encoding)
    except UnicodeDecodeError:
        logging.debug(u"%s - can't encode %s to %s" % (whichmodule(2), what, encoding))
        raise

## fromenc function

def fromenc(txt, encoding='utf-8', what=""):
    """ convert from encoding. """
    if not txt: txt = u""
    if type(txt) == types.UnicodeType: return txt
    try: return txt.decode(encoding)
    except UnicodeDecodeError:
        logging.debug(u"%s - can't decode %s - decoding per char" % (whichmodule(), encoding))
        return decodeperchar(txt, encoding, what)

## toascii function

def toascii(what):
    """ convert to ascii. """
    return what.encode('ascii', 'replace')

## tolatin1 function

def tolatin1(what):
    """ convert to latin1. """
    return what.encode('latin-1', 'replace')

## strippedtxt function

def strippedtxt(what, allowed=[]):
    """ strip control characters from txt. """
    txt = []
    for i in what:
        if ord(i) > 31 or (allowed and i in allowed): txt.append(i)
    try: res = ''.join(txt)
    except: res = u''.join(txt)
    return res
              
## stripcolor function

REcolor = re.compile("\003\d\d(.*?)\003")

def matchcolor(match):
    return match.group(1)

def stripcolor(txt):
    find = REcolor.findall(txt)
    for c in find:
        if c: txt = re.sub(REcolor, c, txt, 1) ; logging.info(txt)
    return txt

## uniqlist function

def uniqlist(l):
    """ return unique elements in a list (as list). """
    result = []
    for i in l:
        if i not in result: result.append(i)
    return result

## jabberstrip function

def jabberstrip(text, allowed=[]):
    """ strip control characters for jabber transmission. """
    txt = []
    allowed = allowed + ['\n', '\t']
    for i in text:
        if ord(i) > 31 or (allowed and i in allowed): txt.append(i)
    return u''.join(txt)

## filesize function

def filesize(path):
    """ return filesize of a file. """
    return os.stat(path)[6]

## touch function

def touch(fname):
    """ touch a file. """
    fd = os.open(fname, os.O_WRONLY | os.O_CREAT)
    os.close(fd)  

## stringinlist function

def stringinlist(s, l):
    """ check is string is in list of strings. """
    for i in l:     
        if s in i: return True
    return False

## stripident function

def stripident(userhost):
    """ strip ident char from userhost """
    try: userhost.getNode() ; return str(userhost)
    except AttributeError:  pass
    if not userhost: return None
    if userhost[0] in "~-+^": userhost = userhost[1:]
    elif userhost[1] == '=': userhost = userhost[2:]
    return userhost

## stripped function

def stripped(userhost):
    """ return a stripped userhost (everything before the '/'). """ 
    return userhost.split('/')[0]

## gethighest function

def gethighest(ddir, ffile):
    """ get filename with the highest extension (number). """
    highest = 0
    for i in os.listdir(ddir):
        if not os.path.isdir(ddir + os.sep + i) and ffile in i:
            try: seqnr = i.split('.')[-1]
            except IndexError: continue
            try:
                if int(seqnr) > highest: highest = int(seqnr)
            except ValueError: continue
    ffile += '.' + str(highest + 1)
    return ffile

## waitevents function

def waitevents(eventlist, millisec=5000):
    result = []
    for e in eventlist:
        if not e: continue
        #logging.warn("waitevents - waiting for %s" % e.txt)
        #e.finished.wait(millisec)
        res = waitforqueue(e.outqueue, 5000)
        result.append(res)
        e.finished.clear()
    return result

## waitforqueue function

def waitforqueue(queue, timeout=10000, maxitems=None, bot=None):
    """ wait for results to arrive in a queue. return list of results. """
    #if len(queue) > 1: return list(queue)
    result = []
    counter = 0
    if not maxitems: maxitems = 100
    logging.warn("waiting for queue: %s - %s" % (timeout, maxitems))
    try:
        while not len(queue):
            if len(queue) > maxitems: break
            if counter > timeout: break
            time.sleep(0.001) ; counter += 10
        logging.warn("waitforqueue - result is %s items (%s) - %s" % (len(queue), counter, str(queue)))
        return queue
    except AttributeError:
        q = []
        while 1:
            time.sleep(0.001) ;  counter += 10
            if counter > timeout: break
            try:
                q.append(queue.get_nowait())
            except Queue.Empty: continue
        logging.warn("waitforqueue - result is %s items (%s) - %s" % (len(q), counter, str(q)))
        return q
    #time.sleep(0.2)

## checkqueues function

def checkqueues(self, queues, resultlist):
    """ check if resultlist is to be sent to the queues. if so do it! """
    for queue in queues:
        for item in resultlist: queue.put_nowait(item)
        return True
    return False

## sedstring function

def sedstring(input, sedstring):
    seds = sedstring.split('/')   
    fr = seds[1].replace('\\', '')
    to = seds[2].replace('\\', '')
    return input.replace(fr,to)

## sedfile function

def sedfile(filename, sedstring):
    result = StringIO.StringIO()
    f = open(filename, 'r')
    seds = sedstring.split('/')   
    fr = seds[1].replace('\\', '')
    to = seds[2].replace('\\', '')
    try:
        for line in f:
            l = line.replace(fr,to)
            result.write(l)
    finally: f.close()
    return result

## dosed function

def dosed(filename, sedstring):
    """ apply a sedstring to the file. """
    try: f = open(filename, 'r')
    except IOError: return
    tmp = filename + '.tmp'
    fout = open(tmp, 'w')
    seds = sedstring.split('/')   
    fr = seds[1].replace('\\', '')
    to = seds[2].replace('\\', '')
    try:
        for line in f:
            if 'googlecode' in line or 'github' in line or 'google.com' in line or 'jsonbot.org' in line: l = line
            else: l = line.replace(fr,to)
            fout.write(l)
    finally:
        fout.flush()
        fout.close()
    try: os.rename(tmp, filename)
    except WindowsError:
        os.remove(filename)
        os.rename(tmp, filename)

def stringsed(instring, sedstring):
    """ apply a sedstring to a string. """
    seds = sedstring.split('/')   
    fr = seds[1].replace('\\', '')
    to = seds[2].replace('\\', '')
    mekker = instring.replace(fr,to)
    return mekker

def copyfile(filename, filename2, sedstring=None):
    """ copy a file with optional sed. """
    if os.path.isdir(filename): return
    try: f = open(filename, 'r')
    except IOError: return
    ddir = ""
    for x in filename2.split(os.sep)[:-1]:
        ddir += os.sep + x
        if not os.path.isdir(ddir):
            try: os.mkdir(ddir)
            except: pass
    try: fout = open(filename2, 'w')
    except: return
    if sedstring:
        seds = sedstring.split('/')   
        fr = seds[1].replace('\\', '')
        to = seds[2].replace('\\', '')
    try:
        for line in f:
            if sedstring:
                l = line.replace(fr,to)
            else: l = line 
            fout.write(l)
    finally:
        fout.flush()
        fout.close()
