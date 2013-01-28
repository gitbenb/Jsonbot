# jsb/errors.py
#
#

""" jsb exceptions. """

## jsb imports

from jsb.utils.trace import calledfrom

## basic imports

import sys

## exceptions


class JsonBotError(Exception):
    pass

class WrongFileName(JsonBotError):
    pass

class NoErrorSet(JsonBotError):
    pass

class CantLogon(JsonBotError):
    pass

class UserIgnored(JsonBotError):
    pass

class URLNotEnabled(JsonBotError):
    pass

class JSONParseError(JsonBotError):
    pass

class StreamError(JsonBotError):
    pass

class RequireError(JsonBotError):
    pass

class CannotAuth(JsonBotError):
    pass

class NotConnected(JsonBotError):
    pass

class FeedAlreadyExists(JsonBotError):
     pass

class MemcachedCounterError(JsonBotError):
     pass

class NoSuchFile(JsonBotError):
     pass

class BotNotEnabled(JsonBotError):
     pass

class NoProperDigest(JsonBotError):
     pass

class NoChannelProvided(JsonBotError):
    pass

class NoInput(JsonBotError):
    pass

class PropertyIgnored(JsonBotError):
    pass

class BotNotSetInEvent(JsonBotError):
    pass

class FeedProviderError(JsonBotError):
    pass

class CantSaveConfig(JsonBotError):
    pass

class NoOwnerSet(JsonBotError):
    pass

class NameNotSet(JsonBotError):
    pass

class NoSuchUser(JsonBotError):
    pass

class NoUserProvided(JsonBotError):
    pass

class NoSuchBotType(JsonBotError):
    pass

class NoChannelSet(JsonBotError):
    pass

class NoSuchCommand(JsonBotError):
    pass

class NoSuchChannel(JsonBotError):
    pass

class NoSuchPlugin(JsonBotError):
    pass

class NoOwnerSet(JsonBotError):
    pass

class PlugsNotConnected(JsonBotError):
    pass

class NoEventProvided(JsonBotError):
    pass

class WrongType(JsonBotError):
    pass
