# jsb/plugs/core/to.py
#
#

""" send output to another user .. used in a pipeline. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.utils.generic import getwho, waitforqueue
from jsb.lib.examples import examples

## basic imports

import time

## to command

def handle_to(bot, ievent):
    """ arguments: <nick> - direct output to <nick>, use this command in a pipeline. """
    try: nick = ievent.args[0]
    except IndexError: ievent.reply('to <nick>') ; return
    if nick == 'me': nick = ievent.nick
    if not getwho(bot, nick): ievent.reply("don't know %s" % nick) ; return
    if not ievent.prev: ievent.reply("use this command in a pipeline") ; return
    rq = ievent.prev.resqueue
    if not rq: time.sleep(1)
    if rq:
        l = len(rq)
        if l: bot.say(nick, "%s sents you this (%s lines):" % (ievent.prev.nick, l)) ; time.sleep(2)
        for r in rq: bot.say(nick, r) 
        if l == 1: ievent.reply('1 element sent')
        else: ievent.reply('%s elements sent' % l)
    else: ievent.reply('nothing to send')

cmnds.add('to', handle_to, ['OPER', 'USER', 'TO'])
examples.add('to', 'send pipeline output to another user', 'list ! to dunker')
