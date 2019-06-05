""" Add action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os

from .. import collection
from .action_update import UpdateAction


class AddAction(UpdateAction):
    """ Action to add a filesystem item to the collection. """
    ACTION_NAME = "add"
    ACTION_DESC = "Add a filesystem item to the collection"

    @classmethod
    def add_arguments(cls, parser):
        super(AddAction, cls).add_arguments(parser)

        parser.add_argument(
            "-p", "--parents", dest="parents", default=False,
            action="store_true", help="Create parent directory nodes if possible and needed"
        )

    def run(self):
        path = self.normalize_path(self.options.path)
        if path is None:
            return False

        (node, remaining) = self.find_nearest_node(path)
        if len(remaining) == 0:
            self.writer.stderr.status(path, "EXISTS")
            return False

        node = self._handle_parents(node, remaining[0:-1])
        if node is None:
            return False

        # Now we want to add the item to the node
        name = remaining[-1]
        path = os.path.join(node.path, name)

        if os.path.islink(path):
            item = collection.Symlink(node, name, "")
            self.writer.stdout.status(item.prettypath, "ADDED")
            self.handle_symlink(item)
        elif os.path.isfile(path):
            item = collection.File(node, name, 0, 0, "") # pylint: disable=redefined-variable-type
            self.writer.stdout.status(item.prettypath, "ADDED")
            self.handle_file(item)
        elif os.path.isdir(path):
            item = collection.Directory(node, name)
            self.writer.stdout.status(item.prettypath, "ADDED")
            if self.options.recurse:
                self.handle_directory(item)
        else:
            return False

        self.program.collection.dirty = True
        return True

    def _handle_parents(self, node, parts):
        """ Create each directory part (only if the given directory actually exists). """

        path = list(node.pathlist)
        while True:
            # All nodes should be directories
            if not isinstance(node, collection.Directory):
                self.writer.stderr.status(path, "NOTDIRECTORY")
                return None

            # We can't add if the node's fs component does not exist
            if not node.exists():
                self.writer.stderr.status(path, "NOTEXIST")
                return None

            # If no more parts, return the directory node
            if len(parts) == 0:
                return node

            if not self.options.parents:
                self.writer.stderr.status(path, "NOPARENTS")
                return None

            # Check if the part is in the directory
            name = parts.pop(0)
            path.append(name)

            if name in node.children:
                # Should never happen since if it did exist, find_nearest_node would have it
                node = node.children[name]
            else:
                node = collection.Directory(node, name)
                self.writer.stdout.status(node.prettypath, "ADDED")


ACTIONS = [AddAction]
