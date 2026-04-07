""" List action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-202026 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os

from .  import base
from .. import consts


class ListAction(base.ActionBase):
    """ List collection. """

    ACTION_NAME = "list"
    ACTION_DESC = "List collections."
    ACTION_LOAD_STATE = True

    def run(self):
        writer = self.writer

        entries = sorted(os.listdir(self.program.statedir))
        for entry in entries:
            subdir = os.path.join(self.program.statedir, entry)
            if not os.path.isdir(subdir):
                continue

            writer.stdout.status(entry, "COLLECTION")
            
            config = os.path.join(subdir, consts.COLLECTION_CONFIG_FILE)
            if not os.path.isfile(config):
                writer.stdout.status(entry, "COLLECTION", "missing: " + consts.COLLECTION_CONFIG_FILE)

            collection = os.path.join(subdir, consts.COLLECTION_FILE)
            if not os.path.isfile(collection):
                writer.stdout.status(entry, "COLLECTION", "missing: " + consts.COLLECTION_FILE)


        return True

ACTIONS = [ListAction]
