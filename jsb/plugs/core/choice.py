# jsb/plugs/core/choice.py
#
#

""" the choice command can be used with a string or in a pipeline. """

## jsb imports

from jsb.utils.generic import waitforqueue
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples

## basic imports

import random
import time

## choice command

def handle_choice(bot, ievent):
    """ arguments: [<space seperated strings>] - make a random choice out of different words or list elements. when used in a pipeline will choose from that. """ 
    result = []
    if ievent.prev:
         ievent.prev.wait()
         result = ievent.inqueue
    else: result = ievent.args
    if result: ievent.reply(random.choice(result))
    else: ievent.reply("no result")

cmnds.add('choice', handle_choice, ['OPER', 'USER', 'GUEST'])
examples.add('choice', 'make a random choice', '1) choice a b c 2) list ! choice')
