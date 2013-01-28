# jsb/cache.py
#
#

""" jsb cache provding get, set and delete functions. """

## jsb imports

from jsb.utils.lazydict import LazyDict


## basic imports

import logging

## defines

cache = LazyDict()

## functions

def get(name, namespace=""):
    """ get data from the cache. """
    global cache
    try: 
        #logging.debug("cache - returning %s" % cache[name])
        return cache[name]
    except KeyError: pass

def set(name, item, timeout=0, namespace=""):
    """ set data in the cache. """
    #logging.debug("cache - setting %s to %s" % (name, str(item)))
    global cache
    cache[name] = item

def delete(name, namespace=""):
    """ delete data from the cache. """
    try:
        global cache
        del cache[name]
        logging.warn("cache - deleted %s" % name)
        return True
    except KeyError: return False

def size():
    return len(cache)
