# jsb/socklib/xmpp/core.py
#
#

"""
    this module contains the core xmpp handling functions.

"""

## jsb imports

from jsb.lib.errors import CannotAuth, StreamError
from jsb.lib.eventbase import EventBase
from jsb.lib.config import Config
from jsb.utils.generic import toenc, jabberstrip, fromenc
from jsb.utils.lazydict import LazyDict
from jsb.utils.exception import handle_exception
from jsb.utils.locking import lockdec
from jsb.lib.threads import start_new_thread
from jsb.utils.trace import whichmodule
from jsb.lib.gozerevent import GozerEvent
from jsb.lib.fleet import getfleet
from jsb.imports import getdns
from jsb.lib.runner import threadrunner

## xmpp import

from jsb.contrib import xmlstream
from jsb.contrib import digestmd5

## basic imports

import socket
import os
import time
import copy
import logging
import thread
import cgi
import xml
import re
import hashlib
import sys
import base64
import random

## python 2.5 shim

try: bytes()
except:
    def bytes(txt): return str(txt)    

## locks

outlock = thread.allocate_lock()   
inlock = thread.allocate_lock()
connectlock = thread.allocate_lock()
outlocked = lockdec(outlock)
inlocked = lockdec(inlock)  
connectlocked = lockdec(connectlock) 

## classes

class XMLStream(xmlstream.NodeBuilder):

    """ XMLStream. """

    def __init__(self, name=None):
        if not self.cfg: raise Exception("sxmpp - config is not set")
        self.cfg.name = name or self.cfg.name
        if not self.cfg.name: raise Exception("bot name is not set in config file %s" % self.cfg.filename)
        self.connection = None
        self.target = None
        self.streamid = None
        self.encoding = "utf-8"
        self.stopped = False
        self.failure = ""
        self.result = LazyDict()
        self.final = LazyDict()
        self.subelements = []
        self.reslist = []
        self.cur = u""
        self.tags = []
        self.features = []
        self.handlers = LazyDict()
        self.addHandler('error', self.handle_error)
        self.addHandler('proceed', self.handle_proceed)
        self.addHandler('message', self.handle_message)
        self.addHandler('presence', self.handle_presence)
        self.addHandler('iq', self.handle_iq)
        self.addHandler('stream', self.handle_stream)
        self.addHandler('stream:stream', self.handle_stream)
        self.addHandler('stream:error', self.handle_streamerror)
        self.addHandler('stream:features', self.handle_streamfeatures)
        self.addHandler('challenge', self.handle_challenge)
        self.addHandler('failure', self.handle_failure)
        self.addHandler('success', self.handle_success)

    def handle_success(self, data):
        """ default stream handler. """
        logging.info("%s - BINGO !! is %s" % (self.cfg.name, data.tojson()))

    def handle_error(self, data):
        """ default stream handler. """
        try:
            logging.error("%s - error is %s" % (self.cfg.name, data['error']['text']['data'])) 
        except: logging.error(data.tojson())

    def handle_failure(self, data):
        """ default stream handler. """
        logging.error("%s - failure is %s" % (self.cfg.name, data.tojson()))
        self.failure = data
        self.stopped = True

    def handle_challenge(self, data):
        """ default stream handler. """
        logging.debug("%s - challenge is %s" % (self.cfg.name, data.tojson()))

    def handle_proceed(self, data):
        """ default stream handler. """
        logging.debug("%s - proceeding" % self.cfg.name)

    def handle_stream(self, data):
        """ default stream handler. """
        logging.debug("%s - stream - %s" % (self.cfg.name, data.tojson()))
        if data and data.id: self.streamid = data.id

    def handle_streamend(self, data):
        """ default stream handler. """
        logging.warn("%s - stream END - %s" % (self.cfg.name, data))

    def handle_streamerror(self, data):
        """ default stream error handler. """
        logging.error("%s - STREAMERROR - %s" % (self.cfg.name, data.tojson()))
        #raise StreamError(data.tojson())
         
    def handle_streamfeatures(self, data):
        """ default stream features handler. """
        logging.debug("%s - STREAMFEATURES: %s" % (self.cfg.name, LazyDict(data).dump()))
         
    def addHandler(self, namespace, func):
        """ add a namespace handler. """
        self.handlers[namespace] = func

    def delHandler(self, namespace):
        """ delete a namespace handler. """
        del self.handlers[namespace]

    def getHandler(self, namespace):
        """ get a namespace handler. """
        try: return self.handlers[namespace]
        except KeyError: return None

    def parse_one(self, data):
        """ handle one xml stanza. """
        xmlstream.NodeBuilder.__init__(self)
        self._dispatch_depth = 2
        try: return self._parser.Parse(data.strip())
        except xml.parsers.expat.ExpatError, ex: expaterror = ex
        except UnicodeEncodeError:
            try: return self._parser.Parse(data.encode("utf-16"))
            except xml.parsers.expat.ExpatError, ex: expaterror = ex
        except Exception, ex:
            handle_exception()
            return {}
        if expaterror:
            if 'not well-formed' in str(expaterror):  
                logging.error(u"%s - data is not well formed" % self.cfg.name)
                logging.info(data)
                logging.debug(u"buffer: %s previous: %s" % (self.buffer, self.prevbuffer))
            return {}
            logging.debug(u"%s - ALERT: %s - %s" % (self.cfg.name, str(expaterror), data))

    def checkifvalid(self, data):
        result = self.parse_one(data)
        self.final = {}
        self.reslist = []
        self.tags = []
        self.subelements = []
        #self.buffer = ""
        return result

    @inlocked
    def loop_one(self, data):
        """ handle one xml stanza. """
        if self.parse_one(data): return self.finish(data)
        return {}

    def _readloop(self):
        """ proces all incoming data. """
        logging.debug('%s - starting readloop' % self.cfg.name)
        self.prevbuffer = u""
        self.buffer = u""
        self.error = u""
        data = u""
        while not self.stopped and not self.stopreadloop:
            try:
                data = jabberstrip(fromenc(self.connection.read()), allowed=["\n", ])
                if self.stopped or self.stopreadloop: break
                logging.info(u"< %s (%s)" % (data, len(data)))
                if data.endswith("</stream:stream>"):
                    logging.error("%s - end of stream detected" % self.cfg.name)
                    self.error = "streamend"
                    self.disconnectHandler(Exception('remote %s disconnected' %  self.cfg.host))
                    break
                if data == "":
                    logging.error('%s - remote disconnected' % self.cfg.name)
                    self.error = 'disconnected'
                    self.disconnectHandler(Exception('remote %s disconnected' %  self.cfg.host))
                    break
                if True:
                    self.buffer = u"%s%s" % (self.buffer, data)
                    handlers = self.handlers.keys()
                    handlers.append("/")
                    for handler in handlers:
                        target = u"%s>" % handler
                        index = self.buffer.find(target)
                        if index != -1:
                            try:
                                if self.loop_one(self.buffer[:index+len(target)]):
                                    self.buffer = self.buffer[index+1+len(target):]
                                else:
                                    self.buffer = u""
                                    break
                            except: handle_exception()
            except AttributeError, ex: 
                logging.error(u"%s - connection disappeared: %s" % (self.cfg.name, str(ex)))
                self.buffer = u""
                self.error = str(ex)
                self.disconnectHandler(ex)
                break
            except xml.parsers.expat.ExpatError, ex:
                logging.error(u"%s - %s - %s" % (self.cfg.name, str(ex), data))
                self.buffer = u""
                self.error = str(ex)
                self.disconnectHandler(ex)
                break
            except Exception, ex:
                handle_exception()
                self.error = str(ex)
                self.disconnectHandler(ex)
                break
        logging.debug('%s - stopping readloop .. %s' % (self.cfg.name, self.error or 'error not set'))

    @outlocked
    def _raw(self, stanza):
        """ output a xml stanza to the socket. """
        if self.stopped or self.failure: logging.info("%s - bot is stopped .. not sending" % self.cfg.name) ; return
        try:
            stanza = stanza.strip()
            if not stanza:
                logging.debug("%s - no stanze provided. called from: %s" % (self.cfg.name, whichmodule()))
                return
            what = jabberstrip(stanza, allowed=["\n", ])
            what = toenc(what)
            if not what.endswith('>') or not what.startswith('<'):
                logging.error('%s - invalid stanza: %s' % (self.cfg.name, what))
                return
            start = what[:3]
            if start in ['<st', '<me', '<pr', '<iq', "<au", "<re", "<fa", "<ab"]:
                if start == "<pr": logging.info(u"> %s" % what)
                else: logging.info(u"> %s" % what)
                if not self.connection: self.sock.send(what)
                else:
                    try: self.connection.send(what + u"\r\n")
                    except AttributeError:
                        try: self.connection.write(what)
                        except AttributeError: self.sock.send(what)
            else: logging.error('%s - invalid stanza: %s' % (self.cfg.name, what))
            if self.cfg.sleeptime: time.sleep(self.cfg.sleeptime)
            else: time.sleep(0.01)
        except socket.error, ex:
            if 'Broken pipe' in str(ex):
                logging.debug('%s - core - broken pipe .. ignoring' % self.cfg.name)
                return
            self.error = str(ex)
            handle_exception()
        except AttributeError: logging.warn("%s - socket went away: %s" % (self.cfg.name, stanza))
        except Exception, ex:
            self.error = str(ex)
            handle_exception()

    def waiter(self, txt=None, find=None):
        if txt: self._raw(txt)
        res = None
        while 1:
            try:
                try: result = self.connection.read()
                except AttributeError: result = self.sock.recv(1500)
                if not result: time.sleep(0.1) ; continue
                logging.info("< %s (%s)" %  (result, self.cfg.name))
                res = self.loop_one(result)
                if self.stopped or self.failure: break
                if not find: break
                elif find in result: break
            except Exception, ex: handle_exception()
        return res

    def doconnect(self):
        """ connect to the server. """
        target = None
        port = None
        try:
            dns = getdns()
            import dns.resolver
        except: pass
        else:
            try:
                xmpp_srv = "_xmpp-client._tcp.%s" % (self.cfg.server or self.cfg.host)
                answers = dns.resolver.query(xmpp_srv, dns.rdatatype.SRV)
            except ImportError:
                loging.warn("resolver is not available.")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                logging.info("no appropriate SRV record found.")
            else:
                addresses = {}
                intmax = 0
                for answer in answers:
                    try:
                        intmax += answer.priority
                        addresses[intmax] = (answer.target.to_text()[:-1], answer.port)
                    except Exception, ex: logging.debug("%s - skipping %s: %s" % (self.cfg.name, str(answer), str(ex)))
                priorities = [x for x in addresses.keys()]
                priorities.sort()

                picked = random.randint(0, intmax)
                for priority in priorities:
                    if picked <= priority:
                        target = addresses[priority]
                        break

        if not target or self.cfg.noresolver: target = (self.cfg.server or self.cfg.host, self.cfg.port)
        logging.debug("%s - TARGET is %s" % (self.cfg.name, target))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(0)
        self.sock.settimeout(30)
        logging.warn("connecting to %s (%s)" % (target, self.cfg.name))
        self.sock.connect(target)
        self.target = target
        logging.warn("connected! trying to login as %s (%s)" % (self.cfg.user, self.cfg.name))
        return True

    def makeready(self):
        if self.cfg.port == 5223:
            logging.warn("using old style port")
            self.dossl()
            iq = self.init_stream('features')
            self.auth_methods(iq)
            return iq
        iq = self.init_stream('features')
        #iq = self.waiter('<stream:stream to="%s" xmlns="jabber:client" xmlns:stream="http://etherx.jabber.org/streams" version="1.0">' % self.cfg.user.split('@')[1], "features")
        self.auth_methods(iq)
        self.init_tls() 
        self.sock.settimeout(60)
        self.sock.setblocking(1)
        self.dossl()
        return iq

    def init_stream(self, wait="stream"):
        if self.stopped: return
        logging.info("%s - starting stream" % self.cfg.name)
        iq = self.waiter('<stream:stream to="%s" xmlns="jabber:client" xmlns:stream="http://etherx.jabber.org/streams" version="1.0">' % self.cfg.user.split('@')[1], wait)
        time.sleep(1)
        logging.warn("iq is %s" % iq.tojson())
        return iq

    def auth(self, jid, password, iq=None, initstream=True, forceauth=None):
        """ auth against the xmpp server. """
        logging.warn('authing %s (%s)' % (jid, self.cfg.name))
        (name, host) = jid.split('@')
        rsrc = self.cfg['resource'] or self.cfg['resource'] or 'jsb';
        if self.cfg.nosasl: self.auth_nosasl(jid, password, iq)
        elif self.cfg.port == 5223: self.auth_sasl(jid, password, iq, False)
        else: self.auth_sasl(jid, password, iq, initstream)
        if self.failure: raise CannotAuth(self.failure.orig)
        self.sock.settimeout(60)
        self.sock.setblocking(1)
        
    def auth_methods(self, iq):
        if self.stopped: return []
        if not iq.orig: raise Exception("%s - can't detect auth method" % self.cfg.name)
        self.features = re.findall("<mechanism>(.*?)</mechanism>", iq.orig)
        return self.features

    def auth_sasl(self, jid, password, iq=None, initstream=True):
        if self.stopped: return
        iq2 = None
        if initstream: iq2 = self.init_stream('features') ; self.auth_methods(iq2)
        self.features.sort()
        for method in self.features:
            logging.debug("method is %s" % method)
            if method not in ["DIGEST-MD5", "PLAIN"]: logging.warn("skipping %s" % method) ; continue
            #if method not in ["PLAIN"]: logging.warn("skipping %s" % method) ; continue
            try:
                meth = getattr(self, "auth_%s" % method.replace("-", "_").lower())
                logging.debug("%s - calling auth method %s" % (self.cfg.name, method))
                meth(jid, password, iq2 or iq)
                self.authmethod = method
                logging.warn("%s - login method is %s" % (self.cfg.name, method))
                return method
            except CannotAuth: raise

    def auth_nosasl(self, jid, password, iq=None):
        """ auth against the xmpp server. """
        logging.debug('%s - authing %s' % (self.cfg.name, jid))
        (name, host) = jid.split('@')
        rsrc = self.cfg['resource'] or self.cfg['resource'] or 'jsb';
        iq = self._raw('<stream:stream to="%s" xmlns="jabber:client" xmlns:stream="http://etherx.jabber.org/streams">' % self.cfg.user.split('@')[1])
        time.sleep(1)
        resp = self.waiter("""<iq type='get'><query xmlns='jabber:iq:auth'><username>%s</username></query></iq>""" % name)
        self.waiter()
        if resp and resp.id:
            s = hashlib.new('SHA1')
            s.update(resp.id)
            s.update(password)
            d = s.hexdigest()
            iq = self.waiter("""<iq type='set'><query xmlns='jabber:iq:auth'><username>%s</username><digest>%s</digest><resource>%s</resource></query></iq>""" % (name, d, rsrc))
        else: iq = self.waiter("""<iq type='set'><query xmlns='jabber:iq:auth'><username>%s</username><resource>%s</resource><password>%s</password></query></iq>""" % (name, rsrc, password))

    def auth_digest_md5(self, jid, password, iq=None):
        (name, host) = jid.split('@')
        rsrc = self.cfg['resource'] or self.cfg['resource'] or 'jsb';
        resp = self.waiter("""<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='DIGEST-MD5'/>""", "challenge")
        challenge = re.findall(">(.*?)</challenge>", resp.orig)
        if not challenge: logging.error("%s - can't find challenge" % self.cfg.name)
        else: self.challenge = challenge[0] ; logging.debug("challenge is %s" % self.challenge)
        response = digestmd5.makeresp("xmpp/%s" % host, host, name, password, self.challenge)
        resp = self.waiter("<response xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>%s</response>" % response.replace("\n", ""))
        if self.failure: raise CannotAuth(self.failure.orig)
        #if "not-authorized" in str(resp.orig): raise Exception(resp.orig)
        if not self.cfg.openfire: self.waiter("<response xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
        self.waiter("<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' to='%s' version='1.0'>" % host)
        self.waiter("<iq type='set' id='bind_2'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>%s</resource></bind></iq>" % rsrc)
        self.waiter("<iq to='%s' type='set' id='sess_1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>" % host)

    def auth_plain(self, jid, password, iq=None):
        (name, host) = jid.split('@')
        if "hipchat" in host: jid = name
        elif not self.cfg.openfire: jid = jid.lower() + "/" + (self.cfg.resource or "bot")
        logging.debug("jid is %s" % jid)
        rsrc = self.cfg['resource'] or self.cfg['resource'] or 'jsb';
        if sys.version_info < (3, 0):
            user = bytes(jid)
            passw = bytes(password)
        else:
            user = bytes(jid, 'utf-8')
            passw = bytes(password, 'utf-8')
        auth = base64.b64encode('\x00' + user + '\x00' + passw).decode('utf-8')
        resp = self.waiter("""<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>%s</auth>""" % auth.replace("\n", ""))
        if self.failure: raise CannotAuth(self.failure.orig)
        #self.waiter("<response xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
        time.sleep(2)
        self.waiter("<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' to='%s' version='1.0'>" % host)
        self.waiter("<iq type='set' id='bind_2'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>%s</resource></bind></iq>" % rsrc)
        self.waiter("<iq to='%s' type='set' id='sess_1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>" % host)
        return resp

    def init_tls(self):
        logging.info("%s - starting TLS" % self.cfg.name)
        return self.waiter('<starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"/>')

    def dossl(self):
        """ enable ssl on the socket. """
        try: import ssl ; self.connection = ssl.wrap_socket(self.sock)
        except ImportError: self.connection = socket.ssl(self.sock)
        if self.connection: return True
        else: return False

    def logon(self):
        """ called upon logon on the server. """
        logging.warn("LOGGED ON!!")
        #print dir(self)
        #threadrunner.put(5, self.cfg.name, self._doprocess, ())

    def finish(self, data):
        """ finish processing of an xml stanza. """
        methods = []
        self.final['subelements'] = self.subelements
        for subelement in self.subelements:
            logging.debug("%s - %s" % (self.cfg.name, str(subelement)))
            for elem in subelement:
                logging.debug("%s - setting %s handler" % (self.cfg.name, elem))
                methods.append(self.getHandler(elem))
            for method in methods:
                if not method: continue
                try:
                    result = GozerEvent(subelement)
                    result.bot = self
                    result.orig = data
                    result.jabber = True
                    method(result) 
                except Exception, ex: handle_exception()
        if self.tags:
            element = self.tags[0]
            logging.debug("%s - setting element: %s" % (self.cfg.name, element))
        else: element = 'stream'
        self.final['element'] = element
        method = self.getHandler(element)
        if method:
            try:
                result = GozerEvent(self.final)
                result.bot = self
                result.orig = data
                result.jabber = True
                method(result) 
            except Exception, ex:
                handle_exception()
                result = {}
        else:
            logging.error("%s - can't find handler for %s" % (self.cfg.name, element))
            result = {}
        if result:
            self.final = {}
            self.reslist = []
            self.tags = []
            self.subelements = []
            self.buffer = ""
            return result

    def unknown_starttag(self,  tag, attrs):
        """ handler called by the self._parser on start of a unknown start tag. """
        xmlstream.NodeBuilder.unknown_starttag(self, tag, attrs)
        self.cur = tag
        if not self.tags: self.final.update(attrs)
        else: self.result[tag] = attrs
        self.tags.append(tag)
 
    def unknown_endtag(self,  tag):
        """ handler called by the self._parser on start of a unknown endtag. """
        xmlstream.NodeBuilder.unknown_endtag(self, tag)
        self.result = {}
        self.cur = u""
        
    def handle_data(self, data):
        """ node data handler. """
        xmlstream.NodeBuilder.handle_data(self, data)

    def dispatch(self, dom):
        """ dispatch a dom to the appropiate handler. """
        res = LazyDict()
        parentname = dom.getName()
        data = dom.getData()
        if data:
            self.final[parentname] = data
            if parentname == 'body': self.final['txt'] = data
        attrs = dom.getAttributes()
        ns = dom.getNamespace()
        res[parentname] = LazyDict()
        res[parentname]['data'] = data
        res[parentname].update(attrs) 
        if ns: res[parentname]['xmlns'] = ns
        for child in dom.getChildren():  
            name = child.getName()
            data = child.getData()
            if data: self.final[name] = data
            attrs = child.getAttributes()
            ns = child.getNamespace()
            res[parentname][name] = LazyDict()
            res[parentname][name]['data'] = data
            res[parentname][name].update(attrs) 
            self.final.update(attrs)
            if ns: res[parentname][name]['xmlns'] = ns
        self.subelements.append(res)

    def disconnectHandler(self, ex):
        """ handler called on disconnect. """
        logging.warn('disconnected: %s (%s)' % (str(ex), self.cfg.name))
        time.sleep(5)
        self.reconnect()