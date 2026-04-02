""" Verify a file and fix timestamps to match that of state. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import json
import os

from .. import collection
from .. import consts
from .. import util
from .base import ActionBase


class FixTimesAction(ActionBase):
    """ Check the collection. """

    ACTION_NAME = "fix-times"
    ACTION_DESC = "Fix file timestamps to match state if size and checksum match"

    def __init__(self, *args, **kwargs):
        ActionBase.__init__(self, *args, **kwargs)

    @classmethod
    def add_arguments(cls, parser):
        super(FixTimesAction, cls).add_arguments(parser)

        parser.add_argument(
            "-n", "--name", dest="name", default=consts.DEFAULT_COLLECTION,
            action="store", help="Collection name"
        )

        parser.add_argument(
            "-R", "--no-recurse", dest="recurse", default=True,
            action="store_false", help="Do not recurse"
        )

        parser.add_argument("path", nargs="?", default=".", help="Path to " + cls.ACTION_NAME)

    def run(self):
        coll = self.program.load_collection(self.options.name)
        if coll is None:
            return False

        path = self.normalize_path(coll, self.options.path)
        if path is None:
            return False
        elif self.verbose:
            self.writer.stdout.status(path, "WORKPATH")

        node = self.find_node(coll, path)
        if node is None:
            self.writer.stderr.status(path, "NONODE")
            return False

        if isinstance(node, collection.Symlink):
            pass
        elif isinstance(node, collection.File):
            result = self.handle_file(node)
        elif isinstance(node, collection.Directory):
            result = self.handle_directory(node)
        else:
            return False

        return result


    def handle_file(self, node):
        stat = os.stat(node.path)

        if abs(node.timestamp - stat.st_mtime) < util.TIMEDIFF:
            return True

        self.writer.stdout.status(node.prettypath, 'TIMEOFF')

        if node.size != stat.st_size:
            self.writer.stdout.status(node.prettypath, 'SIZE')
            return False # If size mismatch off we don't fix the timestamp

        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')

        if node.checksum == node.calc_checksum():
            os.utime(node.path, times=(stat.st_atime, node.timestamp))
            self.writer.stdout.status(node.prettypath, 'TIMEFIXED')
        else:
            self.writer.stdout.status(node.prettypath, 'CHECKSUM')
        
        return True

    def handle_directory(self, node):
        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')
        status = True

        # Check children
        for i in sorted(node.children):
            child = node.children[i]
            if child.exists():
                if isinstance(child, collection.File):
                    if not self.handle_file(child):
                        status = False
                elif isinstance(child, collection.Directory) and self.options.recurse:
                    if not self.handle_directory(child):
                        status = False
                else:
                    pass

        return status


ACTIONS = [FixTimesAction]
