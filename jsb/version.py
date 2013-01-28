# jsb/version.py
#
#

""" version related stuff. """

## jsb imports

from jsb.lib.config import getmainconfig

## basic imports

import os
import binascii

## defines

version = "0.91.0"
__version__ = version

## getversion function

def getversion(txt=""):
    """ return a version string. """
    return "JSONBOT %s DEVELOPMENT %s" % (version, txt)
