#!/usr/bin/env python3
# pylint: disable=too-many-lines,missing-docstring
""" File collection management utility. """

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright 2000-2019"
__license__ = "MIT"

# {{{1 Meta information

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"
__version__ = "20190303.1"


# stdout vs stderr

# stderr should be for when a program error occurs
# - Any exception raised and not handled
# - A file unable to be opened, read or written

# stdout is used other times
# - since fcman is essentially a status program, status such as missing or
#   new items, bad dependencies, etc, should go to stdout
# - in verbose mode, non-error verbose information goes to stdout


# Still need to add better error handling and printing


# Imports

import argparse
import os
import sys


from . import util
from . import actions 
from . import collection


# Checks

if sys.version_info[0:2] < (3, 2):
    sys.exit("This program requires Python 3.2 or greater")


# Program entry point

class VerboseChecker(object):
    """ A small class whose boolean value depends on verbose or a signal. """

    def __init__(self, verbose):
        self._verbose = verbose
        self._signalled = False

        try:
            import signal
            signal.signal(signal.SIGUSR1, self._signal)
        except ImportError:
            pass

    def _signal(self, sig, stack):
        # pylint: disable=unused-argument
        self._signalled = True

    def __bool__(self):
        result = self._verbose or self._signalled
        self._signalled = False
        return result

    __nonzero__ = __bool__


class Program(object):
    """ The main program object. """

    def __init__(self):
        """ Initialize the program object. """
        self.collection = None
        self.cwd = None
        self.file = None # The actual file loaded (options.file is the file to search for)
        self.options = None
        self.verbose = None
        self.writer = None


    def create_arg_parser(self):
        """ Create parser for main and actions """
        parser = argparse.ArgumentParser()

        # Base arguments
        parser.add_argument("-C", "--chdir", dest="chdir", default=None)
        parser.add_argument("-f", "--file", dest="file", default="fcman.xml")
        parser.add_argument("-r", "--root", dest="root", default=None)
        parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true")
        parser.add_argument("-w", "--walk", dest="walk", default=False, action="store_true")
        parser.add_argument("-x", "--no-recurse", dest="recurse", default=True, action="store_false")
        parser.add_argument("-b", "--backup", dest="backup", type=int, default=5, choices=range(0, 10))
        parser.set_defaults(action=None)

        # Add commands
        subparsers = parser.add_subparsers()

        commands = list(filter(lambda cls: cls.ACTION_NAME is not None, actions.Action.get_subclasses()))
        commands.sort(key=lambda cls: cls.ACTION_NAME)

        for i in commands:
            subparser = subparsers.add_parser(i.ACTION_NAME, help=i.ACTION_DESC)
            i.add_arguments(subparser)
            subparser.set_defaults(action=i)

        return parser

    def main(self):
        """ Run the program. """
        # Arguments
        parser = self.create_arg_parser()
        self.options = options = parser.parse_args()

        # Handle some objects
        self.verbose = verbose = VerboseChecker(options.verbose)
        self.writer = writer = util.StdStreamWriter()

        # Handle current directory
        if options.chdir:
            if verbose:
                writer.stdout.status(options.chdir, "CHDIR")
            os.chdir(options.chdir)

        self.cwd = os.getcwd()

        # Handle action
        action = options.action
        if action is None:
            parser.print_help()
            parser.exit()

        if action.ACTION_NAME != "init":
            # Load the collection if needed
            self.file = self.find_file()
            action.parse_arguments(options)

            if not self.file:
                writer.stderr.status("Collection not found", "NOFILE")
                return -1
            elif verbose:
                writer.stdout.status(self.file, "COLLECTION")

            self.collection = collection.Collection.load(self.file)

            if self.options.root:
                self.collection.set_root(self.options.root)
            elif self.collection.autoroot:
                self.collection.set_root(os.path.join(
                    os.path.dirname(self.file),
                    self.collection.autoroot
                ))
            else:
                self.collection.set_root(os.path.dirname(self.file))

            if verbose:
                writer.stdout.status(self.collection.root, "ROOT")

        if not action(self).run():
            return -1

        if self.collection and self.collection.dirty:
            self.save_backup()
            self.collection.save(self.file)

        return 0

    def save_backup(self):
        """ Save a backup based on the filename if requested. """
        filename = self.file
        backup = self.options.backup
        if backup == 0:
            return

        backup_concat = tuple(".{0}bak".format(i) for i in range(1, backup + 1))

        if os.path.exists(filename):
            # Remove last backup if it exists
            if os.path.exists(filename + backup_concat[-1]):
                os.remove(filename + backup_concat[-1])

            for i in range(len(backup_concat) - 2, -1, -1):
                if os.path.exists(filename + backup_concat[i]):
                    os.rename(
                        filename + backup_concat[i],
                        filename + backup_concat[i + 1]
                    )

            os.rename(filename, filename + backup_concat[0])


    def find_file(self):
        """ Use our options to find file. """
        if not self.options.walk:
            # In this mode, file directly specified
            filename = os.path.normpath(self.options.file)
            if os.path.isfile(filename):
                return filename
            return None

        # In walk mode, walk up the directory to find the file
        head = self.cwd
        while head:
            filename = os.path.join(head, self.options.file)
            if os.path.isfile(filename):
                return os.path.relpath(filename) # relpath to keep it pretty

            (head, tail) = os.path.split(head)
            if not tail:
                break

        return None


def main():
    sys.exit(Program().main())

