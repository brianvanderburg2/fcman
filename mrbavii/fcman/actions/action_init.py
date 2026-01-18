""" Init action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-202026 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os

from .base import ActionBase
from .. import collection


class InitAction(ActionBase):
    """ Initialize a collection. """

    ACTION_NAME = "init"
    ACTION_DESC = "Initialize a collection."
    ACTION_LOAD_COLLECTION = False

    def run(self):
        # This is a special action, collection is not loaded at this point
        # can't use self.program.dir or self.program.collection
        coll = collection.Collection()
        coll.set_root(".")

        if os.path.exists(self.options.dir):
            self.writer.stderr.status(self.options.dir, "EXISTS")
            return False

        self.writer.stdout.status(self.options.dir, "INIT")

        # Store the collection and file in the program so it will save it
        os.makedirs(self.options.dir)

        self.program.dir = self.options.dir
        self.program.collection = coll
        coll.dirty = True

        return True

ACTIONS = [InitAction]
