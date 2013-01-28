# jsb/utils/urlstats.py
#
#

""" persist stats of an url. """

## jsb imports

from jsb.lib.persist import Persist, PersistCollection
from jsb.lib.datadir import getdatadir
from jsb.utils.statdict import StatDict
from jsb.utils.name import stripname
from jsb.utils.url import striphtml, Url

## basic imports

import time
import logging
import os

## UrlStats class

class UrlStats(Persist):

    def __init__(self, url):
        self.scantime = 0
        self.url = Url(url)
        self.fname = getdatadir() + os.sep + 'spider' + os.sep + 'stats' + os.sep + stripname(url)
        Persist.__init__(self, self.fname)
        
    def get(self):
        content = geturl2(self.url)
        if content: return self.input(content)              

    def input(self, html):
        self.scantime = time.time()
        words = striphtml(html)
        words = words.replace("\n", "").split()
        stats = StatDict()
        for w in words:
            stats.upitem(w)
        self.data.url = self.url.url
        self.data.words = stats
        self.save()
        logging.warn("%s words found for %s" % (len(stats), self.url.url))
        return stats

    def stats(self):
        stats = StatDict(self.data.words)
        return stats

    