""" Commit action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2026 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os
import shutil
import time

from .. import collection
from .. import util
from .base import ActionBase


class CommitAction(ActionBase):
    """ Dump information about the collection. """
    ACTION_NAME = "commit"
    ACTION_DESC = "Commit staging.xml to collection.xml"

    def run(self):
        # Backup current collection.xml file
        staging = os.path.join(
            self.program.dir,
            self.program.STAGED_FILE
        )

        collection = os.path.join(
            self.program.dir,
            self.program.COMMITTED_FILE)

        backups = os.path.join(
            self.program.dir,
            self.program.BACKUP_DIR
        )

        backupname = time.strftime("%Y%m%d-%H%M%S.xml")

        if os.path.exists(collection):
            if util.files_match(staging, collection):
                self.writer.stdout.status(self.program.dir, "NOCHG")
                return True

            if not os.path.isdir(backups):
                os.makedirs(backups)

            shutil.copyfile(collection, os.path.join(backups, backupname))

        shutil.copyfile(staging, collection)

        self.writer.stdout.status(self.program.dir, "COMMIT")
        return True


ACTIONS = [CommitAction]
