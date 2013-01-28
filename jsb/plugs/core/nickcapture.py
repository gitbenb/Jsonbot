# jsb/plugs/core/nickcapture.py
#
#

""" nick recapture callback. """

## jsb imports

from jsb.lib.callbacks import callbacks

## callbacks

def ncaptest(bot, ievent):
    """ test if user is splitted. """
    if '*.' in ievent.txt or bot.cfg.server in ievent.txt: return 0
    ievent.bind()
    if bot.cfg.wantnick and bot.cfg.wantnick.lower() == ievent.nick.lower(): return 1
    if bot.cfg.nick.lower() == ievent.nick.lower(): return 1
    return 0

def ncap(bot, ievent):
    """ recapture the nick. """
    bot.donick(bot.cfg.wantnick or bot.cfg.nick)

callbacks.add('QUIT', ncap, ncaptest, threaded=True)
