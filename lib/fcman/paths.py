# This file is placed in the public domain.

""" This module contains path information for the application. """

import os as _os

def init(prefix):
    """ Initialize the program paths information. """

    g = globals()

    g['prefix'] = prefix
    g['datadir'] = _os.path.join(prefix, 'share', 'fcman')
    g['docdir'] = _os.path.join(prefix, 'share', 'doc', 'fcman')


