# jsb/utils/trace.py
#
#

""" trace related functions """

## basic imports

import sys
import os

## defines

stopmarkers = ['jsb', 'myplugs', 'python2.5', 'python2.6', 'python2.7', 'python27', 'runtime', 'api', 'versions']

## calledfrom function

def calledfrom(frame):
    """ return the plugin name where given frame occured. """
    try:
        filename = frame.f_back.f_code.co_filename
        plugfile = filename.split(os.sep)
        if plugfile:
            mod = []
            for i in plugfile[::-1]:
                mod.append(i)
                if i in stopmarkers: break
            modstr = '.'.join(mod[::-1])[:-3]
            if 'handler_' in modstr: modstr = modstr.split('.')[-1]
    except AttributeError: modstr = None
    del frame
    return modstr

## callstack function

def callstack(frame):
    """ return callstack trace as a string. """
    result = []
    loopframe = frame
    marker = ""
    while 1:
        try:
            filename = loopframe.f_back.f_code.co_filename
            plugfile = filename.split(os.sep)
            if plugfile:
                mod = []
                for i in plugfile[::-1]:
                    mod.append(i)
                    if i in stopmarkers: marker = i ; break
                modstr = '.'.join(mod[::-1])[:-3]
                if 'handler_' in modstr: modstr = modstr.split('.')[-1]
                if not modstr: modstr = plugfile
            result.append("%s:%s" % (modstr, loopframe.f_back.f_lineno))
            loopframe = loopframe.f_back
        except: break
    del frame
    del loopframe
    return result

## where function

def where():
    return callstack(sys._getframe(0))

## whichmodule function

def whichmodule(depth=1):
    """ return filename:lineno of the module. """
    try:
        frame = sys._getframe(depth)
        plugfile = frame.f_back.f_code.co_filename[:-3].split('/')
        lineno = frame.f_back.f_lineno
        mod = []
        stop = False
        for i in plugfile[::-1]:
            if stop: break
            mod.append(i)
            for j in stopmarkers:
                if j in i: stop = True
        modstr = '.'.join(mod[::-1]) + ':' + str(lineno)
        #if 'handler_' in modstr or "python" in modstr: modstr = modstr.split('.')[-1]
    except AttributeError: modstr = None
    del frame
    return modstr

## whichplugin function

def whichplugin(depth=1):
    """ return filename:lineno of the module. """
    try:
        frame = sys._getframe(depth)
        plugfile = frame.f_back.f_code.co_filename[:-3].split('/')
        lineno = frame.f_back.f_lineno
        mod = []
        for i in plugfile[::-1]: 
            mod.append(i)
            if i in stopmarkers: break
        modstr = '.'.join(mod[::-1])
        if 'handler_' in modstr: modstr = modstr.split('.')[-1]
    except AttributeError: modstr = None
    del frame
    return modstr
