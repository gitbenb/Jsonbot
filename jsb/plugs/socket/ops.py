# plugs/op.py
#
#

"""
    for op to work for a user the user must have the channel name in his/hers
    status .. use !user-addstatus <username> #channel
    normally the bot doesnt op nicks that join after a split to prevent floods, 
    this can be disabled by using ops-cfg oponsplit 1
"""

## jsb imports

from jsb.utils.generic import getwho
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.callbacks import callbacks
from jsb.lib.users import getusers
from jsb.lib.persistconfig import PersistConfig

## basic imports

import time
import logging

## defines

cfg = PersistConfig()
cfg.define('oponsplit', 0)

## onjoincb callback

def opjoincb(bot, ievent):
    """ see if we should op a user on join """
    # don't try to op the bot
    if ievent.nick == bot.nick: return
    #if bot.state.has_key('no-op') and chan in bot.state['no-op']: return
    import time
    time.sleep(1)
    if (ievent.user and 'OPER' in ievent.user.data.perms) or (ievent.chan and ievent.userhost in ievent.chan.data.ops): bot.doop(ievent.channel.lower(), ievent.nick)
    try: bot.splitted.remove(ievent.nick.lower())
    except (ValueError, AttributeError): pass

callbacks.add('JOIN', opjoincb)

## op command

def handle_op1(bot, ievent):
    """ op [<nick>] .. op an user """
    chan = ievent.channel.lower()
    #if bot.state.has_key('no-op') and chan in bot.state['no-op']:
    #    ievent.reply('opping is disabled in %s' % ievent.channel)
    #    return
    try: nick = ievent.args[0]
    except IndexError: nick = ievent.nick
    userhost = getwho(bot, nick)
    if not userhost: userhost = ievent.userhost
    if (ievent.user and 'OPER' in ievent.user.data.perms) or (ievent.chan and userhost in ievent.chan.data.ops): bot.doop(chan, nick)
    ievent.done()

cmnds.add('op', handle_op1, 'USER', threaded=True, speed=9)
examples.add('op', 'op [<nick>] .. give ops to <nick> or op the person giving the command', '1) op 2) op dunker')

## ops-permadd command

def handle_permadd(bot, ievent):
    if not ievent.chan: ievent.reply("channel is not set in event") ; return
    try: nick = ievent.args[0]
    except IndexError: nick = ievent.nick
    userhost = getwho(bot, nick)
    if not userhost: userhost = ievent.userhost
    if not userhost in ievent.chan.data.ops:
        ievent.chan.data.ops.append(userhost)
        ievent.chan.save()
        ievent.reply("added %s to the permenent ops list" % userhost)
    else: ievent.reply("%s is already in permops list" % userhost)

cmnds.add('ops-permadd', handle_permadd, 'OPER')
examples.add('ops-permadd', 'add permanent ops for user', 'ops-permadd dunker')

## ops-permdel command

def handle_permdel(bot, ievent):
    if not ievent.chan: ievent.reply("channel is not set in event") ; return
    try: nick = ievent.args[0]
    except IndexError: nick = ievent.nick
    userhost = getwho(bot, nick)
    if not userhost: userhost = ievent.userhost
    if userhost in ievent.chan.data.ops:
        ievent.chan.data.ops.remove(userhost)
        ievent.chan.save()
        ievent.reply("removed %s from the permenent ops list" % userhost)
    else: ievent.reply("%s is not in permops list" % userhost)

cmnds.add('ops-permdel', handle_permdel, 'OPER')
examples.add('ops-permdel', 'delete permanent ops for user', 'ops-permadd dunker')

## splitted command

def handle_splitted(bot, ievent):
    """ splitted .. show splitted list """
    ievent.reply(str(bot.splitted))

cmnds.add('splitted', handle_splitted, 'OPER')
examples.add('splitted', 'show whos on the splitted list', 'splitted')

## splitted-clear command

def handle_splittedclear(bot, ievent):
    """ splitted-clear .. clear splitted list """
    bot.splitted = []
    ievent.reply('done')

cmnds.add('splitted-clear', handle_splittedclear, 'OPER')
examples.add('splitted-clear', 'clear the splitted list', 'splitted-clear')

## ops-disable command

def handle_opsdisable(bot, ievent):
    """ disable opping in channel """
    try: chan = ievent.args[0].lower()
    except: chan = ievent.channel.lower()
    oplist = bot.state['no-op']
    if oplist and chan not in oplist:
        bot.state['no-op'].append(chan)
        bot.state.save()
        ievent.reply('opping in %s disabled' % chan)
        if chan in bot.state['opchan']: bot.delop(chan, bot.nick)
    else: ievent.reply('opping %s is already disabled' % chan)

#cmnds.add('ops-disable', handle_opsdisable, 'OPER')
#examples.add('ops-disable', 'ops-disable [<channel>] .. disable opping in provided channel or the channel command was given in', '1) ops-disable 2) ops-disable #dunkbots')

## ops-enable command

def handle_opsenable(bot, ievent):
    """ enable opping in channel """
    try: chan = ievent.args[0].lower()
    except: chan = ievent.channel.lower()
    oplist = bot.state['no-op']
    if oplist and chan in oplist:
        bot.state['no-op'].remove(chan)
        bot.state.save()
        ievent.reply('opping in %s is enabled' % chan)
    else: ievent.reply('opping in %s is already enabled' % chan)

#cmnds.add('ops-enable', handle_opsenable, 'OPER')
#examples.add('ops-enable', 'ops-enable [<channel>] .. enable opping in provided channel or the channel command was given in', '1) ops-enable 2) ops-enable #dunkbots')

## ops-snoop command

def handle_opsnoop(bot, ievent):
    """ show in which channels opping is disabled """
    ievent.reply('opping is disabled in %s' % bot.state['no-op'])
    
cmnds.add('ops-snoop', handle_opsnoop, 'OPER')
examples.add('ops-snoop', 'list in which channels opping is disabled', 'ops-snoop')

## checkmode callback

def checkmode(bot, ievent):
    """ check mode string """
    plus = 0
    teller = 0
    try:
        args = ievent.arguments
        chan = args[0].lower()
        modestr = args[1]
        who = args[2:]
    except: logging.warn('unknow mode string format: %s' % str(ievent)) ; return
    if not bot.state.has_key('no-op'): bot.state['no-op'] = [] ; bot.state.save()
    for i in modestr:
        if i == '+': plus = 1 ; continue
        if i == '-': plus = 0 ; continue
        if i == 'o' and plus:
            if who[teller].lower() == bot.cfg.nick.lower():
                if ievent.channel in bot.state['no-op']:
                    bot.delop(ievent.channel.lower(), bot.cfg.nick)
                else:
                    logging.warn('opped on %s' % chan)
                    bot.state['opchan'].append(chan)
        if i == 'o' and not plus:
            if who[teller].lower() == bot.cfg.nick.lower():
                logging.warn('deopped on %s' % chan)
                try: bot.state['opchan'].remove(chan)
                except ValueError: pass
        teller += 1

callbacks.add('MODE', checkmode)
