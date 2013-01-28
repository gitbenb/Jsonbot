# plugs/markov.py
#
#

"""

Markov Talk for Gozerbot

The Chain:
    (predictate) -> [list of possible words]

TODO:
    - Propabilities
    - Start searching for full sentence, not just the first ORDER_K words 
      of a sentence

BHJTW:
    - adapted for JSONBOT

"""

__copyright__ = 'this file is in the public domain'
__author__ =  'Bas van Oostveen'
__coauthor__ = 'Bart Thate <bthate@gmail.com>'

from jsb.lib.datadir import getdatadir
from jsb.utils.url import geturl, striphtml
from jsb.utils.generic import jsonstring
from jsb.lib.persist import PlugPersist
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.callbacks import callbacks
from jsb.lib.plugins import plugs as plugins
from jsb.lib.threads import start_new_thread
from jsb.utils.limlist import Limlist
from jsb.lib.persist import PersistCollection, Persist
from jsb.utils.exception import handle_exception
from os.path import join as _j
import time
import re
import random
import types
import logging
import os

from jsb.lib.persistconfig import PersistConfig

cfg = PersistConfig()
cfg.define('enable', [])
cfg.define('command', 0)
cfg.define('onjoin', [])
cfg.define("target", "jsonbot")

def enabled(botname, channel):
    if jsonstring([botname, channel]) in cfg['enable']:
        return True

# Markers (is Marker the correct name for this?)
class Marker: pass
class BeginMarker(Marker): pass
class EndMarker(Marker): pass
class NickMarker(Marker): pass

# Tokens
TOKEN = Marker()
TOKEN_BEGIN = BeginMarker()
TOKEN_END = EndMarker()
TOKEN_NICK = NickMarker()

# Order-k, use predictate [-k:] = [word,word,]
# if ORDER_K==1: { ('eggs'):['with','spam',], 'with': ['bacon','green',] }
# if ORDER_K==2: { ('eat','eggs'):['with',TOKEN,), ('eggs','with'): ['bacon',] }
# ...
# Logical setting is often 2 or 3
ORDER_K = 2

# Maximum generation cycles
MAXGEN = 500

markovlearn = PlugPersist('markovlearn')
markovlearn.data.l = markovlearn.data.l or []
markovwords = {}
markovwordi = []
markovchains = {}

cfg.define('loud', 0)

def dummycb(bot, event): pass

callbacks.add('START', dummycb)

def init():
    """ init plugin """
    if not cfg.get('enable'): return 1
    callbacks.add("PRIVMSG", cb_markovtalk, cb_markovtalk_test, threaded=True)
    callbacks.add('JOIN', cb_markovjoin, threaded=True)
    callbacks.add('MESSAGE', cb_markovtalk, cb_markovtalk_test, threaded=True)
    callbacks.add('CONSOLE', cb_markovtalk, cb_markovtalk_test, threaded=True)
    start_new_thread(markovtrain, (markovlearn.data.l,))
    return 1

def size():
    """ return size of markov chains """
    return len(markovchains)

def markovtrain(l):
    """ train items in list """
    time.sleep(1)
    logging.warn("list to scan is: %s" % ",".join(l))
    for i in l:
        if i.startswith('http://'): start_new_thread(markovlearnurl, (i,))
        elif i.startswith('spider://'): start_new_thread(markovlearnspider, (i,))
        elif i.startswith('spiders://'): start_new_thread(markovlearnspider, (i,))
        else: start_new_thread(markovlearnlog, (i,))
    return 1
	
def iscommand(bot, ievent):
    """ check to see if ievent is a command """
    if not ievent.txt: return 0
    try: cc = bot.channels[ievent.channel]['cc']
    except (TypeError, KeyError): cc = None
    txt = ""
    if cc and ievent.txt[0] == cc: txt = ievent.txt[1:]
    if ievent.txt.startswith(bot.nick + ':') or ievent.txt.startswith(bot.nick + ','): txt = ievent.txt[len(bot.nick)+1:]
    oldtxt = ievent.txt
    ievent.txt = txt
    result = plugins.woulddispatch(bot, ievent)
    ievent.txt = oldtxt
    return result

def pre_markovjoin(bot, ievent):
    if ievent.forwarded or ievent.relayed: return False
    return True


def cb_markovjoin(bot, ievent):
    """ callback to run on JOIN """
    # check if its we who are joining
    nick = ievent.nick.lower()
    if nick in bot.splitted: return
    if nick == bot.cfg.nick: return
    # check if (bot.name, ievent.channel) is in onjoin list if so respond
    try: onjoin = cfg.get('onjoin')
    except KeyError: onjoin = None
    if type(onjoin) != types.ListType: return
    if jsonstring([bot.name, ievent.channel]) in onjoin:
        txt = getreply(bot, ievent, ievent.nick + ':')
        if txt: ievent.reply('%s: %s' % (ievent.nick, txt))
            
def cb_markovtalk_test(bot, ievent):
    """ callback precondition """
    if ievent.iscmnd(): return False
    return True

def cb_markovtalk(bot, ievent):
    """ learn from everything that is being spoken to the bot """
    txt = strip_txt(bot, ievent.txt)
    # markovtalk_learn
    if enabled(bot.cfg.name, ievent.channel): markovtalk_learn(txt)
    # if command is set in config then we don't respond in callback
    elif not cfg.get('loud'): return 
    itxt = ievent.txt.lower()
    # check is bot.nick is in ievent.txt if so give response
    botnick = cfg.target
    #responsenicks = (botnick, botnick+":", botnick+",")
    if botnick in itxt or cfg.get('loud') and ievent.msg: 
        # reply when called 
        result = getreply(bot, ievent, txt)
	# dont reply if answer is going to be the same as question
        if not result: return
        if result.lower() == txt.lower(): return
        ievent.reply(result)

# re to strip first word of logline
txtre = re.compile('^\S+ ')

def markovlearnspider(target):
    logging.warn("starting spider learn on %s" % target)
    coll = PersistCollection(getdatadir() + os.sep + 'spider' + os.sep + "data")
    if target.startswith("spider://"): target = target[9:]
    objs = coll.search('url', target)
    for obj in objs:
        if not obj.data and obj.data.url: print "skip - no url" ; continue
        time.sleep(0.001)
        if target not in obj.data.url: continue
        logging.warn("url is %s" % obj.data.url)
        try:
            if obj.data and obj.data.txt:
                for line in obj.data.txt.split("\n"):
                    if line.count(";") > 1: continue
                    markovtalk_learn(striphtml(line))
        except: handle_exception()


def markovlearnlog(chan):
    """ learn a log """
    lines = 0
    logfiles = os.listdir(getdatadir() + os.sep + 'chatlogs')
    for filename in logfiles:
        if chan[1:] not in filename: continue
        logging.warn("opening %s" % filename)
        for line in open(getdatadir() + os.sep + 'chatlogs' + os.sep + filename, 'r'):
            if lines % 10 == 0: time.sleep(0.001)
            if not line: continue
            lines += 1
            try:
                txt = ' '.join(line.strip().split()[2:]) # log format is: 2011-08-07 00:02:16  <botfather> love, peace and happiness
                markovtalk_learn(txt)
            except IndexError: continue
    logging.warn('learning %s log done. %s lines' % (chan, lines))
    return lines

def markovlearnurl(url):
    """ learn an url """
    lines = 0
    logging.warn('learning %s' % url)
    try:
        f = geturl(url)
        for line in f.split('\n'):
            line = striphtml(line)
            if lines % 10 == 0: time.sleep(0.01)
            line = line.strip()
            if not line: continue
            markovtalk_learn(line)
            lines += 1
    except Exception, e: logging.error(str(e))
    logging.warn('learning %s done' % url)
    return lines

def strip_txt(bot, txt):
    """ strip bot nick and addressing """
    # TODO: strip other nicks, preferably replacing them with something like 
    # TOKEN_NICK
    txt = txt.replace(cfg.target, "")
    txt = txt.replace("%s," % bot.cfg.nick, "")
    txt = txt.replace("%s:" % bot.cfg.nick, "")
    txt = txt.replace("%s" % bot.cfg.nick, "")
    return txt.strip()

def msg_to_array(msg):
    """ convert string to lowercased items in list """
    return [word.strip().lower() for word in msg.strip().split()]

def mw(w):
    if not w in markovwords:
        wi = len(markovwordi)
        markovwordi.append(w)
        markovwords[w] = wi
        return wi
    return markovwords[w]

def o2i(order):
    return tuple(mw(w) for w in order)

def i2o(iorder):
    return tuple(markovwordi[i] for i in iorder)

def markovtalk_learn(text_line):
    """ this is the function were a text line gets learned """
    text_line = msg_to_array(text_line)
    length = len(text_line)
    order = [TOKEN, ] * ORDER_K
    for i in range(length-1):
        order.insert(0, text_line[i])
        order = order[:ORDER_K]
        next_word = text_line[i+1]
        key = markovchains.setdefault(o2i(order), [])
        if not next_word in key: key.append(mw(next_word))

def getreply(bot, ievent, text_line):
    """ get 20 replies and choose the largest one """
    if not text_line: return "blurp .. no input"
    txt = text_line
    text_line = msg_to_array(text_line)
    wordsizes = {}
    maxsize = 0
    for i in text_line:
        wordsizes[len(i)] = i
        if len(i) > maxsize: maxsize = len(i)
    results = []
    keywords = ['is', 'are', "can", "will", "shall"]
    max = maxsize
    p = text_line
    if True:
        for pp in p:
            for k in keywords:
                line = getline('%s %s' % (pp, k))
                if line and line not in results: results.append(line) ; p = line
        print p
    if not results: return ""
    #res = []
    #for result in results[:3]:
    #    if len(result.split()) > 1: res.append(result.capitalize())
    #r = '. '.join(res)
    r = random.choice(results)
    if not r.endswith("."): r += "."
    return r.capitalize()

def getline(text_line):
    """ get line from markovvhains """
    text_line = msg_to_array(text_line)
    order = Limlist(ORDER_K)
    for i in range(ORDER_K): order.append(TOKEN)
    teller = 0
    for i in text_line[:ORDER_K]:
        order[teller] = i
        teller += 1
    output = ""
    prev = ""
    for i in range(MAXGEN):
        try:
            logging.debug(str(order))
            successorList = i2o(markovchains[o2i(order)])
            logging.debug(str(successorList))
        except KeyError, ex: continue
        word = successorList[0]
        if not word: break
        for word in successorList:
            if word not in output: output = output + " "  + word
        order.insert(0, word)
        order = order[:ORDER_K]
    logging.warn(output)
    output = output.replace('"""', '')
    output = output.replace(". ", "")
    output = output.lower()
    return output.strip()
    
def handle_markovsize(bot, ievent):
    """ markov-size .. returns size of markovchains """
    ievent.reply("I know %s phrases" % str(len(markovchains.keys())))

cmnds.add('markov-size', handle_markovsize, 'OPER')
examples.add('markov-size', 'size of markovchains', 'markov-size')

def handle_markovlearn(bot, ievent):
    """ command to let the bot learn a log or an url .. learned data 
        is not persisted """
    try: item = ievent.args[0]
    except IndexError: ievent.reply('<channel>|<url>') ; return
    if item.startswith('http://'):
        nrlines = markovlearnurl(item)
        ievent.reply('learned %s lines' % nrlines)
        return
    ievent.reply('learning log file %s' % item)
    nrlines = markovlearnlog(item)
    ievent.reply('learned %s lines' % nrlines)

cmnds.add('markov-learn', handle_markovlearn, 'OPER', threaded=True)
examples.add('markov-learn', 'learn a logfile or learn an url', '1) markov-learn #dunkbots 2) markov-learn http://gozerbot.org')
 
def handle_markovlearnadd(bot, ievent):
    """ add log or url to be learned at startup or reload """
    try: item = ievent.args[0]
    except IndexError: ievent.missing('<channel>|<url>|spider:<url>') ; return
    if item in markovlearn.data.l: ievent.reply('%s is already in learnlist' % item) ; return
    markovlearn.data.l.append(item)
    markovlearn.save()
    start_new_thread(markovtrain, (markovlearn.data.l,))
    ievent.reply('done')

cmnds.add('markov-learnadd', handle_markovlearnadd, 'OPER')
examples.add('markov-learnadd', 'add channel or url to permanent learning .. this will learn the item on startup', '1) markov-learnadd #dunkbots 2) markov-learnadd http://jsonbot.org')

def handle_markovlearnlist(bot, ievent):
    """ show the learnlist """
    ievent.reply(str(markovlearn.data.l))

cmnds.add('markov-learnlist', handle_markovlearnlist, 'OPER')
examples.add('markov-learnlist', 'show items in learnlist', 'markov-learnlist')

def handle_markovlearndel(bot, ievent):
    """ remove item from learnlist """
    try: item = ievent.args[0]
    except IndexError: ievent.missing('<channel>|<url>') ; return
    if item not in markovlearn.data.l: ievent.reply('%s is not in learnlist' % item) ; return
    markovlearn.data.l.remove(item)
    markovlearn.save()
    ievent.reply('done')

cmnds.add('markov-learndel', handle_markovlearndel, 'OPER')
examples.add('markov-learndel', 'remove item from learnlist', '1) markov-learndel #dunkbots 2) markov-learndel http://jsonbot.org')

def handle_markov(bot, ievent):
    """ this is the command to make the bot reply a markov response """
    if not enabled(bot.cfg.name, ievent.channel): ievent.reply('markov is not enabled in %s' % ievent.channel) ; return
    if not ievent.rest: ievent.missing('<txt>') ; return
    result = getreply(bot, ievent, strip_txt(bot, ievent.rest))
    if result: ievent.reply(result)

cmnds.add('markov', handle_markov, ['USER', 'WEB', 'CLOUD'])
examples.add('markov', 'ask for markov response', 'markov nice weather')

def handle_markovonjoinadd(bot, ievent):
    """ add channel to onjoin list """
    try: channel = ievent.args[0]
    except IndexError: channel = ievent.channel
    if (bot.cfg.name, channel) in cfg.get('onjoin'): ievent.reply('%s already in onjoin list' % channel) ; return
    cfg.get('onjoin').append((bot.cfg.name, channel))
    cfg.save()
    ievent.reply('%s added' % channel)

cmnds.add('markov-onjoinadd', handle_markovonjoinadd, 'OPER')
examples.add('markov-onjoinadd', 'add channel to onjoin config', '1) markov-onjoinadd 2) markov-onjoinadd #dunkbots')
 
def handle_markovonjoinremove(bot, ievent):
    """ remove channel from onjoin list """
    try: channel = ievent.args[0]
    except IndexError: channel = ievent.channel
    try: cfg.get('onjoin').remove((bot.cfg.name, channel))
    except ValueError: ievent.reply("%s not in onjoin list" % channel) ; return
    cfg.save()
    ievent.reply('%s removed' % channel)

cmnds.add('markov-onjoinremove', handle_markovonjoinremove, 'OPER')
examples.add('markov-onjoinremove', 'remove channel from onjoin config', '1) markov-onjoinremove 2) markov-onjoinremove #dunkbots')

def handle_markovenable(bot, ievent):
    """ enable markov in a channel .. learn the log of that channel """
    try: channel = ievent.args[0]
    except IndexError: channel = ievent.channel
    if not enabled(bot.cfg.name, channel): cfg.get('enable').append(jsonstring([bot.cfg.name, channel]))
    else: ievent.reply('%s is already enabled' % channel) ; return
    cfg.save()
    markovlearn.data.l.append(channel)
    markovlearn.save()
    ievent.reply('%s enabled' % channel)

cmnds.add('markov-enable', handle_markovenable, 'OPER')
examples.add('markov-enable', 'enable markov learning in [<channel>]', '1) markov-enable 2) markov-enable #dunkbots')

def handle_markovdisable(bot, ievent):
    """ disable markov in a channel """
    try: channel = ievent.args[0]
    except IndexError: channel = ievent.channel
    if enabled(bot.cfg.name, channel): cfg.get('enable').remove(jsonstring([bot.cfg.name, channel]))
    else: ievent.reply('%s is not enabled' % channel) ; return
    cfg.save()
    try:
        markovlearn.data.l.remove(channel)
        markovlearn.save()
    except ValueError: pass
    ievent.reply('%s disabled' % channel)

cmnds.add('markov-disable', handle_markovdisable, 'OPER')
examples.add('markov-disable', 'disable markov learning in [<channel>]', '1) markov-disable 2) markov-disable #dunkbots')
