# jsb/db/__init__.py
#
#

""" database interface """

__copyright__ = 'this file is in the public domain'

## jsb imports

from jsb.lib.config import getmainconfig
from jsb.utils.locking import lockdec
from jsb.utils.generic import tolatin1
from jsb.utils.exception import handle_exception
from jsb.lib.datadir import getdatadir

## basic imports

import thread
import os
import time
import types
import logging

## locks

dblock = thread.allocate_lock()
dblocked = lockdec(dblock)

## Db class

class Db(object):

    """ this class implements a database connection. it connects to the 
        database on initialisation.
    """

    def __init__(self, dbname=None, dbhost=None, dbuser=None, dbpasswd=None, dbtype=None, ddir=None, doconnect=True):
        self.datadir = ddir or getdatadir()
        self.datadir = self.datadir + os.sep + "db" + os.sep
        if hasattr(os, 'mkdir'):
            if not os.path.isdir(self.datadir):
                try: os.mkdir(self.datadir)
                except OSError: pass
        cfg = getmainconfig()
        self.dbname = dbname or cfg.dbname
        if not self.dbname: raise Exception("no db name")
        self.dbhost = dbhost or cfg.dbhost or ""
        self.dbuser = dbuser or cfg.dbuser or ""
        self.dbpasswd = dbpasswd or cfg.dbpasswd or ""
        self.connection = None
        self.timeout = 15
        self.dbtype = dbtype or cfg.dbtype or 'sqlite'
        self.error = ""
        if doconnect: self.connect()

    def connect(self, timeout=15):
        """ connect to the database. """
        self.timeout = timeout
        logging.debug("connecting to %s (%s)" % (self.dbname, self.dbtype))
        if self.dbtype == 'mysql':
            try: import MySQLdb
            except ImportError, ex: logging.error(str(ex)) ; self.error = str(ex) ; return 0
            self.connection = MySQLdb.connect(db=self.dbname, host=self.dbhost, user=self.dbuser, passwd=self.dbpasswd, connect_timeout=self.timeout, charset='utf8')
        elif 'sqlite' in self.dbtype:
            try:
                import sqlite3
                self.connection = sqlite3.connect(self.datadir + os.sep + self.dbname, check_same_thread=False)
            except ImportError:
                import sqlite
                self.connection = sqlite.connect(self.datadir + os.sep + self.dbname)
        elif self.dbtype == 'postgres':
            import psycopg2
            logging.warn('NOTE THAT POSTGRES IS NOT FULLY SUPPORTED')
            self.connection = psycopg2.connect(database=self.dbname, host=self.dbhost, user=self.dbuser, password=self.dbpasswd)
        else:
            logging.error('unknown database type %s' % self.dbtype)
            return 0
        logging.warn("%s is ok (%s)" % (self.dbname, self.dbtype))
        return 1

    def reconnect(self):
        """ reconnect to the database server. """
        self.error = ""
        return self.connect()

    @dblocked
    def executescript(self, txt):
        cursor = self.cursor()
        if 'sqlite' in self.dbtype: cursor.executescript(txt)
        #self.commit()

    @dblocked
    def execute(self, execstr, args=None):
        """ execute string on database. """
        time.sleep(0.001)
        result = None
        if self.error: loggging.error("db error was set to %s" % self.error) ; return None
        execstr = execstr.strip()
        if self.dbtype == 'sqlite': execstr = execstr.replace('%s', '?')
        if self.dbtype == 'mysql':
            try: self.ping()
            except AttributeError: self.reconnect()                
            except Exception, ex:
                logging.warn('reconnecting')
                try: self.reconnect()
                except Exception, ex: logging.error('failed reconnect: %s' % str(ex)) ; return
        logging.debug('exec %s %s' % (execstr, args))
        cursor = self.cursor()
        nr = 0
        try:
            if args:
                if type(args) == tuple or type(args) == list: nr = cursor.execute(execstr, args)
                else: nr = cursor.execute(execstr, (args, ))
            else: nr = cursor.execute(execstr)
        except:
            if self.dbtype == 'postgres': cursor.execute(""" ROLLBACK """)
            if 'sqlite' in self.dbtype: cursor.close() ; del cursor
            raise
        # see if we need to commit the query
        got = False
        if execstr.startswith('INSERT'): nr = cursor.lastrowid or nr ; got = True
        elif execstr.startswith('UPDATE'): nr = cursor.rowcount ; got = True
        elif execstr.startswith('DELETE'): nr = cursor.rowcount ; got = True
        if got: self.commit()
        # determine rownr
        if self.dbtype == 'sqlite' and not got and type(nr) != types.IntType:
            nr = cursor.rowcount or cursor.lastrowid
            if nr == -1: nr = 0
        # fetch results
        result = None
        try:
            result = cursor.fetchall()
            if not result: result = nr
        except Exception, ex:
            if 'no results to fetch' in str(ex): pass
            else: handle_exception()
            result = nr
        cursor.close()
        return result

    def cursor(self):
        """ return cursor to the database. """
        return self.connection.cursor()

    def commit(self):
        """ do a commit on the datase. """
        self.connection.commit()

    def ping(self):
        """ do a ping. """
        return self.connection.ping()

    def close(self):
        """ close database. """
        if 'sqlite' in self.dbtype: self.commit()
        self.connection.close()

    def define(self, definestr):
        try: self.executescript(definestr)
        except Exception, ex:
            if 'already exists' in str(ex): pass
            else: handle_exception()
