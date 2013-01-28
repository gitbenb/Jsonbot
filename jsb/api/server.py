# jsb/api/server.py
#
#

""" jsb api server.  """

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.drivers.tornado.event import TornadoEvent
from jsb.lib.datadir import getdatadir
from jsb.imports import gettornado
from jsb.lib.exit import globalshutdown
from jsb.lib.floodcontrol import floodcontrol
from jsb.api.hooks import api_check
from jsb.lib.runner import apirunner
from jsb.tornado import server

tornado = gettornado()

## tornado import

import tornado.web

## basic imports

import sys
import time
import types
import os
import logging
import urlparse
import urllib
import socket
import ssl
import select

## defines

bot = None

## server part

class APIHandler(server.BaseHandler):

    """ the bots remote command dispatcher. """

    @tornado.web.asynchronous
    def get(self, path):
        """ show basic page. """
        try:
            if not bot: logging.warn("api server not enabled") ; return
            user = self.current_user
            host = self.request.host
            event = TornadoEvent(bot=bot)
            event.parseAPI(self, "GET", path)
            event.doweb = True
            if floodcontrol.checkevent(event): self.send_error(408) ; return
            api_check(bot, event)
        except Exception, ex:
            handle_exception()
            self.send_error(500)

    @tornado.web.asynchronous
    def post(self, path):
        """ show basic page. """
        try:
            if not bot: logging.warn("api server not enabled") ; return
            user = self.current_user
            host = self.request.host
            event = TornadoEvent(bot=bot)
            event.parseAPI(self, "POST", path)
            event.doweb = True
            if floodcontrol.checkevent(event): self.send_error(408) ; return
            api_check(bot, event)
        except Exception, ex:
            handle_exception()
            self.send_error(500)



def createserver(ddir):
    """ create the API tornado app. """
    from jsb.tornado.server import TornadoServer
    settings = {
        "static_path": ddir + os.sep + "static",
        "cookie_secret": "661oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    }

    application = tornado.web.Application([(r"(/api/.*)", APIHandler)], **settings)
    return TornadoServer(application)

def runapiserver(port=None, ddir=None):
    """ start running the API server. needs to be called from the main thread. """
    from jsb.drivers.tornado.bot import TornadoBot
    global bot
    bot = TornadoBot(botname="api-bot")
    if port:
        try: port = int(port)
        except ValueError: pass
    else: port = 10105
    try:
         server = createserver(ddir or getdatadir())
         server.bind(port)
         logging.warn("starting API server on port %s" % port)
         server.start()
         server.io_loop.start()
    except KeyboardInterrupt: globalshutdown()
    except Exception, ex: handle_exception() ; os._exit(1)
    else: globalshutdown()
