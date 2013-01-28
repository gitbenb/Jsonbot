# jsb/web/event.py
#
#

""" web event. """

## jsb imports

from jsb.lib.eventbase import EventBase
from jsb.utils.generic import splittxt, fromenc, toenc
from jsb.utils.xmpp import stripped
from jsb.lib.outputcache import add
from jsb.utils.url import getpostdata
from jsb.utils.exception import handle_exception
from jsb.lib.channelbase import ChannelBase
from jsb.imports import getjson, gettornado
from jsb.utils.lazydict import LazyDict
from jsb.lib.errors import NoInput, NoErrorSet

## other imports

json = getjson()

tornado = gettornado()
import tornado.escape

## basic imports

import cgi
import logging
import re

## WebEvent class

class TornadoEvent(EventBase):

    def __init__(self, bot=None): 
        EventBase.__init__(self, bot=bot)
        self.bottype = "tornado"
        self.cbtype = "TORNADO"
        self.bot = bot
        self.how = "overwrite"

    def __deepcopy__(self, a):
        e = TornadoEvent()
        e.copyin(self)
        e.handler = self.handler
        e.request = self.request
        return e

    def parseAPI(self, handler, apitype, path):
        """ parse request/response into a WebEvent. """
        #logging.warn(dir(handler))
        #logging.warn(dir(handler.request))
        #logging.warn(request.arguments)
        #logging.warn(request.body)
        self.handler = handler
        self.request = handler.request
        self.query = self.request.query
        self.upath = path
        self.apitype = apitype
        self.userhost = tornado.escape.xhtml_escape(handler.current_user)
        if not self.userhost: raise Exception("no current user.")
        input = path
        self.isweb = True
        logging.warn("input is %s" % input)
        if not input: raise NoInput(input)
        self.txt = fromenc(input.strip(), self.bot.encoding)
        self.nick = self.userhost.split("@")[0]
        self.auth = fromenc(self.userhost)
        self.stripped = stripped(self.auth)
        self.channel = stripped(self.userhost)
        logging.debug(u'tornado - parsed - %s - %s' % (self.txt, self.userhost)) 
        self.prepare()
        return self

    def parse(self, handler, request, path=None):
        """ parse request/response into a WebEvent. """
        self.handler = handler
        self.request = request
        self.userhost = tornado.escape.xhtml_escape(handler.current_user)
        if not self.userhost: raise Exception("no current user.")
        try: how = request.arguments['how'][0]
        except KeyError: how = "background"
        if not how: how = "background"
        self.how = how
        if self.how == "undefined": self.how = "overwrite"
        logging.warn("web - how is %s" % self.how)
        input = request.headers.get('content') or request.headers.get('cmnd')
        if not input:
            try: input = request.arguments['content'] or request.arguments['cmnd']
            except KeyError: pass
        self.isweb = True
        if not input: logging.warn("input is %s" % input) ; raise NoInput(input)
        self.txt = fromenc(input[0].strip(), self.bot.encoding)
        self.nick = self.userhost.split("@")[0]
        self.auth = fromenc(self.userhost)
        self.stripped = stripped(self.auth)
        self.channel = stripped(self.userhost)
        logging.debug(u'tornado - parsed - %s - %s' % (self.txt, self.userhost)) 
        self.prepare()
        return self

    def parsesocket(self, handler, message):
        """ parse request/response into a WebEvent. """
        self.handler = handler
        try: data = LazyDict(json.loads(message))
        except Exception, ex: logging.error("failed to parse data: %s - %s" % (message, str(ex))) ; return self
        logging.info("incoming: %s" % message)
        self.div = data.target
        self.userhost = tornado.escape.xhtml_escape(handler.current_user)
        if not self.userhost: raise Exception("no current user.")
        self.isweb = True
        input = data.cmnd
        self.how = data.how or self.how
        logging.warn("cmnd is %s - how is %s" % (input, self.how))
        self.txt = fromenc(input.strip(), self.bot.encoding)
        self.nick = self.userhost.split("@")[0]
        self.auth = fromenc(self.userhost)
        self.stripped = stripped(self.auth)
        self.channel = stripped(self.userhost)
        logging.debug(u'tornado - parsed - %s - %s' % (self.txt, self.userhost)) 
        self.prepare()
        return self

    def error(self, nr):
        if nr: self.handler.send_error(nr) ; self.finish()
        else: raise NoErrorSet