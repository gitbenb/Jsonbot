# jsb/plugs/socket/fish.py
#
#

""" 
    Encrypts incoming and outgoing text using the FiSH encryption.

    Help on the fish command:

    event.reply("help                      -- shows this text")
    event.reply("keyx <nick>               -- Exchanges key")
    event.reply("key  <user|channel> <key> -- Set the key")
    event.reply("del  <user|channel>       -- Removes the key")

 """

__author__ = "Frank Spijkerman"

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.callbacks import callbacks
from jsb.lib.morphs import outputmorphs
from jsb.lib.morphs import inputmorphs
from jsb.lib.persiststate import PlugState
from jsb.utils.lazydict import LazyDict
from jsb.lib.persist import Persist
from jsb.utils.name import stripname
from jsb.lib.datadir import getdatadir
from jsb.utils.generic import getwho
from jsb.lib.users import getusers
from jsb.lib.errors import RequireError
from jsb.lib.persistconfig import PersistConfig

## basic imports

from string import strip
import os
import logging
import pickle

## check for pycrypto dependancy

try:
  import Crypto.Cipher.Blowfish
  import Crypto.Cipher.AES
except ImportError:
  raise RequireError("PyCrypto is required for FiSH. Please install this library if you want to use this plug")

## defines

cfg = PersistConfig()
cfg.define("enable", 0)

users = getusers()

## KeyStore class

class KeyStore(Persist):
  def __init__(self, keyname):
    Persist.__init__(self, getdatadir() + os.sep + 'keys' + os.sep + 'fish' + os.sep + stripname(keyname))

## make sure we get loaded

def dummycb(bot, event): pass
callbacks.add("START", dummycb)

## plugin

def init():
  """ Init """
  if cfg.enable:
    inputmorphs.add(fishin)
    outputmorphs.add(fishout)
    callbacks.add("NOTICE", dh1080_exchange)
    cmnds.add("fish", handle_fish, "OPER")
    examples.add("fish", "command that handles fish enrypting over IRC", "fish help")
  else: logging.warn("fish plugin is not enabled - use fish-cfg enable 1")

## fishin function

def fishin(text,event = None):
  if event and not (event.bottype == "irc" or event.bottype == "botbase"): return text
  if text.startswith('+OK '):
    target = None
    if event and event.channel and event.channel.startswith("#"):
      target = event.channel
    elif event:
      u  = users.getuser(event.userhost)
      if u: target = u.data.name

    if not target: return

    key = KeyStore(stripname(target))
    if not key.data.key:
      logging.debug("FiSHin: No key found for target %s" % target)
      return text

    try:
      #logging.debug("FiSHin raw: key: %s Raw: %s (%s)" % (key.data.key, text, target))
      text = decrypt(key.data.key, text)
      logging.debug("FiSHin raw decrypt: :%s:" % text)
      return text
    except (MalformedError, UnicodeDecodeError):
      return None 

  return text

## fishout function

def fishout(text, event):
  if event and not (event.bottype == "irc" or event.bottype == "botbase"): return text
  target = None
  if event and event.channel and event.channel.startswith("#"):
    target = event.channel
    if not target:
        u = users.getuser(event.userhost)
        if u: target = u.data.name
  
  if not target: return

  key = KeyStore(stripname(target))
  if not key.data.key:
    logging.debug("FiSHout: No key found for target %s" % target)
    return text 

  cipher = encrypt(key.data.key, text)
  return cipher

## encrypt function

def encrypt(key, text):
  b = Blowfish(key)
  return blowcrypt_pack(text, b)

## decrypt function

def decrypt(key, inp):
  b = Blowfish(key)
  return blowcrypt_unpack(inp, b)

## dh1080_exchange function

def dh1080_exchange(bot, ievent):
  # Not a known user, so also no key.
  u = users.getuser(ievent.userhost)
  if u: target = u.data.name
  else: return True
  if ievent.txt.startswith("DH1080_INIT "):
    logging.warn("FiSH: DH1080_INIT with %s" % target)
    key = KeyStore(stripname(target))

    dh = DH1080Ctx()
    if dh1080_unpack(ievent.txt, dh) != True:
      logging.warn("FiSH Key exchange failed!")
      return False

    key.data.key = dh1080_secret(dh)
    key.data.dh = pickle.dumps(dh)
    key.save()

    logging.debug("FiSH UserKey: %s Key: %s" % (ievent.txt[12:], key.data.key))
    ievent.bot.notice(ievent.nick, dh1080_pack(dh))

    return False

  if ievent.txt.startswith("DH1080_FINISH "):
    key = KeyStore(stripname(target))

    logging.warn("FiSH: DH1080_FINISH")
    dh = pickle.loads(key.data.dh)
    if dh1080_unpack(ievent.txt, dh) != True:
      logging.warn("FiSH Key exchange failed!")
      return False

    key.data.key = dh1080_secret(dh)
    key.save()
    
    logging.debug("FiSH: Key set for %s to %s" % (target, key.data.key)) 
    return False

  return True

## fish command

def handle_fish(bot, event):
  """ Handles the fish command """
  args = event.rest.rsplit(" ")
  if not args[0]: event.missing("<commands> [options,...]") ; return

  command = args[0]
  if command == 'help':
    event.reply("help                      -- shows this text")
    event.reply("keyx <nick>               -- Exchanges key")
    event.reply("key  <user|channel> <key> -- Set the key")
    event.reply("del  <user|channel>       -- Removes the key")
    return False

  if command == 'keyx':
    if len(args) != 2: event.missing("keyx <nick>"); return

    userhost = getwho(bot, args[1])
    if userhost == None: return

    user = users.getuser(userhost)
    if user == None:
        event.reply("Unable to exchange key with an unknown user")
        return 

    target = user.data.name
    if target == None: return

    logging.warn("FiSH: Key exchange with  %s (%s)" % (args[1], target))
    dh = DH1080Ctx()
    bot.notice(args[1], dh1080_pack(dh))

    key = KeyStore(stripname(target))
    key.data.dh = pickle.dumps(dh)
    key.save()
    
  if command == 'key':
    if len(args) != 3: event.missing("key <user|channel> <key>"); return
    key = KeyStore(stripname(args[1]))
    key.data.key = args[2]
    key.save()
    event.reply("Stored key for %s" % args[1])

  if command == 'del':
    if len(args) != 2: event.missing("del <user|channel>"); return
    key = KeyStore(stripname(args[1]))

    if not key.data.key: 
      event.reply("No key found for %s" % args[1]); return

    key.data.key=""
    key.data.dh=""
    key.save()
    event.reply("Deleted key %s" % args[1])
  


#### irccrypt module

##
## irccrypt.py - various cryptographic methods for IRC + IRCSRP reference
## implementation.
##
## Copyright (c) 2009, Bjorn Edstrom <be@bjrn.se>
## 
## Permission to use, copy, modify, and distribute this software for any
## purpose with or without fee is hereby granted, provided that the above
## copyright notice and this permission notice appear in all copies.
## 
## THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
## WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
## MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
## ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
## WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
## ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
## OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
##

""" Library for various common cryptographic methods used on IRC.
Currently supports:

* blowcrypt - as used by for Fish et al.
* Mircryption-CBC - an improvement of blowcrypt using the CBC mode.
* DH1080 - A Diffie Hellman key exchange adapted for IRC usage.

Additionally, implements the new IRCSRP method as described at
http://www.bjrn.se/ircsrp

Sample usage:

blowcrypt, Fish etc
-------------------

>>> b = Blowfish("password")
>>> blowcrypt_pack("Hi bob!", b)
'+OK BRurM1bWPZ1.'
>>> blowcrypt_unpack(_, b)
'Hi bob!'

Mircryption-CBC
---------------

>>> b = BlowfishCBC("keyTest")
>>> mircryption_cbc_pack("12345678", b)
'+OK *oXql/CRQbadX+5kl68g1uQ=='

DH1080
------

>>> alice = DH1080Ctx()
>>> bob = DH1080Ctx()
>>> dh1080_pack(alice)
'DH1080_INIT qStH1LjBpb47s0XY80W9e3efrVSh2Qfq...<snip>
>>> dh1080_unpack(_, bob)
True
>>> dh1080_pack(bob)
'DH1080_FINISH mjyk//fqPoEwp5JfbJtzDmlfpzmtME...<snip>
>>> dh1080_unpack(_, alice)
True
>>> dh1080_secret(alice)
'tfu4Qysoy56OYeckat1HpJWzi+tJVx/cm+Svzb6eunQ'
>>> dh1080_secret(bob)
'tfu4Qysoy56OYeckat1HpJWzi+tJVx/cm+Svzb6eunQ'

For more information, see the accompanying article at http://www.bjrn.se/
"""

___author__ = "Bjorn Edstrom <be@bjrn.se>"
___date__ = "2009-01-25"
___version__ = "0.1.1"

import base64
import hashlib
from math import log
try:
    import Crypto.Cipher.Blowfish
    import Crypto.Cipher.AES
except ImportError:
    print "This module requires PyCrypto / The Python Cryptographic Toolkit."
    print "Get it from http://www.dlitz.net/software/pycrypto/."
    raise
from os import urandom
import struct
import time

##
## Preliminaries.
##

class MalformedError(Exception):
    pass


def sha256(s):
    """sha256"""
    return hashlib.sha256(s).digest()


def int2bytes(n):
    """Integer to variable length big endian."""
    if n == 0:
        return '\x00'
    b = ''
    while n:
        b = chr(n % 256) + b
        n /= 256
    return b


def bytes2int(b):
    """Variable length big endian to integer."""
    n = 0
    for p in b:
        n *= 256
        n += ord(p)
    return n


# FIXME! Only usable for really small a with b near 16^x.
def randint(a, b):
    """Random integer in [a,b]."""
    bits = int(log(b, 2) + 1) / 8
    candidate = 0
    while True:
        candidate = bytes2int(urandom(bits))
        if a <= candidate <= b:
            break
    assert a <= candidate <= b
    return candidate


def padto(msg, length):
    """Pads 'msg' with zeroes until it's length is divisible by 'length'.
    If the length of msg is already a multiple of 'length', does nothing."""
    L = len(msg)
    if L % length:
        msg += '\x00' * (length - L % length)
    assert len(msg) % length == 0
    return msg


def xorstring(a, b, blocksize): # Slow.
    """xor string a and b, both of length blocksize."""
    xored = ''
    for i in xrange(blocksize):
        xored += chr(ord(a[i]) ^ ord(b[i]))  
    return xored


def cbc_encrypt(func, data, blocksize):
    """The CBC mode. The randomy generated IV is prefixed to the ciphertext.
    'func' is a function that encrypts data in ECB mode. 'data' is the
    plaintext. 'blocksize' is the block size of the cipher."""
    assert len(data) % blocksize == 0
    
    IV = urandom(blocksize)
    assert len(IV) == blocksize
    
    ciphertext = IV
    for block_index in xrange(len(data) / blocksize):
        xored = xorstring(data, IV, blocksize)
        enc = func(xored)
        
        ciphertext += enc
        IV = enc
        data = data[blocksize:]

    assert len(ciphertext) % blocksize == 0
    return ciphertext


def cbc_decrypt(func, data, blocksize):
    """See cbc_encrypt."""
    assert len(data) % blocksize == 0
    
    IV = data[0:blocksize]
    data = data[blocksize:]

    plaintext = ''
    for block_index in xrange(len(data) / blocksize):
        temp = func(data[0:blocksize])
        temp2 = xorstring(temp, IV, blocksize)
        plaintext += temp2
        IV = data[0:blocksize]
        data = data[blocksize:]
    
    assert len(plaintext) % blocksize == 0
    return plaintext


class Blowfish:
    
    def __init__(self, key=None):
        if key:
            self.blowfish = Crypto.Cipher.Blowfish.new(key)

    def decrypt(self, data):
        return self.blowfish.decrypt(data)
    
    def encrypt(self, data):
        return self.blowfish.encrypt(data)


class BlowfishCBC:
    
    def __init__(self, key=None):
        if key:
            self.blowfish = Crypto.Cipher.Blowfish.new(key)

    def decrypt(self, data):
        return cbc_decrypt(self.blowfish.decrypt, data, 8)
    
    def encrypt(self, data):
        return cbc_encrypt(self.blowfish.encrypt, data, 8)


class AESCBC:
    
    def __init__(self, key):
        self.aes = Crypto.Cipher.AES.new(key)

    def decrypt(self, data):
        return cbc_decrypt(self.aes.decrypt, data, 16)
    
    def encrypt(self, data):
        return cbc_encrypt(self.aes.encrypt, data, 16)


##
## blowcrypt, Fish etc.
##

# XXX: Unstable.
def blowcrypt_b64encode(s):
    """A non-standard base64-encode."""
    B64 = "./0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    res = ''
    while s:
        left, right = struct.unpack('>LL', s[:8])
        for i in xrange(6):
            res += B64[right & 0x3f]
            right >>= 6
        for i in xrange(6):
            res += B64[left & 0x3f]
            left >>= 6
        s = s[8:]
    return res


def blowcrypt_b64decode(s):
    """A non-standard base64-decode."""
    B64 = "./0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    res = ''
    while s:
        left, right = 0, 0
        for i, p in enumerate(s[0:6]):
            right |= B64.index(p) << (i * 6)
        for i, p in enumerate(s[6:12]):
            left |= B64.index(p) << (i * 6)
        res += struct.pack('>LL', left, right)
        s = s[12:]
    return res


def blowcrypt_pack(msg, cipher):
    """."""
    return '+OK ' + blowcrypt_b64encode(cipher.encrypt(padto(msg, 8)))


def blowcrypt_unpack(msg, cipher):
    """."""
    if not (msg.startswith('+OK ') or msg.startswith('mcps ')):
        raise ValueError
    _, rest = msg.split(' ', 1)
    if len(rest) < 12:
        raise MalformedError

    try:
        raw = blowcrypt_b64decode(padto(rest, 12))
    except TypeError:
        raise MalformedError
    if not raw:
        raise MalformedError

    try:
        plain = cipher.decrypt(raw)
    except ValueError:
        raise MalformedError
    
    return plain.strip('\x00')


##
## Mircryption-CBC
##

def mircryption_cbc_pack(msg, cipher):
    """."""
    padded = padto(msg, 8)
    return '+OK *' + base64.b64encode(cipher.encrypt(padded))


def mircryption_cbc_unpack(msg, cipher):
    """."""
    if not msg.startswith('+OK *') or msg.startswith('mcps *'):
        raise ValueError

    try:
        _, coded = msg.split('*', 1)
        raw = base64.b64decode(coded)
    except TypeError:
        raise MalformedError
    if not raw:
        raise MalformedError

    try:
        padded = cipher.decrypt(raw)
    except ValueError:
        raise MalformedError
    if not padded:
        raise MalformedError

    plain = padded.strip("\x00")
    return plain


##
## DH1080
##

g_dh1080 = 2
p_dh1080 = int('FBE1022E23D213E8ACFA9AE8B9DFAD'
               'A3EA6B7AC7A7B7E95AB5EB2DF85892'
               '1FEADE95E6AC7BE7DE6ADBAB8A783E'
               '7AF7A7FA6A2B7BEB1E72EAE2B72F9F'
               'A2BFB2A2EFBEFAC868BADB3E828FA8'
               'BADFADA3E4CC1BE7E8AFE85E9698A7'
               '83EB68FA07A77AB6AD7BEB618ACF9C'
               'A2897EB28A6189EFA07AB99A8A7FA9'
               'AE299EFA7BA66DEAFEFBEFBF0B7D8B', 16)
q_dh1080 = (p_dh1080 - 1) / 2 


# XXX: It is probably possible to implement dh1080 base64 using Pythons own, by
# considering padding, lengths etc. The dh1080 implementation is basically the
# standard one but with the padding character '=' removed. A trailing 'A'
# is also added sometimes.
def dh1080_b64encode(s):
    """A non-standard base64-encode."""
    b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    d = [0]*len(s)*2

    L = len(s) * 8
    m = 0x80
    i, j, k, t = 0, 0, 0, 0
    while i < L:
        if ord(s[i >> 3]) & m:
            t |= 1
        j += 1
        m >>= 1
        if not m:
            m = 0x80
        if not j % 6:
            d[k] = b64[t]
            t &= 0
            k += 1
        t <<= 1
        t %= 0x100
        #
        i += 1
    m = 5 - j % 6
    t <<= m
    t %= 0x100
    if m:
        d[k] = b64[t]
        k += 1
    d[k] = 0
    res = ''
    for q in d:
        if q == 0:
            break
        res += q
    return res


def dh1080_b64decode(s):
    """A non-standard base64-encode."""
    b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    buf = [0]*256
    for i in range(64):
        buf[ord(b64[i])] = i

    L = len(s)
    if L < 2:
        raise ValueError
    for i in reversed(range(L-1)):
        if buf[ord(s[i])] == 0:
            L -= 1
        else:
            break
    if L < 2:
        raise ValueError

    d = [0]*L
    i, k = 0, 0
    while True:
        i += 1
        if k + 1 < L:
            d[i-1] = buf[ord(s[k])] << 2
            d[i-1] %= 0x100
        else:
            break
        k += 1
        if k < L:
            d[i-1] |= buf[ord(s[k])] >> 4
        else:
            break
        i += 1
        if k + 1 < L:
            d[i-1] = buf[ord(s[k])] << 4
            d[i-1] %= 0x100
        else:
            break
        k += 1
        if k < L:
            d[i-1] |= buf[ord(s[k])] >> 2
        else:
            break
        i += 1
        if k + 1 < L:
            d[i-1] = buf[ord(s[k])] << 6
            d[i-1] %= 0x100
        else:
            break
        k += 1
        if k < L:
            d[i-1] |= buf[ord(s[k])] % 0x100
        else:
            break
        k += 1
    return ''.join(map(chr, d[0:i-1]))


def dh_validate_public(public, q, p):
    """See RFC 2631 section 2.1.5."""
    return 1 == pow(public, q, p)


class DH1080Ctx:
    """DH1080 context."""
    def __init__(self):
        self.public = 0
        self.private = 0
        self.secret = 0
        self.state = 0
        
        bits = 1080
        while True:
            self.private = bytes2int(urandom(bits/8))
            self.public = pow(g_dh1080, self.private, p_dh1080)
            if 2 <= self.public <= p_dh1080 - 1 and \
               dh_validate_public(self.public, q_dh1080, p_dh1080) == 1:
                break


def dh1080_pack(ctx):
    """."""
    cmd = None
    if ctx.state == 0:
        ctx.state = 1
        cmd = "DH1080_INIT "
    else:
        cmd = "DH1080_FINISH "
    return cmd + dh1080_b64encode(int2bytes(ctx.public))


def dh1080_unpack(msg, ctx):
    """."""
    if not msg.startswith("DH1080_"):
        raise ValueError

    invalidmsg = "Key does not validate per RFC 2631. This check is not " \
                 "performed by any DH1080 implementation, so we use the key " \
                 "anyway. See RFC 2785 for more details."

    if ctx.state == 0:
        if not msg.startswith("DH1080_INIT "):
            raise MalformedError
        ctx.state = 1
        try:
            cmd, public_raw = msg.split(' ', 1)
            public = bytes2int(dh1080_b64decode(public_raw))

            if not 1 < public < p_dh1080:
                raise MalformedError
            
            if not dh_validate_public(public, q_dh1080, p_dh1080):
                print invalidmsg
                
            ctx.secret = pow(public, ctx.private, p_dh1080)
        except:
            raise MalformedError
        
    elif ctx.state == 1:
        if not msg.startswith("DH1080_FINISH "):
            raise MalformedError
        ctx.state = 1
        try:
            cmd, public_raw = msg.split(' ', 1)
            public = bytes2int(dh1080_b64decode(public_raw))

            if not 1 < public < p_dh1080:
                raise MalformedError

            if not dh_validate_public(public, q_dh1080, p_dh1080):
                print invalidmsg
            
            ctx.secret = pow(public, ctx.private, p_dh1080)
        except:
            raise MalformedError

    return True
        

def dh1080_secret(ctx):
    """."""
    if ctx.secret == 0:
        raise ValueError
    return dh1080_b64encode(sha256(int2bytes(ctx.secret)))


##
## IRCSRP version 1
##

modp14 = """
      FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
      29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
      EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
      E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
      EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE45B3D
      C2007CB8 A163BF05 98DA4836 1C55D39A 69163FA8 FD24CF5F
      83655D23 DCA3AD96 1C62F356 208552BB 9ED52907 7096966D
      670C354E 4ABC9804 F1746C08 CA18217C 32905E46 2E36CE3B
      E39E772C 180E8603 9B2783A2 EC07A28F B5C55DF0 6F4C52C9
      DE2BCBF6 95581718 3995497C EA956AE5 15D22618 98FA0510
      15728E5A 8AACAA68 FFFFFFFF FFFFFFFF
"""
g = 2
N = int(modp14.replace(' ', '').replace('\n', ''), 16)
H = sha256

class IRCSRPExchange:
    def __init__(self):
        self.status = 0
        self.I = 0
        self.x = 0
        self.a = 0
        self.A = 0
        self.b = 0
        self.B = 0
        self.S = 0
        self.u = 0
        self.K = 0
        self.M1 = 0
        self.M2 = 0

class IRCSRPUsers:
    def __init__(self):
        # Store info about friends here, such as
        # self.db["alice"] = alice_s, alice_v
        self.db = {}

        # Temporary storage for exchange. The dict key is derived from the
        # IRC message, not the username.
        self.others = {}
        
    def get_details(self, username):
        s, v = self.db[username]
        return s, v


class IRCSRPCtx:
    """Everyone has one of these."""
    def __init__(self, dave=False):
        self.cipher = None
        self.status = 0
        self.username = ''
        self.password = ''
        self.sessionkey = ''
        self.ex = IRCSRPExchange()
        self.isdave = dave
        if dave:
            self.users = IRCSRPUsers()
            
    def set_key(self, key):
        assert len(key) == 32
        self.sessionkey = key
        self.cipher = AESCBC(key)
        if self.isdave:
            padded = padto('\xffKEY' + key, 16)
            return '+aes ' + base64.b64encode(self.cipher.encrypt(padded))
        return None


def ircsrp_generate(username, password):
    """Alice runs this and gives the result to Dave."""
    s = urandom(32)
    x = bytes2int(H(s + username + password))
    v = pow(g, x, N)
    return s, v


def ircsrp_pack(ctx, msg):
    """Encrypt message for channel."""
    times = struct.pack(">L", int(time.time()))
    infos = chr(len(ctx.username)) + ctx.username + times
    padded = padto('M' + infos + msg, 16)
    return '+aes ' + base64.b64encode(ctx.cipher.encrypt(padded))


def ircsrp_unpack(ctx, msg):
    """Decrypt message for channel."""
    if not msg.startswith('+aes '):
        raise ValueError

    try:
        _, coded = msg.split(' ', 1)
        raw = base64.b64decode(coded)
    except TypeError:
        raise MalformedError
    if not raw:
        raise MalformedError

    try:
        padded = ctx.cipher.decrypt(raw)
    except ValueError:
        raise MalformedError
    if not padded:
        raise MalformedError

    plain = padded.strip("\x00")

    # New key?
    if plain.startswith('\xffKEY'):
        new = plain[4:]
        if not len(new) == 32:
            raise MalformedError
        ctx.sessionkey = new
        ctx.cipher = AESCBC(new)
        print "*** Session key changed to:", repr(new)
        return None

    if not plain[0] == 'M':
        raise ValueError

    usernamelen = ord(plain[1])
    username = plain[2:2+usernamelen]
    timestampstr = plain[2+usernamelen:4+2+usernamelen]
    timestamp = struct.unpack(">L", timestampstr)[0]

    print "*** Sent by username:", username
    print "*** Sent at time:", time.ctime(timestamp)
        
    return plain[4+2+usernamelen:]


def ircsrp_exchange(ctx, msg=None, sender=None):
    """The key exchange, for NOTICE handler. Parameters are:
    
    :<sender>!user@host.com NOTICE :<msg>\r\n
    """
    b64 = lambda s: base64.b64encode(s)
    b64i = lambda i: b64(int2bytes(i))
    unb64 = lambda s: base64.b64decode(s)
    unb64i = lambda s: bytes2int(unb64(s))

    cmd, arg = '', ''
    if msg:
        cmd, arg = msg.split(' ', 1)
        if not cmd.startswith('+srp'):
            raise ValueError
        cmd = cmd[5:].strip(' ')
    
    # Alice initiates the exchange.
    if msg == None and sender == None and ctx.ex.status == 0:
        
        ctx.ex.status = 1
        
        return "+srpa0 " + ctx.username

    # Dave
    if cmd == '0':
        
        ex = ctx.users.others[sender] = IRCSRPExchange()

        I = ex.I = arg
        s, v = ex.s, ex.v = ctx.users.get_details(I)
        b = ex.b = randint(2, N-1)
        B = ex.B = (3*v + pow(g, b, N)) % N

        return "+srpa1 " + b64(s + int2bytes(B))

    # Alice
    if cmd == '1' and ctx.ex.status == 1:

        args = unb64(arg)
        s = ctx.ex.s = args[:32]
        B = ctx.ex.B = bytes2int(args[32:])
        if B % N == 0:
            raise ValueError
        
        a = ctx.ex.a = randint(2, N-1)
        A = ctx.ex.A = pow(g, a, N)
        x = ctx.ex.x = bytes2int(H(s + ctx.username + ctx.password))
        
        u = ctx.ex.u = bytes2int(H(int2bytes(A) + int2bytes(B)))
        S = ctx.ex.S = pow(B - 3*pow(g, x, N), (a + u*x) % N, N)
        K = ctx.ex.K = H(int2bytes(S))
        M1 = ctx.ex.M1 = H(int2bytes(A) + int2bytes(B) + int2bytes(S))

        ctx.ex.status = 2
        
        return "+srpa2 " + b64(M1 + int2bytes(A))

    # Dave
    if cmd == '2':
        
        if not sender in ctx.users.others:
            raise ValueError
        ex = ctx.users.others[sender]

        args = unb64(arg)
        M1 = args[:32]
        A = bytes2int(args[32:])
        if A % N == 0:
            raise ValueError

        u = bytes2int(H(int2bytes(A) + int2bytes(ex.B)))
        S = pow(A * pow(ex.v, u, N), ex.b, N)
        K = H(int2bytes(S))
        M2 = H(int2bytes(A) + M1 + int2bytes(S))

        M1ver = H(int2bytes(A) + int2bytes(ex.B) + int2bytes(S))
        if M1 != M1ver:
            raise ValueError

        aes = AESCBC(K)

        del ctx.users.others[sender]
        
        return "+srpa3 " + b64(aes.encrypt(ctx.sessionkey + M2))

    # Alice
    if cmd == '3' and ctx.ex.status == 2:

        cipher = unb64(arg)
        aes = AESCBC(ctx.ex.K)
        plain = aes.decrypt(cipher)

        sessionkey = plain[:32]
        M2 = plain[32:]

        M2ver = H(int2bytes(ctx.ex.A) + ctx.ex.M1 + int2bytes(ctx.ex.S))
        if M2 != M2ver:
            raise ValueError

        ctx.sessionkey = sessionkey
        ctx.cipher = AESCBC(sessionkey)

        print "*** Session key is:", repr(sessionkey)
        
        ctx.ex.status = 0
        
        return True

    raise ValueError


# 2*37*22312747
