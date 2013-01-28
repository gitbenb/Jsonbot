# jsb/plugs/core/queues.py
#
#

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples

## queues-flush commands

def handle_queuesflush(bot, event):
    if bot.outqueue:
        while not bot.outqueue.empty():
            bot.outqueue.get_nowait()
    if bot.laterqueue:
        while not bot.laterqueue.empty():
            bot.laterqueue.get_nowait()
    event.reply("queus flushed")

cmnds.add("queues-flush", handle_queuesflush, "OPER")
examples.add("queues-flush", "flush queues on the bot", "queues-flush")

def handle_queuesbot(bot, event):
    event.reply("out: %s later: %s event: %s" % (bot.outqueue.qsize(), bot.laterqueue.qsize(), bot.eventqueue.qsize()))

cmnds.add("queues-bot", handle_queuesbot, "OPER")
examples.add("queues-bot", "show sizes of bots output queus", "queus-bot")

def handle_queuesrunners(bot, event):
    result = {}
    from jsb.lib.runner import allrunners
    for runner in allrunners:
        result[runner.name] = runner.size()
    event.reply("waiting in runner queues: ", result)

cmnds.add("queues-runners", handle_queuesrunners, "OPER")
examples.add("queues-runners", "show how many jobs are waiting", "queues-runners")
