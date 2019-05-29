""" Rename action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


from .base import ActionBase


class RenameAction(ActionBase):
    """ Rename a node. """

    ACTION_NAME = "rename"
    ACTION_DESC = "Rename a node."

    @classmethod
    def add_arguments(cls, parser):
        """ Add our arguments. """
        super(RenameAction, cls).add_arguments(parser)
        parser.add_argument("path", help="The path of the node to rename.")
        parser.add_argument("name", help="The name to rename to.")

    def run(self):
        nodepath = self.normalize_path(self.options.path)
        if nodepath is None:
            return False

        node = self.find_node(nodepath)
        if node is None:
            self.writer.stderr.status(nodepath, "NONODE")
            return False

        if not node.rename(self.options.name):
            self.writer.stderr.status(nodepath, "NORENAME")
            return False
        else:
            self.writer.stdout.status(nodepath, "RENAME", node)

        self.program.collection.dirty = True
        return True


ACTIONS = [RenameAction]
