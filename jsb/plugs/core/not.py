# jsb/plugs/core/not.py
#
#

""" negative grep. """

## jsb imports

from jsb.lib.examples import examples
from jsb.lib.commands import cmnds
from jsb.utils.generic import waitforqueue

## basic imports

import getopt
import re
import time

## not command

def handle_not(bot, ievent):
    """ no arguments - negative grep, use this command in a pipeline. """
    try: (options, rest) = getopt.getopt(ievent.args, 'r')
    except getopt.GetoptError, ex:
        ievent.reply(str(ex))
        return
    if not ievent.inqueue: time.sleep(0.5)
    doregex = False
    for i, j in options:
        if i == '-r': doregex = True
    res = []
    if doregex:
        try: reg = re.compile(' '.join(rest))
        except Exception, ex:
            ievent.reply("can't compile regex: %s" % str(ex))
            return
        for i in ievent.inqueue:
            if not re.search(reg, i): res.append(i)
    else:
        for i in ievent.inqueue:
            if ievent.rest not in str(i): res.append(i)
    if not res: ievent.reply('no result')
    else: ievent.reply("results: ", res)

cmnds.add('not', handle_not, ['OPER', 'USER', 'GUEST'])
examples.add('not', 'reverse grep used in pipelines', 'list ! not todo')
