""" Check and verify actions. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os

from .. import collection
from .. import util
from .base import ActionBase


class CheckAction(ActionBase):
    """ Check the collection. """

    ACTION_NAME = "check"
    ACTION_DESC = "Perform quick collection check"

    def __init__(self, *args, **kwargs):
        ActionBase.__init__(self, *args, **kwargs)
        self._fullcheck = False

    @classmethod
    def add_arguments(cls, parser):
        super(CheckAction, cls).add_arguments(parser)
        parser.add_argument("path", nargs="?", default=".", help="Path to " + cls.ACTION_NAME)

    def run(self):
        path = self.normalize_path(self.options.path)
        if path is None:
            return False
        elif self.verbose:
            self.writer.stdout.status(path, "WORKPATH")

        node = self.find_node(path)
        if node is None:
            self.writer.stderr.status(path, "NONODE")
            return False


        if isinstance(node, collection.Symlink):
            return self.handle_symlink(node)
        elif isinstance(node, collection.File):
            return self.handle_file(node)
        elif isinstance(node, collection.Directory):
            return self.handle_directory(node)
        else:
            return False

    def _missing_dir(self, node):
        for i in sorted(node.children):
            newnode = node.children[i]

            self.writer.stdout.status(newnode.prettypath, 'MISSING')
            if isinstance(newnode, collection.Directory):
                self._missing_dir(newnode)

    def handle_symlink(self, node):
        target = os.readlink(node.path)
        if target != node.target:
            self.writer.stdout.status(node.prettypath, 'SYMLINK')
            return False

        return True

    def handle_file(self, node):
        status = True
        stat = os.stat(node.path)

        if abs(node.timestamp - stat.st_mtime) > util.TIMEDIFF:
            status = False
            self.writer.stdout.status(node.prettypath, 'TIMESTAMP')

        if node.size != stat.st_size:
            status = False
            self.writer.stdout.status(node.prettypath, 'SIZE')

        if self._fullcheck:
            if self.verbose:
                self.writer.stdout.status(node.prettypath, 'PROCESSING')
            if node.checksum != node.calc_checksum():
                status = False
                self.writer.stdout.status(node.prettypath, 'CHECKSUM')

        return status

    def handle_directory(self, node):
        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')
        status = True

        # Check for missing
        for i in sorted(node.children):
            newnode = node.children[i]

            if node.ignore(i):
                self.writer.stdout.status(newnode.prettypath, 'SHOULDIGNORE')
            if not newnode.exists():
                self.writer.stdout.status(newnode.prettypath, 'MISSING')
                status = False

                # Report all subitems
                if isinstance(newnode, collection.Directory) and self.options.recurse:
                    self._missing_dir(newnode)


        # Check for new items
        for i in sorted(os.listdir(node.path)):
            if not node.ignore(i) and not i in node.children:
                self.writer.stdout.status(node.prettypath.rstrip("/") + "/" + i, 'NEW')
                status = False

                # Show new child items
                path = node.path + os.sep + i
                if os.path.isdir(path) and not os.path.islink(path) and self.options.recurse:
                    newnode = collection.Directory(node, i)

                    orig = self._fullcheck
                    self._fullcheck = False
                    self.handle_directory(newnode)
                    self._fullcheck = orig

                    del node.children[i]

        # Check children
        for i in sorted(node.children):
            child = node.children[i]
            if child.exists():
                if isinstance(child, collection.Symlink):
                    if not self.handle_symlink(child):
                        status = False
                elif isinstance(child, collection.File):
                    if not self.handle_file(child):
                        status = False
                elif isinstance(child, collection.Directory) and self.options.recurse:
                    if not self.handle_directory(child):
                        status = False
                else:
                    pass

        return status


class VerifyAction(CheckAction):
    """ Verify the collection. """

    ACTION_NAME = "verify"
    ACTION_DESC = "Perform full checksum verification"

    def __init__(self, *args, **kwargs):
        CheckAction.__init__(self, *args, **kwargs)
        self._fullcheck = True


ACTIONS = [CheckAction, VerifyAction]
