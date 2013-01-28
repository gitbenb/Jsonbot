# jsb/lib/factory.py
#
#

""" Factory to produce instances of classes. """

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.lib.errors import NoSuchBotType, NoUserProvided

## basic imports

import logging

## Factory base class

class Factory(object):
     pass

## BotFactory class

class BotFactory(Factory):

    def create(self, type=None, cfg={}):
        try: type = cfg['type'] or type or None
        except KeyError: pass
        try:
            if 'xmpp' in type:
                from jsb.drivers.xmpp.bot import SXMPPBot
                bot = SXMPPBot(cfg)
            elif type == 'irc':
                from jsb.drivers.irc.bot import IRCBot
                bot = IRCBot(cfg)
            elif type == 'console':
                from jsb.drivers.console.bot import ConsoleBot
                bot = ConsoleBot(cfg)
            elif type == 'base':
                from jsb.lib.botbase import BotBase
                bot = BotBase(cfg)
            elif type == 'tornado' or type == "web":
                from jsb.drivers.tornado.bot import TornadoBot
                bot = TornadoBot(cfg)
            elif type == 'sleek':
                from jsb.drivers.sleek.bot import SleekBot
                bot = SleekBot(cfg)
            else: raise NoSuchBotType('%s bot .. unproper type %s' % (type, cfg.dump()))
            return bot
        except NoUserProvided, ex: logging.info("%s - %s" % (cfg.name, str(ex)))
        except AssertionError, ex: logging.warn("%s - assertion error: %s" % (cfg.name, str(ex)))
        except Exception, ex: handle_exception()

bot_factory = BotFactory()
