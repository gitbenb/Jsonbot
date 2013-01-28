# jsb/plugs/common/tour.py
#
#

""" do a tour of the bot. """

eventlist = ["!welcome", "JSONBOT provides functionality through the use of plugins, you can use the !list comamnd to see what plugins are available =>", "!list"]

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples

## basic imports

import time

## dotour command

def handle_dotour(bot, event):
    if event.user.state.data.notour: event.reply("the tour is disabled for %s" % event.userhost) ; return
    event.reply("will say something every 5 seconds. you can disable this tour by typing !set notour 1")
    time.sleep(5)
    for txt in eventlist:
        if event.user.state.data.notour: break 
        if txt.startswith("!"):
            e = bot.make_event(event.userhost, event.channel, txt[1:], 0, event)
            e.execute()
        else: event.reply(txt)
        time.sleep(5)
    event.done()

cmnds.add("tour", handle_dotour, ["OPER", "USER", "GUEST"], threaded=True)
examples.add("tour", "show a tour of the bot", "tour")