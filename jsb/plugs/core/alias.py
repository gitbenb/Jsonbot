# jsb/plugs/core/alias.py
#
#

""" 
    this alias plugin allows aliases for commands to be added. aliases are in
    the form of <alias> -> <command> .. aliases to aliases are not allowed, 
    aliases are per channel.

"""

## gozerbot imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples

## basic imports

import os

## alias-search command

def handle_aliassearch(bot, ievent):
    """ arguments: <what> - search aliases. """
    try: what = ievent.rest
    except IndexError:
        ievent.missing('<what>')
        return
    result = []
    res = []
    aliases = ievent.chan.data.aliases
    if aliases:
        for i, j in aliases.iteritems():
            if what in i or what in j: result.append((i, j))
    if not result: ievent.reply('no %s found' % what)
    else:
        for i in result: res.append("%s => %s" % i)
        ievent.reply("aliases matching %s: " % what, res)

cmnds.add('alias-search', handle_aliassearch, 'USER')
examples.add('alias-search', 'search aliases',' alias-search web')

## alias command

def handle_aliasset(bot, ievent):
    """ arguments: <from> <to> - set alias. """
    try: (aliasfrom, aliasto) = (ievent.args[0], ' '.join(ievent.args[1:]))
    except IndexError:
        ievent.missing('<from> <to>')
        return
    if not aliasto:
        ievent.missing('<from> <to>')
        return
    if cmnds.has_key(aliasfrom):
        ievent.reply('command with same name already exists.')
        return
    aliases = ievent.chan.data.aliases
    if not aliases: ievent.chan.data.aliases = aliases = {}
    if aliases.has_key(aliasto):
        ievent.reply("can't alias an alias")
        return
    ievent.chan.data.aliases[aliasfrom] = aliasto
    ievent.chan.save()
    ievent.reply('alias added')

cmnds.add('alias', handle_aliasset, 'USER', allowqueue=False)
examples.add('alias', 'alias <alias> <command> .. define alias', 'alias ll list')

## alias-makeglobal command

def handle_aliasmakeglobal(bot, ievent):
    """ no arguments -  make channel aliases global. """
    aliases = ievent.chan.data.aliases
    if not aliases: ievent.chan.data.aliases = aliases = {}
    from jsb.lib.aliases import getaliases, savealiases
    galiases = getaliases()
    galiases.update(ievent.chan.data.aliases)
    savealiases()
    ievent.reply('global aliases updated')

cmnds.add('alias-makeglobal', handle_aliasmakeglobal, 'OPER', allowqueue=False)
examples.add('alias-makeglobal', 'push channel specific aliases into the global aliases', 'alias-makeglobal')

## alias-del command

def handle_delalias(bot, ievent):
    """ arguments: <aliasfrom> - delete alias. """
    try: what = ievent.args[0]
    except IndexError:
        ievent.missing('<what>')
        return
    aliases = ievent.chan.data.aliases
    try: 
        if aliases:
            del aliases[what]
            ievent.chan.save()
            ievent.reply('alias deleted')
            return
    except KeyError: pass
    ievent.reply('there is no %s alias' % what)

cmnds.add('alias-del', handle_delalias, 'USER')
examples.add('alias-del', 'alias-del <what> .. delete alias', 'alias-del ll')

## aliases command

def handle_aliasget(bot, ievent):
    """ not arguments - show aliases. (per user) """
    aliases = ievent.chan.data.aliases
    if aliases: ievent.reply("channel aliases: %s" % str(aliases))
    from jsb.lib.aliases import getaliases
    aliases = getaliases()
    if aliases: ievent.reply("global aliases: %s" % aliases.tojson())

cmnds.add('aliases', handle_aliasget, 'OPER')
examples.add('aliases', 'aliases <what> .. get aliases', 'aliases')
