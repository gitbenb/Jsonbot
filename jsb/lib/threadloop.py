# jsb/threadloop.py
#
#

""" class to implement start/stoppable threads. """

## lib imports

from jsb.utils.exception import handle_exception
from threads import start_new_thread, getname

## basic imports

import Queue
import time
import logging
from collections import deque

## defines

threadloops = []

## ThreadLoop class

class ThreadLoop(object):

    """ implement startable/stoppable threads. """

    def __init__(self, name="", queue=None, *args, **kwargs):
        self.name = name
        self.stopped = False
        self.running = False
        self.outs = []
        try: self.queue = queue or Queue.PriorityQueue()
        except AttributeError: self.queue = queue or Queue.Queue()
        self.nowrunning = "none"
        self.lastiter = 0
        self.nrtimes = 0

    def _loop(self):
        """ the threadloops loop. """
        logging.debug('starting %s' % getname(self))
        self.running = True
        nrempty = 0
        while not self.stopped:
            try: (speed, data) = self.queue.get()
            except (IndexError, Queue.Empty):
                if self.stopped: break
                continue
            if self.stopped: break
            if not data: break
            try: self.handle(*data) ; self.lastiter = time.time()
            except Exception, ex: handle_exception()
            time.sleep(0.01)
            self.nrtimes += 1
            
        self.running = False
        logging.warn('stopping %s' % getname(self))
        
    def put(self, speed, *data):
        """ put data on task queue. """
        self.queue.put((speed, data))

    def start(self):
        """ start the thread. """
        if not self.running and not self.stopped:
            self.running = True
            if not self in threadloops: threadloops.append(self)
            return start_new_thread(self._loop, ())

    def stop(self):
        """ stop the thread. """
        self.stopped = True
        self.running = False
        self.put(0, None)
        if self in threadloops: threadloops.remove(self)

    def handle(self, *args, **kwargs):
        """ overload this. """
        pass

    def waiting(self):
        return self.queue.qsize()

## RunnerLoop class

class RunnerLoop(ThreadLoop):

    """ dedicated threadloop for bot commands/callbacks. """

    def put(self, speed, *data):
        """ put data on task queue. """
        self.queue.put((speed, data))

    def _loop(self):
        """ runner loop. """
        logging.debug('starting %s' % self.name)
        self.running = True
        while not self.stopped:
            try:
                speed, data = self.queue.get()
                if self.stopped: break
                if not data: break
                self.handle(speed, data)
                self.lastiter = time.time()
            except (IndexError, Queue.Empty): continue
            except Exception, ex: handle_exception()
            time.sleep(0.01)
            self.nrtimes += 1
        self.running = False
        logging.debug('%s - stopping threadloop' % self.name)

class TimedLoop(ThreadLoop):

    """ threadloop that sleeps x seconds before executing. """

    def __init__(self, name, sleepsec=300, *args, **kwargs):
        ThreadLoop.__init__(self, name, *args, **kwargs)
        self.sleepsec = sleepsec

    def _loop(self):
        """ timed loop. sleep a while. """
        logging.warn('%s - starting timedloop (%s seconds)' % (self.name, self.sleepsec))
        self.stopped = False
        self.running = True
        while not self.stopped:
            time.sleep(self.sleepsec)
            if self.stopped: break
            try: self.handle() ; self.lastiter = time.time()
            except Exception, ex: handle_exception()
            self.nrtimes += 1
        self.running = False
        logging.warn('%s - stopping timedloop' % self.name)
