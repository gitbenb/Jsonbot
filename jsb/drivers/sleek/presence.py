# jsb/drivers/sleek/presence.py
#
#

""" SleekXMPP Presence. """

# jsb imports

from jsb.lib.eventbase import EventBase
from jsb.utils.exception import handle_exception
from jsb.utils.trace import whichmodule
from jsb.lib.gozerevent import GozerEvent

## basic imports

import time
import logging 

## classes

class Presence(GozerEvent):

    def __init__(self, nodedict={}):
        GozerEvent.__init__(self, nodedict)
        self.element = "presence"
        self.jabber = True
        self.cmnd = "PRESENCE"
        self.cbtype = "PRESENCE"
        self.bottype = "xmpp"

    def parse(self, data, bot=None):
        """ set ircevent compatible attributes """
        try:
            self.bot = bot or self.bot
            self.cmnd = 'PRESENCE'
            self.fromm = str(data['from'])        
            try: self.nick = self.fromm.split('/')[1]
            except (AttributeError, IndexError): self.nick = ""
            self.jid = str(self.jid) or self.fromm
            self.ruserhost = self.jid
            self.userhost = self.jid
            self.resource = self.nick
            self.stripped = self.jid.split('/')[0]
            self.auth = self.stripped
            self.channel = self.fromm.split('/')[0]
            self.printto = self.channel
            self.origtxt = self.txt
            self.time = time.time()
            if self.type == 'groupchat': self.groupchat = True
            else: self.groupchat = False
        except Excpetion, ex: handle_exception()
