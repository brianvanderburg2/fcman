""" Move action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


from .. import consts
from .base import ActionBase


class MoveAction(ActionBase):
    """ Move a node to a new parent. """

    ACTION_NAME = "move"
    ACTION_DESC = "Move node to a new parent."

    @classmethod
    def add_arguments(cls, parser):
        """ Add our arguments. """
        super(MoveAction, cls).add_arguments(parser)
        parser.add_argument(
            "-n", "--name", dest="name", default=consts.DEFAULT_COLLECTION,
            action="store", help="Collection name"
        )
        parser.add_argument("path", help="The path of the node to move.")
        parser.add_argument("parent", help="The path of the new parent.")

    def run(self):
        coll = self.program.load_collection(self.options.name)
        if coll is None:
            return False

        nodepath = self.normalize_path(coll, self.options.path)
        parentpath = self.normalize_path(coll, self.options.parent)

        if nodepath is None or parentpath is None:
            return False

        node = self.find_node(coll, nodepath)
        parent = self.find_node(coll, parentpath)

        if node is None:
            self.writer.stderr.status(nodepath, "NONODE")

        if parent is None:
            self.writer.stderr.status(parentpath, "NONODE")

        if node is None or parent is None:
            return False

        if not node.reparent(parent):
            self.writer.stderr.status(nodepath, "NOMOVE")
            return False
        else:
            self.writer.stdout.status(nodepath, "MOVE", node)

        return self.program.save_collection(self.options.name, coll)


ACTIONS = [MoveAction]
