#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-docstring,too-few-public-methods
""" File collection management utility. """

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright 2000-2019"
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
import signal
import sys

from . import util
from . import actions
from . import collection


# Only run on Python 3
if sys.version_info[0:2] < (3, 2):
    sys.exit("This program requires Python 3.2 or greater")


# modify the default keyboard interrup exception
def sigint_print_and_exit(*args):
    sys.stderr.write("Aborted by Interrupt\n")
    sys.exit(-1)
signal.signal(signal.SIGINT, sigint_print_and_exit)


class VerboseChecker(object):
    """ A small class whose boolean value depends on verbose or a signal. """

    def __init__(self, verbose):
        self._verbose = verbose
        self._signalled = False

        try:
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
        self.iwd = None # The initial working directory before any chdir
        self.cwd = None
        self.file = None # The actual file loaded (options.file is the file to search for)
        self.options = None
        self.verbose = None
        self.writer = None

    @staticmethod
    def create_arg_parser():
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
        parser.add_argument("-e", "--exportdir", dest="exportdir", default=None)
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
        self.verbose = verbose = VerboseChecker(options.verbose)
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
        if action.ACTION_NAME != "init":
            # Load the collection if needed
            if not self.load_file():
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

        if self.collection and self.collection.dirty:
            self.save_backup()
            self.collection.save(self.file)

        return 0

    def load_file(self):
        """ Load the file. """
        writer = self.writer
        verbose = self.verbose

        self.file = self.find_file()

        if not self.file:
            writer.stderr.status("Collection not found", "NOFILE")
            return False
        elif verbose:
            writer.stdout.status(self.file, "COLLECTION")

        self.collection = collection.Collection.load(self.file)

        # Set root
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

        # Set exportdir
        if self.options.exportdir:
            self.collection.set_exportdir(self.options.exportdir)
        elif self.collection.autoexportdir:
            self.collection.set_exportdir(os.path.join(
                os.path.dirname(self.file),
                self.collection.autoexportdir
            ))
        else:
            self.collection.set_exportdir(os.path.dirname(self.file))

        if verbose:
            writer.stdout.status(self.collection.exportdir, "EXPORT")

        return True

    def save_backup(self):
        """ Save a backup based on the filename if requested. """
        filename = self.file
        backupname = os.path.join(
            self.collection.exportdir,
            os.path.basename(filename)
        )
        backup = self.options.backup
        if backup == 0:
            return

        backup_concat = tuple(".{0}bak".format(i) for i in range(1, backup + 1))

        if os.path.exists(filename):
            # Make directory if it doesn't exist
            if not os.path.isdir(self.collection.exportdir):
                os.makedirs(self.collection.exportdir)

            # Remove last backup if it exists
            if os.path.exists(backupname + backup_concat[-1]):
                os.remove(backupname + backup_concat[-1])

            for i in range(len(backup_concat) - 2, -1, -1):
                if os.path.exists(backupname + backup_concat[i]):
                    os.rename(
                        backupname + backup_concat[i],
                        backupname + backup_concat[i + 1]
                    )

            os.rename(filename, backupname + backup_concat[0])


    def find_file(self):
        """ Use our options to find file. """

        # Don't use os.path.isfile, it fails on device files from command
        # substitution such as:
        # mrbavii-fcman -f <(unxz history.xml.xz> findpath / "..."

        if not self.options.walk:
            # In this mode, file directly specified
            filename = os.path.normpath(self.options.file)
            if os.path.exists(filename):
                return filename
            return None

        # In walk mode, walk up the directory to find the file
        head = self.cwd
        while head:
            filename = os.path.join(head, self.options.file)
            if os.path.exists(filename):
                return os.path.relpath(filename) # relpath to keep it pretty

            (head, tail) = os.path.split(head)
            if not tail:
                break

        return None


def main():
    sys.exit(Program().main())
