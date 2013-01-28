# jsb/utils/statdict.py
#
#

""" dictionairy to keep stats. """

## jsb imports

from jsb.utils.lazydict import LazyDict
from jsb.lib.errors import WrongType

## classes

class StatDict(LazyDict):

    """ dictionary to hold stats """

    def __iadd__(self, b):
        if not type(b) == StatDict: raise WrongType(type(b))
        for key, value in b.iteritems():
            self.upitem(key, value)
        return self

    def set(self, item, value):
        """ set item to value """
        self[item] = value

    def upitem(self, item, value=1):
        """ increase item """
        if not self.has_key(item):
            self[item] = value
            return
        self[item] += value

    def downitem(self, item, value=1):
        """ decrease item """
        if not self.has_key(item):
            self[item] = value
            return
        self[item] -= value

    def top(self, start=1, limit=None):
        """ return highest items """
        result = []
        for item, value in self.iteritems():
            if value >= start: result.append((item, value))
        result.sort(lambda b, a: cmp(a[1], b[1]))
        if limit: result =  result[:limit]
        return result

    def down(self, end=100, limit=None):
        """ return lowest items """
        result = []
        for item, value in self.iteritems():
            if value <= end: result.append((item, value))
        result.sort(lambda a, b: cmp(a[1], b[1]))
        if limit: return result[:limit]
        else: return result

    def countdictkeys(self, d):
        """ count all keys of a dict. """
        for key in d:
            self.upitem(key)

    def countdictvalues(self, d):
        """ count all keys of a dict. """
        for key, value in d.iteritems():
            print key, value
            try: self.upitem(value)
            except TypeError: pass
