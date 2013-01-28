# jsb/api/__init__.py
#
#

""" JSONBOT package for the REST API. """

__version__ = "0.1"

from jsb.lib.callbacks import api_callbacks
from jsb.lib.runner import apirunner

import urllib
import logging

class APIHooks(object):

    def __init__(self):
        self.cbs = {}

    def register(self, path, handler):
        #from jsb.api.server import bot
        #if not bot: logging.warn("api server not enabled - not registering %s hook" % path) ; return
        logging.warn("registering %s - %s" % (path, str(handler)))
        self.cbs[path] = handler

    def unregister(self, path):
        logging.warn("unregister %s" % path)
        del self.cbs[path]

    def dispatch(self, urlpath, bot, event):
        logging.warn("dispatching %s" % urlpath)
        urlpath = urllib.unquote_plus(urlpath.strip())
        urlpath = urlpath.split('#')[0]
        urlpath = urlpath.split('?')[0] 
        for path, cb in self.cbs.iteritems():
            if urlpath.startswith(path): apirunner.put(5, urlpath, cb, bot, event) ; return      

get_hooks = APIHooks()
post_hooks = APIHooks()

def api_check(bot , event):
    if event.apitype == "POST": post_hooks.dispatch(event.upath, bot, event)
    elif event.apitype == "GET": get_hooks.dispatch(event.upath, bot, event)
    else: logging.error("unknown api type %s" % event.apitype)

def api_ping(bot, event):
    event.reply("pong")
    event.finish()

get_hooks.register("/api/ping", api_ping)
