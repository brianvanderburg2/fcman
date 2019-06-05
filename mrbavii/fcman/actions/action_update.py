""" Update action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["UpdateAction"]


import os

from .. import collection
from .. import util
from .base import ActionBase


class UpdateAction(ActionBase):
    """ Update the collection. """

    ACTION_NAME = "update"
    ACTION_DESC = "Update the collection"

    @classmethod
    def add_arguments(cls, parser):
        super(UpdateAction, cls).add_arguments(parser)
        parser.add_argument(
            "-f", "--force", dest="force", default=False,
            action="store_true", help="Always update the checksum."
        )
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
            self.handle_symlink(node)
        elif isinstance(node, collection.File):
            self.handle_file(node)
        elif isinstance(node, collection.Directory):
            self.handle_directory(node)
        else:
            return False

        self.program.collection.dirty = True
        return True

    def handle_symlink(self, node):
        target = os.readlink(node.path)
        if target != node.target:
            node.target = target
            self.writer.stdout.status(node.prettypath, "SYMLINK")

    def handle_file(self, node):
        stat = os.stat(node.path)

        if (self.options.force or
                abs(node.timestamp - stat.st_mtime) > util.TIMEDIFF or
                node.size != stat.st_size or node.checksum == ""):

            if self.verbose:
                self.writer.stdout.status(node.prettypath, 'PROCESSING')
            node.checksum = node.calc_checksum()
            node.timestamp = int(stat.st_mtime)
            node.size = stat.st_size
            self.writer.stdout.status(node.prettypath, 'CHECKSUM')

    def handle_directory(self, node):
        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')

        # Check for missing items
        for i in sorted(node.children):
            child = node.children[i]
            if node.ignore(i):
                del node.children[i]
                self.writer.stdout.status(child.prettypath, 'IGNORED')
            elif not child.exists():
                del node.children[i]
                self.writer.stdout.status(child.prettypath, 'DELETED')

        # Add new items
        for i in sorted(os.listdir(node.path)):
            if not node.ignore(i) and not i in node.children:
                path = node.path + os.sep + i

                if os.path.islink(path):
                    item = collection.Symlink(node, i, "")
                elif os.path.isfile(path):
                    item = collection.File(node, i, 0, 0, "") # pylint: disable=redefined-variable-type
                elif os.path.isdir(path):
                    item = collection.Directory(node, i)
                else:
                    continue # Unsupported item type, will be reported missing with check

                self.writer.stdout.status(item.prettypath, 'ADDED')

        # Update all item including newly added items
        for i in sorted(node.children):
            child = node.children[i]
            if isinstance(child, collection.Symlink):
                self.handle_symlink(child)
            elif isinstance(child, collection.File):
                self.handle_file(child)
            elif isinstance(child, collection.Directory) and self.options.recurse:
                self.handle_directory(child)
            else:
                pass


ACTIONS = [UpdateAction]
