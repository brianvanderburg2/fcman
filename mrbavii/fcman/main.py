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
import toml
import traceback

from . import actions
from . import collection
from . import config
from . import consts
from . import errors
from . import util


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

    def __init__(self):
        """ Initialize the program object. """
        self.collections = {}
        self.config = None

        self.iwd = None # initial working directory (before chdir)
        self.cwd = None # current working direction (after chdir)
        self.options = None
        self.verbose = None
        self.writer = None
        self.topdir = None
        self.statedir = None

    @staticmethod
    def create_arg_parser():
        """ Create parser for main and actions """
        parser = argparse.ArgumentParser()

        # Base arguments
        parser.add_argument("-C", "--chdir", dest="chdir", default=None)
        parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true")

        group = parser.add_mutually_exclusive_group()
        group.add_argument("-r", "--raw", dest="raw", default=False, action="store_true")
        group.add_argument("-w", "--walk", dest="walk", default=False, action="store_true")

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

        if action.ACTION_LOAD_STATE:
            if not self.load_state():
                return -1

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

        return 0


    #---------------------------------------------------------------------------
    # State related code
    #---------------------------------------------------------------------------

    def load_state(self):
        """ Load the config, state dir, etc """
        writer = self.writer
        verbose = self.verbose

        if not self.find_statedir():
            writer.stderr.status(".", "STATENOTFOUND")
            return False
        elif verbose:
            writer.stdout.status(self.statedir, "STATEDIR")

        self.config = config.Config(
            os.path.join(self.statedir, consts.MAIN_CONFIG_FILE)
        )

        return True

    def find_statedir(self):
        """ Find our state directory and update topdirectory as needed """
        self.statedir = self._find_statedir()
        if self.statedir is None:
            self.topdir = None
            return False

        if self.options.raw:
            self.topdir = self.statedir
        else:
            self.topdir = os.path.dirname(self.statedir)

        return True

    def _find_statedir(self):
        """ Use our options to find state directory. """
        if not self.options.walk:
            dirname = os.path.normpath(consts.STATEDIR_RAW if self.options.raw else consts.STATEDIR_NORMAL)
            if os.path.isdir(dirname) and os.path.isfile(os.path.join(dirname, consts.MAIN_CONFIG_FILE)):
                return os.path.relpath(dirname) # relpath to keep it pretty
            return None

        # In walk mode, walk up the directory to find the collection dir
        head = self.cwd
        while head:
            dirname = os.path.join(head, consts.STATEDIR_NORMAL)
            if os.path.isdir(dirname) and os.path.isfile(os.path.join(dirname, consts.MAIN_CONFIG_FILE)):
                return os.path.relpath(dirname) # relpath to keep it pretty

            (head, tail) = os.path.split(head)
            if not tail:
                break

        return None

    #---------------------------------------------------------------------------
    # Collection related code
    #---------------------------------------------------------------------------

    def load_collection(self, name):
        """ Load the collection. """
        writer = self.writer
        verbose = self.verbose

        if not util.valid_collection_name(name):
            writer.stderr.status(name, "INVALID")
            return None

        subdir = os.path.join(self.statedir, name)
        if not os.path.isdir(subdir):
            writer.stderr.status(name, "NOTFOUND")
            return None

        # Load collection and config
        coll = collection.Collection.load(
            os.path.join(subdir, consts.COLLECTION_FILE)
        )

        cfg = config.Config(
            os.path.join(subdir, consts.COLLECTION_CONFIG_FILE)
        )

        # Set config
        coll.set_config(cfg)

        # Set root
        coll.set_root(
            os.path.join(
                self.topdir,
                cfg.get_value("config.root", ".").replace("/", os.sep)
            )
        )

        if verbose:
            writer.stdout.status(name, "LOADED")
            writer.stdout.status(coll.root, "ROOT")

        return coll

    def save_collection(self, name, coll):
        """ Save the collection. """
        writer = self.writer
        verbose = self.verbose

        if not util.valid_collection_name(name):
            writer.stderr.status(name, "INVALID")
            return False

        subdir = os.path.join(self.statedir, name)
        if not os.path.isdir(subdir):
            writer.stderr.status(name, "NOTFOUND")
            return False

        coll.save(
            os.path.join(subdir, consts.COLLECTION_FILE)
        )

        if verbose:
            writer.stdout.status(name, "SAVED")

        return True


def main():
    try:
        result = Program().main()
    except errors.Error as e:
        sys.stderr.write(str(e))
        sys.stderr.write("\n\n")
        sys.stderr.flush()
        result = -1

    return result
