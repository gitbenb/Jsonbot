# jsb/plugs/core/reverse.py
#
# 

""" reverse pipeline or reverse <txt>. """

__copyright__ = 'this file is in the public domain'
__author__ = 'Hans van Kranenburg <hans@knorrie.org>'

## jsb imports

from jsb.utils.generic import waitforqueue
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples

## basic imports

import types
import time

## reverse command

def handle_reverse(bot, ievent):
    """ arguments: [<string>] - reverse string or use in a pipeline. """
    if ievent.rest: ievent.reply(ievent.rest[::-1]) ; return
    if True or ievent.prev:
        #ievent.prev.wait()
        ievent.reply("results: ", reversed(ievent.inqueue))
        return

cmnds.add('reverse', handle_reverse, ['USER', 'GUEST'])
examples.add('reverse', 'reverse text or pipeline', '1) reverse gozerbot 2) list ! reverse')
