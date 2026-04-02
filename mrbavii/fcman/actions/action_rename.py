""" Rename action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


from .. import consts
from .base import ActionBase


class RenameAction(ActionBase):
    """ Rename a node. """

    ACTION_NAME = "rename"
    ACTION_DESC = "Rename a node."

    @classmethod
    def add_arguments(cls, parser):
        """ Add our arguments. """
        super(RenameAction, cls).add_arguments(parser)
        parser.add_argument(
            "-n", "--name", dest="name", default=consts.DEFAULT_COLLECTION,
            action="store", help="Collection name"
        )
        
        parser.add_argument("path", help="The path of the node to rename.")
        parser.add_argument("newname", help="The name to rename to.")

    def run(self):
        coll = self.program.load_collection(self.options.name)
        if coll is None:
            return False

        nodepath = self.normalize_path(coll, self.options.path)
        if nodepath is None:
            return False

        node = self.find_node(coll, nodepath)
        if node is None:
            self.writer.stderr.status(nodepath, "NONODE")
            return False

        if not node.rename(self.options.newname):
            self.writer.stderr.status(nodepath, "NORENAME")
            return False
        else:
            self.writer.stdout.status(nodepath, "RENAME", node)

        return self.program.save_collection(self.options.name, coll)


ACTIONS = [RenameAction]
