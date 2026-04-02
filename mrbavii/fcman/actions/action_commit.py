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
from .. import consts
from .. import util
from .base import ActionBase


class CommitAction(ActionBase):
    """ Dump information about the collection. """
    ACTION_NAME = "commit"
    ACTION_DESC = "Commit collection"

    @classmethod
    def add_arguments(cls, parser):
        """ Add arguments """
        super(CommitAction, cls).add_arguments(parser)
        parser.add_argument(
            "-n", "--name", dest="name", default=consts.DEFAULT_COLLECTION,
            action="store", help="Collection name"
        )

    def run(self):
        # Backup current collection.xml file
        if not util.valid_collection_name(self.options.name):
            self.writer.stderr.status(name, "BAD NAME")
            return False

        subdir = os.path.join(self.program.statedir, self.options.name)
        if not os.path.isdir(subdir):
            self.writer.stderr.status(name, "NO COLLECTION")
            return False

        staging = os.path.join(subdir, consts.STAGED_FILE)
        committed = os.path.join(subdir, consts.COMMITTED_FILE)

        backupdir = os.path.join(subdir, consts.BACKUP_DIR)
        backupname = time.strftime("committed-%Y%m%d-%H%M%S.xml")
        backup = os.path.join(backupdir, backupname)

        if os.path.exists(committed):
            if util.files_match(staging, committed):
                self.writer.stdout.status(self.options.name, "NOCHG")
                return True

            if not os.path.isdir(backupdir):
                os.makedirs(backupdir)

            shutil.copyfile(committed, backup)

        shutil.copyfile(staging, committed)

        self.writer.stdout.status(self.options.name, "COMMIT")
        return True


ACTIONS = [CommitAction]
