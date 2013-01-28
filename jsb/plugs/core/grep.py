# jsb/plugs/core/grep.py
#
#

""" grep the output of bot comamnds. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.utils.generic import waitforqueue
from jsb.lib.examples import examples

## basic imports

import getopt
import re
import time

## grep command

def handle_grep(bot, ievent):
    """ no arguments - grep the result list, use this command in a pipeline. """
    if not ievent.rest: ievent.reply('grep <txt>') ; return
    try: (options, rest) = getopt.getopt(ievent.args, 'riv')
    except getopt.GetoptError, ex: ievent.reply(str(ex)) ; return
    doregex = False
    docasein = False
    doinvert = False
    for i, j in options:
        if i == '-r': doregex = True
        if i == '-i': docasein = True
        if i == '-v': doinvert = True
    res = []
    #if ievent.prev: ievent.prev.wait()
    target = ievent.inqueue   
    if doregex:
        try:
            if docasein: reg = re.compile(' '.join(rest), re.I)
            else: reg = re.compile(' '.join(rest))
        except Exception, ex:
            ievent.reply("can't compile regex: %s" % str(ex))
            return
        if doinvert:
            for i in target:
                if not re.search(reg, i): res.append(i)
        else:
            for i in target:
                if re.search(reg, i): res.append(i)
    else:
        if docasein: what = ' '.join(rest).lower()
        elif doinvert: what = ' '.join(rest)
        else: what = ievent.rest
        for i in target:
            if docasein:
                if what in str(i.lower()): res.append(i)
            elif doinvert:
                if what not in str(i): res.append(i)
            else:
                if what in str(i): res.append(i)
    if not res: ievent.reply('no result')
    else: ievent.reply('results: ', res)

cmnds.add('grep', handle_grep, ['OPER', 'USER', 'GUEST'])
examples.add('grep', 'grep the output of a command', 'list ! grep core')
