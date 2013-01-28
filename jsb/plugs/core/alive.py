# jsb/plugs/core/alive.py
#
#

""" checking when the bot has last accessed files. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.persist import PersistCollection
from jsb.lib.datadir import getdatadir
from jsb.contrib.natural.file import accessed

## basic imports

import os

## alive command

def handle_alive(bot, event):
    if len(event.args) < 1: event.missing("<plugname> [<search>]") ; return
    if event.options and event.options.all:
        collection = PersistCollection(getdatadir())
    else: collection = PersistCollection(getdatadir() + os.sep + 'plugs')
    filenames = collection.filenames(event.args)
    result = {}
    for fn in filenames: result[fn.split(os.sep)[-1]] = accessed(fn)
    event.reply("alive results: ", result)

cmnds.add("alive", handle_alive, ["OPER", ])
examples.add("alive", "show last access time of files in the data directory", "alive rss")
