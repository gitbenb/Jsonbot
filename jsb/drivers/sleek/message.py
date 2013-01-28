# jsb/drivers/sleek/message.py
#
#

""" jabber message definition .. types can be normal, chat, groupchat, 
    headline or  error
"""

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.utils.trace import whichmodule
from jsb.utils.generic import toenc, fromenc, jabberstrip
from jsb.utils.locking import lockdec
from jsb.lib.eventbase import EventBase
from jsb.lib.errors import BotNotSetInEvent
from jsb.lib.gozerevent import GozerEvent

## basic imports

import types
import time
import thread
import logging
import re

## locks

replylock = thread.allocate_lock()
replylocked = lockdec(replylock)

## classes

class Message(GozerEvent):

    """ jabber message object. """

    def __init__(self, nodedict={}):
        self.element = "message"
        self.jabber = True
        self.cmnd = "MESSAGE"
        self.cbtype = "MESSAGE"
        self.bottype = "xmpp"
        self.type = "normal"
        self.speed = 8
        GozerEvent.__init__(self, nodedict)
  
    def __copy__(self):
        return Message(self)

    def __deepcopy__(self, bla):
        m = Message()
        m.copyin(self)
        return m

    def parse(self, data, bot=None):
        """ set ircevent compat attributes. """
        logging.info("starting parse on %s" % str(data))
        self.bot = bot
        self.jidchange = False
        self.jid = str(data['from'])
        self.type = data['type']
        if not self.jid: logging.error("can't detect origin - %s" % data) ; return
        try: self.resource = self.jid.split('/')[1]
        except IndexError: pass
        self.channel = self.jid.split('/')[0]
        self.origchannel = self.channel
        self.nick = self.resource
        self.ruserhost = self.jid
        self.userhost = self.jid
        self.stripped = self.jid.split('/')[0]
        self.printto = self.channel
        try: self.txt = str(data['body']) ; self.nodispatch = False
        except AttributeError: self.txt = "" ; self.nodispatch = True
        self.time = time.time()
        logging.warn("message type is %s" % self.type)
        if self.type == 'groupchat':
            self.groupchat = True
            self.auth = self.userhost
        else:
            self.showall = True
            self.groupchat = False
            self.auth = self.stripped
            self.nick = self.jid.split("@")[0]
        self.msg = not self.groupchat
        self.fromm = self.jid
        self.makeargs()
        self.bind(self.bot)
        self.issleek = True
        return self

    def errorHandler(self):
        """ dispatch errors to their handlers. """
        try:
            code = self.get('error').code
        except Exception, ex:
            handle_exception()
        try:
            method = getattr(self, "handle_%s" % code)
            if method:
                logging.error('sxmpp.core - dispatching error to handler %s' % str(method))
                method(self)
        except AttributeError, ex: logging.error('sxmpp.core - unhandled error %s' % code)
        except: handle_exception()

    def normalize(self, what):
        return self.bot.normalize(what)
