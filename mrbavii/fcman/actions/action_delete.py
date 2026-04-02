""" Delete action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


from .. import consts

from .base import ActionBase


class DeleteAction(ActionBase):
    """ Delete a node. """

    ACTION_NAME = "delete"
    ACTION_DESC = "Delete a node."

    @classmethod
    def add_arguments(cls, parser):
        """ Add our arguments. """
        super(DeleteAction, cls).add_arguments(parser)

        parser.add_argument(
            "-n", "--name", dest="name", default=consts.DEFAULT_COLLECTION,
            action="store", help="Collection name"
        )
               
        parser.add_argument("path", help="The path of the node to delete.")

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

        if not node.delete():
            self.writer.stderr.status(nodepath, "NODELETE")
            return False
        else:
            self.writer.stdout.status(nodepath, "DELETE")

        return self.program.save_collection(self.options.name, coll)


ACTIONS = [DeleteAction]
