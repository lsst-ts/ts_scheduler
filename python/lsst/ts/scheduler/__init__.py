# -*- coding: utf-8 -*-

__author__ = 'Francisco Delgado'
__email__ = 'fdelgado@lsst.org'

try:
    from .version import *
except ModuleNotFoundError:
    __version__ = "?"

from .driver import *
from .scheduler_csc import *
