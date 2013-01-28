# jsb/threads.py
#
#

""" own threading wrapper. """

## jsb imports

from jsb.utils.exception import handle_exception

## basic imports

import threading
import re
import time
import thread
import logging
import uuid

## defines

# RE to determine thread name

classre = re.compile("class\s+\'(\S+)\'", re.I)
methodre = re.compile('method\s+(\S+)', re.I)
funcre = re.compile('function\s+(\S+)', re.I)
objectre = re.compile('<(\S+)\s+object at (\S+)>', re.I)

## Botcommand class

class Botcommand(threading.Thread):

    """ thread for running bot commands. """

    def __init__(self, group, target, name, args, kwargs):
        threading.Thread.__init__(self, None, target, name, args, kwargs)
        self.name = name
        self.bot = args[0]
        self.ievent = args[1]
        self.setDaemon(True)

    def run(self):
        """ run the bot command. """
        try:
            self.bot.benice()
            result = threading.Thread.run(self)
            self.ievent.ready()
        except Exception, ex:
            handle_exception(self.ievent)
            time.sleep(1)

## Thr class

class Thr(threading.Thread):

    """ thread wrapper. """

    def __init__(self, group, target, name, args, kwargs):
        threading.Thread.__init__(self, None, target, name, args, kwargs)
        self.setDaemon(True)
        self.name = name

    def run(self):
        """ run the thread. """
        try:
            logging.debug('threads - running thread %s' % self.name) 
            threading.Thread.run(self)
        except Exception, ex:
            handle_exception()
            time.sleep(1)

## getname function

def getname(func):
    """ get name of function/method. """
    name = str(func)
    cls = re.search(classre, name)
    if cls: name = cls.group(1) ; name = name.split(".")[-1]
    else:
        method = re.search(methodre, name)
        if method: name = method.group(1)
        else: 
            function = re.search(funcre, name)
            if function: name = function.group(1)
            else:
                object = re.search(objectre, name)
                if object: name = "%s-%s" % (object.group(1), object.group(2))
                else: name = str(func)
    return name

## start_new_thread function

def start_new_thread(func, arglist, kwargs={}):
    """ start a new thread .. set name to function/method name."""
    if not kwargs: kwargs = {}
    if not 'name' in kwargs:
        name = getname(func)
        if not name: name = str(func)
    else: name = kwargs['name']
    try:
        thread = Thr(None, target=func, name=name, args=arglist, kwargs=kwargs)
        thread.start()
        return thread
    except Exception, ex:
        if "can't start" in str(ex): logging.error("threads - thread space is exhausted - can't start thread %s" % name)
        handle_exception()
        time.sleep(3)

## start_bot_cpmmand function

def start_bot_command(func, arglist, kwargs={}):
    """ start a new thread .. set name to function/method name. """
    if not kwargs: kwargs = {}
    try:
        name = getname(func)
        if not name: name = 'noname'
        thread = Botcommand(group=None, target=func, name=name, args=arglist, kwargs=kwargs)
        thread.start()
        return thread
    except:
        handle_exception()
        time.sleep(1)


def threaded(func):
    """ threading decorator. """
    def threadedfunc(*args, **kwargs):
        start_new_thread(func, args, kwargs)
    return threadedfunc
