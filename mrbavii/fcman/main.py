#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-docstring,too-few-public-methods
""" File collection management utility. """

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright 2000-2026"
__license__ = "MIT"

# stderr should be for when a program error occurs
# - Any exception raised and not handled
# - A file unable to be opened, read or written

# stdout is used other times
# - since fcman is essentially a status program, status such as missing or
#   new items, bad dependencies, etc, should go to stdout
# - in verbose mode, non-error verbose information goes to stdout

import argparse
import os
import shutil
import signal
import sys

from . import util
from . import actions
from . import collection


# Only run on Python 3
if sys.version_info[0:2] < (3, 9):
    sys.exit("This program requires Python 3.9 or greater")


# modify the default keyboard interrupt exception
def sigint_print_and_exit(*args):
    sys.stderr.write("Aborted by Interrupt\n")
    sys.exit(-1)
signal.signal(signal.SIGINT, sigint_print_and_exit)


class Program(object):
    """ The main program object. """

    COMMITTED_FILE = "collection.xml"
    STAGED_FILE = "staging.xml"
    SAVES_DIR = "saves"
    BACKUP_DIR = "backups"
    EXPORTS_DIR = "exports"
    TAGS_DIR = "tags"

    def __init__(self):
        """ Initialize the program object. """
        self.collection = None
        self.iwd = None # The initial working directory before any chdir
        self.cwd = None
        self.dir = None # The collection directory (ie contains the collection xml files)
        self.root = None # The root directory (ie contains the files)
        self.options = None
        self.verbose = None
        self.writer = None

    @staticmethod
    def create_arg_parser():
        """ Create parser for main and actions """
        parser = argparse.ArgumentParser()

        # Base arguments
        parser.add_argument("-C", "--chdir", dest="chdir", default=None)
        parser.add_argument("-d", "--dir", dest="dir", default=".fcman")
        parser.add_argument("-r", "--root", dest="root", default=None)
        parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true")
        parser.add_argument("-w", "--walk", dest="walk", default=False, action="store_true")
        parser.add_argument("-c", "--committed", dest="committed", default=False, action="store_true")
        parser.add_argument("-x", "--no-recurse", dest="recurse", default=True, action="store_false")
        parser.set_defaults(action=None)

        # Add commands
        subparsers = parser.add_subparsers()
        commands = list(actions.ACTIONS[name] for name in sorted(actions.ACTIONS))

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
        self.verbose = verbose = util.VerboseChecker(options.verbose)
        self.writer = writer = util.StdStreamWriter()

        # Handle current directory
        self.iwd = os.getcwd()

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

        action.parse_arguments(options)
        if action.ACTION_LOAD_COLLECTION:
            # Load the collection if needed
            if not self.load_collection():
                return -1

        if options.committed and not action.ACTION_ALLOW_COMMITTED:
            writer.stderr.status("Action not allowed", "NOTALLOWED")
            return -1;

        def sigint_handler(*args):
            # if acton handles the signal, don't abort
            if action_obj.handle_sigint() != True:
                orig_handler(*args)

        action_obj = action(self)
        orig_handler = signal.signal(signal.SIGINT, sigint_handler)
        try:
            if not action_obj.run():
                return -1
        finally:
            signal.signal(signal.SIGINT, orig_handler)

        if self.collection and self.collection.dirty:
            if not options.committed: # don't save to staged file if we loaded the committed file
                self.collection.save(
                    os.path.join(
                        self.dir,
                        self.STAGED_FILE
                    )
                )
            else:
                writer.stderr.status("Save not allowed", "NOSAVE")
                return -1

        return 0

    def load_collection(self):
        """ Load the collection. """
        writer = self.writer
        verbose = self.verbose

        self.dir = self.find_dir()

        if not self.dir:
            writer.stderr.status("Collection not found", "NODIR")
            return False
        elif verbose:
            writer.stdout.status(self.dir, "COLLECTION")

        self.collection = collection.Collection.load(
            os.path.join(
                self.dir,
                self.STAGED_FILE if self.options.committed == False else self.COMMITTED_FILE
            )
        )

        # Set root
        if self.options.root:
            self.collection.set_root(self.options.root)
        else:
            self.collection.set_root(os.path.dirname(self.dir))

        if verbose:
            writer.stdout.status(self.collection.root, "ROOT")

        return True


    def find_dir(self):
        """ Use our options to find collection directory. """

        if not self.options.walk:
            # In this mode, dir directly specified
            dirname = os.path.normpath(self.options.dir)
            if os.path.isdir(dirname):
                return dirname
            return None

        # In walk mode, walk up the directory to find the collection dir
        head = self.cwd
        while head:
            dirname = os.path.join(head, self.options.dir)
            if os.path.isdir(dirname):
                return os.path.relpath(dirname) # relpath to keep it pretty

            (head, tail) = os.path.split(head)
            if not tail:
                break

        return None


def main():
    sys.exit(Program().main())
