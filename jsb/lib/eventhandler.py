# jsb/eventhandler.py
#
#

""" event handler. use to dispatch function in main loop. """

## jsb imports

from jsb.utils.exception import handle_exception
from jsb.utils.locking import lockdec
from threads import start_new_thread

## basic imports

import Queue
import thread
import logging
import time

## locks

handlerlock = thread.allocate_lock()
locked = lockdec(handlerlock)

## classes

class EventHandler(object):

    """
        events are handled in 11 queues with different priorities:
        queue0 is tried first queue10 last.

    """

    def __init__(self):
        self.sortedlist = []
        try: self.queue = Queue.PriorityQueue()
        except AttributeError: self.queue = Queue.Queue()
        self.stopped = False
        self.running = False
        self.nooutput = False

    def start(self):
        """ start the eventhandler thread. """
        self.stopped = False
        if not self.running:
            start_new_thread(self.handleloop, ())
            self.running = True

    def handle_one(self):
        try:
            speed, todo = self.queue.get_nowait()
            self.dispatch(todo)
        except Queue.Empty: pass

    def stop(self):
        """ stop the eventhandler thread. """
        self.running = False
        self.stopped = True
        self.go.put('Yihaaa')

    def put(self, speed, func, *args, **kwargs):
        """ put item on the queue. """
        self.queue.put_nowait((speed, (func, args, kwargs)))

    def handleloop(self):
        """ thread that polls the queues for items to dispatch. """
        logging.warn('starting - %s ' % str(self))
        while not self.stopped:
            try:
                (speed, todo) = self.queue.get()
                logging.warn("running at speed %s - %s" % (speed, str(todo)))
                self.dispatch(todo)
            except Queue.Empty: time.sleep(0.1)
            except Exception, ex: handle_exception()
        logging.warn('stopping - %s' % str(self))

    runforever = handleloop

    def dispatch(self, todo):
        """ dispatch functions from provided queue. """
        try:
            (func, args, kwargs) = todo
            func(*args, **kwargs)
        except ValueError:
            try:
                (func, args) = todo
                func(*args)
            except ValueError:
                (func, ) = todo
                func()
        except: handle_exception()


## handler to use in main prog

mainhandler = EventHandler()
