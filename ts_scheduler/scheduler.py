#!/usr/bin/env python

import sys

from schedulerMain import Main

if (__name__ == '__main__'):
    try:
        log_file = sys.argv[1]
    except IndexError:
        log_file = ""

    scheduler = Main(log_file)

    scheduler.run()

    sys.exit(0)
