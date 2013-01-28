# jsb/tornado/server.py
#
#

""" jsb tornado server code.  """

## jsb import

from jsb.imports import gettornado

tornado = gettornado()

## tornado import

import tornado.ioloop
import tornado.httpserver
import tornado.web

## basic imports

import logging

## jsb specific ioloop

class JSBLoop(tornado.ioloop.IOLoop):

    def __init__(self, *args):
        logging.warn("using Select IOLoop.")
        tornado.ioloop.IOLoop.__init__(self, tornado.ioloop._Select(), *args)
        
## server part

class TornadoServer(tornado.httpserver.HTTPServer):

    pass

class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        user  = self.get_secure_cookie("user")
        if not user: user = "demouser" + "@" + self.request.remote_ip
        if user: return tornado.escape.xhtml_escape(user)
