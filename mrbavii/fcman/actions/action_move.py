""" Move action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


from .base import ActionBase


class MoveAction(ActionBase):
    """ Move a node to a new parent. """

    ACTION_NAME = "move"
    ACTION_DESC = "Move node to a new parent."

    @classmethod
    def add_arguments(cls, parser):
        """ Add our arguments. """
        super(MoveAction, cls).add_arguments(parser)
        parser.add_argument("path", help="The path of the node to move.")
        parser.add_argument("parent", help="The path of the new parent.")

    def run(self):
        nodepath = self.normalize_path(self.options.path)
        parentpath = self.normalize_path(self.options.parent)

        if nodepath is None or parentpath is None:
            return False

        node = self.find_node(nodepath)
        parent = self.find_node(parentpath)

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

        self.program.collection.dirty = True
        return True


ACTIONS = [MoveAction]
