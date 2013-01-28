# boty/drivers/xmpp/bot.py
#
#

""" XMPP bot build on sleekxmpp. """

## boty imports

from jsb.imports import getsleek

sleekxmpp = getsleek()

## jsb imports

from jsb.lib.threads import start_new_thread
from jsb.utils.xmpp import stripped
from jsb.lib.botbase import BotBase
from jsb.drivers.xmpp.bot import SXMPPBot
from jsb.lib.errors import NoUserProvided
from jsb.lib.eventhandler import mainhandler
from message import Message
from presence import Presence

## basic imports

import logging

## BotyXMPPBot class

class SleekBot(SXMPPBot):

    def __init__(self, cfg, *args, **kwargs):
        if not cfg.user: raise NoUserProvided("please make sure the user config variable is set in %s (or use -u)"  % cfg.cfile)
        SXMPPBot.__init__(self, cfg, *args, **kwargs)
        self.type = "sleek"
        self.xmpp = sleekxmpp.ClientXMPP(cfg.user, cfg.password)
        self.default_port = cfg.port or 5222
        self.wait_timeout = 5
        self.xmpp.add_event_handler("session_start", self.session_start)
        self.xmpp.add_event_handler("message", self.handle_message)
        self.xmpp.add_event_handler('disconnected', self.handle_disconnected)
        self.xmpp.add_event_handler('connected', self.handle_connected)
        self.xmpp.add_event_handler('presence_available', self.handle_presence)
        self.xmpp.add_event_handler('presence_dnd', self.handle_presence)
        self.xmpp.add_event_handler('presence_xa', self.handle_presence)
        self.xmpp.add_event_handler('presence_chat', self.handle_presence)
        self.xmpp.add_event_handler('presence_away', self.handle_presence)   
        self.xmpp.add_event_handler('presence_unavailable', self.handle_presence) 
        self.xmpp.add_event_handler('presence_subscribe', self.handle_presence)   
        self.xmpp.add_event_handler('presence_subscribed', self.handle_presence)  
        self.xmpp.add_event_handler('presence_unsubscribe', self.handle_presence) 
        self.xmpp.add_event_handler('presence_unsubscribed', self.handle_presence)
        self.xmpp.add_event_handler('groupchat_direct_invite', self.handle_groupinvite)
        self.xmpp.add_event_handler('groupchat_invite', self.handle_groupinvite)
        self.xmpp.add_event_handler('groupchat_message', self.handle_message)
        self.xmpp.add_event_handler('groupchat_presence', self.handle_presence)
        self.xmpp.add_event_handler('groupchat_subject', self.handle_presence)
        self.xmpp.add_event_handler('failed_auth', self.handle_failedauth)
        self.xmpp.exception = self.exception
        self.xmpp.use_signals()
        if cfg.openfire:
            import ssl
            self.xmpp.ssl_version = ssl.PROTOCOL_SSLv3

    def session_start(self, event):
        logging.warn("session started")
        self.xmpp.send_presence()
        start_new_thread(self.joinchannels, ())
        
    def exception(self, ex): logging.error(str(ex))

    def handle_failedauth(self, error, *args): logging.error(error) 

    def handle_failure(self, ex, *args, **kwargs): logging.error(str(ex))

    def handle_disconnected(self, *args, **kwargs):
        logging.error("server disconnected")

    def handle_connected(self, *args, **kwargs):
        logging.warn("connected!")

    def start(self, connect=True, *args, **kwargs):
        BotBase.start(self, False)
        try:
            if connect:
                target = self.cfg.server or self.cfg.host
                port = self.cfg.port or 5222
                logging.warn("connecting to %s:%s" % (target, port)) 
                if port == 5223: use_tls = True
                else: use_tls = True
                self.xmpp.connect(address=(target, port), use_tls=use_tls)
                print 1
            self.xmpp.process(block=True)
            print 2
        except Exception, ex: logging.error(str(ex))

    def send(self, event):
        try:
            xml = event.tojabber()
            if not xml:
                raise Exception("can't convert %s to xml .. bot.send()" % what)
        except (AttributeError, TypeError):
            handle_exception()
            return
        self.xmpp.send_raw(xml)

    def outnocb(self, printto, txt, how=None, event=None, html=False, isrelayed=False, *args, **kwargs):
        """ output txt to bot. """
        if printto and printto in self.state['joinedchannels']: outtype = 'groupchat'
        else: outtype = "chat"
        target = printto
        txt = self.normalize(txt)
        #txt = stripcolor(txt)
        repl = Message(event)
        repl.to = target
        repl.type = (event and event.type) or "chat"
        repl.txt = txt
        if html:
            repl.html = txt
        logging.debug("%s - reply is %s" % (self.cfg.name, repl.dump()))
        if not repl.type: repl.type = 'normal'
        logging.debug("%s - sxmpp - out - %s - %s" % (self.cfg.name, printto, unicode(txt)))
        self.send(repl)

    def handle_message(self, data, *args, **kwargs):
        """ message handler. """   
        if '<delay xmlns="urn:xmpp:delay"' in str(data): logging.debug("ignoring delayed message") ; return
        m = Message()
        m.parse(data, self)
        if m.type == 'groupchat' and m.subject:
            logging.debug("%s - checking topic" % self.cfg.name)
            self.topiccheck(m)
            nm = Message(m)   
            callbacks.check(self, nm)
            return
        if m.isresponse:
            logging.debug("%s - message is a response" % self.cfg.name)
            return
        jid = None
        m.origjid = m.jid
        #if self.cfg.user in m.jid or (m.groupchat and self.cfg.nick == m.nick):
        #    logging.error("%s - message to self .. ignoring" % self.cfg.name)
        #    return 0
        if self.cfg.fulljids and not m.msg:
            utarget = self.userhosts.get(m.nick)
            if utarget: m.userhost = m.jid = m.auth = stripped(utarget)
            else: m.userhost = m.jid
        if m.msg: m.userhost = stripped(m.userhost)
        logging.debug("using %s as userhost" % m.userhost)
        m.dontbind = False
        self.put(m)

    def handle_presence(self, data, *args, **kwargs):
        """ message handler. """   
        try:
            p = Presence()
            p.parse(data, self)
            frm = p.fromm
            nickk = ""   
            nick = p.nick
            if self.cfg.user in frm: self.pongcheck = True
            if nick: 
                self.userhosts[nick] = stripped(frm)
                nickk = nick
            jid = p.fromm
            if nickk and jid and self.cfg.fulljids:
                channel = p.channel
                if not self.jids.has_key(channel):
                    self.jids[channel] = {}
                self.jids[channel][nickk] = jid
                self.userhosts[nickk] = stripped(jid)
                logging.debug('%s - setting jid of %s (%s) to %s' % (self.cfg.name, nickk, channel, self.userhosts[nickk]))
            if p.type == 'subscribe':
                pres = Presence({'to': p.fromm, 'type': 'subscribed'})
                self.send(pres)
                pres = Presence({'to': p.fromm, 'type': 'subscribe'})
                self.send(pres)
            nick = p.resource
            if p.type != 'unavailable':
                p.joined = True
                p.type = 'available'
            elif self.cfg.user in p.userhost:
                try:
                    del self.jids[p.channel]
                    logging.debug('%s - removed %s channel jids' % (self.cfg.name, p.channel))
                except KeyError: pass
            else:   
                try:
                    del self.jids[p.channel][p.nick]
                    logging.debug('%s - removed %s jid' % (self.cfg.name, p.nick))
                except KeyError: pass
            self.put(p)
        except Exception, ex: logging.error(str(ex))
