""" Init action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os

from .base import ActionBase
from .. import collection


class InitAction(ActionBase):
    """ Initialize a collection. """

    ACTION_NAME = "init"
    ACTION_DESC = "Initialize a collection."

    def run(self):
        # This is a special action, collection is not loaded at this point
        # can't use self.program.file or self.program.collection
        coll = collection.Collection()
        coll.set_root(".")
        coll.set_exportdir(".")
        if self.options.root is not None:
            coll.autoroot = self.options.root

        if os.path.exists(self.options.file):
            self.writer.stderr.status(self.options.file, "EXISTS")
            return False

        self.writer.stdout.status(self.options.file, "INIT")

        # Store the collection and file in the program so it will save it
        self.program.file = self.options.file
        self.program.collection = coll
        coll.dirty = True

        return True

ACTIONS = [InitAction]
