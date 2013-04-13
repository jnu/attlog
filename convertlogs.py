#! /usr/bin/env python
#coding=utf8

'''
./convertlogs.py [log1] ... [logN] > out.JSON

Take specified log files, parse them, and put one majestic JSON string to
stdout containing all the actionable information contained in these logs.

Copyright (c) 2013 Joseph Nudell
'''
__author__="Joseph Nudell"
__date__="$April 12, 2013$"


from attlog import attlog
from sys import argv, exit, stderr


def run(*files):
    masterlog = attlog()

    for fn in files:
        newlog = attlog(fn)

        masterlog += newlog

    print str(masterlog)


if __name__=='__main__':
    if len(argv)<2:
        print >>stderr, "Invalid arguments"
        print >>stderr, __doc__
        exit(1)

    run(*argv[1:])
