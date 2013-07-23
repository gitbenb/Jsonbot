# jsb/runner.py
#
#

""" threads management to run jobs. """

## jsb imports

from jsb.lib.threads import getname, start_new_thread, start_bot_command
from jsb.utils.exception import handle_exception
from jsb.utils.locking import locked, lockdec
from jsb.utils.lockmanager import rlockmanager, lockmanager
from jsb.utils.generic import waitevents
from jsb.utils.trace import callstack, whichmodule
from jsb.lib.threadloop import RunnerLoop
from jsb.lib.callbacks import callbacks
from jsb.lib.errors import URLNotEnabled
from jsb.utils.statdict import StatDict
from jsb.utils.locking import lockdec

## basic imports

import Queue
import time
import thread
import random
import logging
import sys

## defines

stats = StatDict()

## locks

startlock = thread.allocate_lock()
startlocked = lockdec(startlock)

## Runner class

class Runner(RunnerLoop):

    """
        a runner is a thread with a queue on which jobs can be pushed. 
        jobs scheduled should not take too long since only one job can 
        be executed in a Runner at the same time.

    """

    def __init__(self, name="runner", doready=True):
        RunnerLoop.__init__(self, name)
        self.working = False
        self.starttime = time.time()
        self.elapsed = self.starttime
        self.finished = time.time()
        self.doready = doready
        self.nowrunning = ""
        self.longrunning = []
        self.shortrunning = []
        
    def handle(self, speed, argslist):
        """ schedule a job. """
        self.working = True
        try:
            try: descr, func, args, kwargs = argslist
            except ValueError:
                try:
                    descr, func, args = argslist
                    kwargs = {}
                except ValueError:
                    descr, func = argslist
                    args = ()
                    kwargs = {}                  
            self.nowrunning = getname(func) + " - " + descr 
            logging.info('running %s - %s- %s' % (descr, str(func), args))
            self.starttime = time.time()
            result = func(*args, **kwargs)
            self.finished = time.time()
            self.elapsed = self.finished - self.starttime
            if self.elapsed > 5:
                logging.debug('ALERT %s %s job taking too long: %s seconds' % (descr, str(func), self.elapsed))
            stats.upitem(self.nowrunning)
            stats.upitem(self.name)
            logstr = "finished %s - %s (%s)" % (self.nowrunning, result or "no result", self.elapsed)
            logging.warn(logstr)
            time.sleep(0.005)
        except Exception, ex: handle_exception() ; result = str(ex)
        self.working = False

    def done(self, event):
        try: int(event.cbtype)
        except ValueError:
            if event.cbtype not in ['TICK', 'PING', 'NOTICE', 'TICK60']: logging.warn(str(event.cbtype))
                            
## BotEventRunner class

class BotEventRunner(Runner):

    def handle(self, speed, args):
        """ schedule a bot command. """
        try:
            descr, func, bot, ievent = args
            self.nowrunning = getname(func) + " - " + descr 
            self.starttime = time.time()
            if not ievent.nolog: logging.info("event handler is %s" % str(func))
            if self.nowrunning in self.longrunning and not self.nowrunning in self.shortrunning: 
                logging.warn("putting %s on longrunner" % self.nowrunning)
                longrunner.put(ievent.speed or speed, descr, func, bot, ievent)
                return
            self.working = True
            try: result = func(bot, ievent)
            except URLNotEnabled, ex: logging.warn("urls fetching is disabled (%s)" % ievent.usercmnd) ; return str(ex)
            self.finished = time.time()
            self.elapsed = self.finished - self.starttime
            if self.elapsed > 5:
                if self.nowrunning not in self.longrunning: self.longrunning.append(self.nowrunning)
                try: self.shortrunning.remove(self.nowrunning)
                except ValueError: pass
                if not ievent.nolog: logging.debug('ALERT %s %s job taking too long: %s seconds' % (descr, str(func), self.elapsed))
            stats.upitem(self.nowrunning)
            stats.upitem(self.name)
            time.sleep(0.005)
            logstr = "finished %s - %s - %s (%s)" % (self.nowrunning, result or "no result", ievent.cbtype, self.elapsed)
            if ievent.cbtype not in ['TICK', 'PING', 'NOTICE', 'TICK60']: logging.info(logstr)
        except Exception, ex:
            handle_exception()
            result = str(ex)
        self.working = False

class LongRunner(Runner):

    def handle(self, speed, args):
        """ schedule a bot command. """
        try:
            descr, func, bot, ievent = args
            self.nowrunning = getname(func) + " - " + descr 
            self.starttime = time.time()
            if not ievent.nolog: logging.debug("long event handler is %s" % str(func))
            self.working = True
            result = func(bot, ievent)
            self.elapsed = time.time() - self.starttime
            if self.elapsed < 1 and self.nowrunning not in self.shortrunning: self.shortrunning.append(self.nowrunning)
            stats.upitem(self.nowrunning)
            stats.upitem(self.name)
            logstr = "finished %s - %s - %s (%s)" % (self.nowrunning, result or "no result", ievent.cbtype, self.elapsed)
            if ievent.cbtype not in ['TICK', 'PING', 'NOTICE', 'TICK60']: logging.warn(logstr)
        except Exception, ex:
            handle_exception()
            result = str(ex)
        self.working = False


## Runners class

class Runners(object):

    """ runners is a collection of runner objects. """

    def __init__(self, name, max=100, runnertype=Runner, doready=True):
        self.name = name
        self.max = max
        self.runners = []
        self.runnertype = runnertype
        self.doready = doready

    def names(self):
        return [getname(runner.name) for runner in self.runners]

    def size(self):
        qsize = [runner.queue.qsize() for runner in self.runners]
        return "%s/%s" % (qsize, len(self.runners))

    def runnersizes(self):
        """ return sizes of runner objects. """
        result = []
        for runner in self.runners: result.append("%s - %s" % (runner.queue.qsize(), runner.name))
        return result

    def stop(self):
        """ stop runners. """
        for runner in self.runners: runner.stop()

    def start(self):
        """ overload this if needed. """
        pass

    def putnew(self, speed, *data):
        runner = self.makenew()
        runner.put(speed, *data)
        if self.runners: self.cleanup()
 
    @startlocked
    def put(self, speed, *data):
        """ put a job on a free runner.  """
        got = False
        for runner in self.runners:
            if runner.queue.empty():
                runner.put(speed, *data)
                got = True
                break
        if not got:
            runner = self.makenew()
            runner.put(speed, *data)
              
    def running(self):
        """ return list of running jobs. """
        result = []
        for runner in self.runners:
            if runner.working: result.append(runner.nowrunning)
        return result

    def makenew(self):
        """ create a new runner. """
        runner = None
        if len(self.runners) < self.max:
            runner = self.runnertype(self.name + "-" + str(len(self.runners)))
            runner.start()
            self.runners.append(runner)
        else: runner = random.choice(self.runners)
        return runner

    @startlocked
    def cleanup(self):
        """ clean up idle runners. """
        r = []
        for runner in self.runners:
            if runner.queue.empty(): r.append(runner)
        if not r: return
        for runner in r: runner.stop()
        for runner in r:
            try: self.runners.remove(runner)
            except ValueError: pass
        logging.info("%s - cleaned %s" %  (self.name, [item.nowrunning for item in r]))
        logging.debug("%s - now running: %s" % (self.name, self.size()))
        
## show runner status

def runner_status():
    print cmndrunner.runnersizes()
    print callbackrunner.runnersizes()


## global runners

cmndrunner = defaultrunner = Runners("default", 50, BotEventRunner) 
longrunner = Runners("long", 80, LongRunner)
callbackrunner = Runners("callback", 70, BotEventRunner)
waitrunner = Runners("wait", 20, BotEventRunner)
apirunner = Runners("api", 20, BotEventRunner)
threadrunner = Runners("threads", 50, Runner)

allrunners = [cmndrunner, longrunner, callbackrunner, waitrunner, apirunner, threadrunner]

## cleanup 

def runnercleanup(bot, event):
    for runner in allrunners: runner.cleanup()

callbacks.add("TICK60", runnercleanup)

def size():
    return "cmnd: %s - callbacks: %s - wait: %s - long: %s - api: %s thread: %s" % (cmndrunner.size(), callbackrunner.size(), waitrunner.size(), longrunner.size(), apirunner.size(), threadrunner.size())
