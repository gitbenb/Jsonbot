# jsb/channelbase.py
#
#

""" provide a base class for channels. """

## jsb imports

from jsb.utils.name import stripname
from jsb.utils.lazydict import LazyDict
from jsb.lib.persist import Persist
from jsb.lib.datadir import getdatadir
from jsb.utils.trace import whichmodule
from jsb.lib.errors import NoChannelProvided, NoChannelSet

## basic imports

import time
import os
import logging

## classes

class ChannelBase(Persist):

    """ Base class for all channel objects. """

    def __init__(self, id, botname=None, type="notset", needexist=False):
        if not id: raise NoChannelSet()
        if not botname: Persist.__init__(self, getdatadir() + os.sep + 'channels' + os.sep + stripname(id), needexist=needexist)
        else: Persist.__init__(self, getdatadir() + os.sep + 'fleet' + os.sep + stripname(botname) + os.sep + 'channels' + os.sep + stripname(id), needexist=needexist)
        self.id = id
        self.type = type
        self.lastmodified = time.time()
        self.data.id = id
        self.data.enable = self.data.enable or False
        self.data.ops = self.data.ops or []
        self.data.taglist = self.data.taglist or []
        self.data.silentcommands = self.data.silentcommands or []
        self.data.allowcommands = self.data.allowcommands or []
        self.data.feeds = self.data.feeds or []
        self.data.forwards = self.data.forwards or []
        self.data.allowwatch = self.data.allowwatch or []
        self.data.watched = self.data.watched or []
        self.data.passwords = self.data.passwords or {}
        self.data.cc = self.data.cc or ""
        self.data.nick = self.data.nick or "jsb"
        self.data.key = self.data.key or ""
        self.data.denyplug = self.data.denyplug or []
        self.data.createdfrom = whichmodule()
        self.data.cacheindex = 0
        self.data.tokens = self.data.tokens or []
        self.data.webchannels = self.data.webchannels or []

    def setpass(self, type, key):
        """ set channel password based on type. """
        self.data.passwords[type] = key
        self.save()

    def getpass(self, type='IRC'):
        """ get password based of type. """
        try:
            return self.data.passwords[type]
        except KeyError: return

    def delpass(self, type='IRC'):
        """ delete password. """
        try:
            del self.data.passwords[type]
            self.save()
            return True
        except KeyError: return

    def parse(self, event):
        """
            parse an event for channel related data and constuct the 
            channel with it. Overload this.

        """
        pass

