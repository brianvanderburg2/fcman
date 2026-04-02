""" Backup action. """
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


class BackupAction(ActionBase):
    """ Backup a collection state. """
    ACTION_NAME = "backup"
    ACTION_DESC = "Backup a collection state"

    @classmethod
    def add_arguments(cls, parser):
        """ Add arguments """
        super(BackupAction, cls).add_arguments(parser)
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

        filename = os.path.join(subdir, consts.COLLECTION_FILE)
        if not os.path.exists(filename):
            self.writer.stderr.status(name, "NO COLLECTION FILE")
            return False

        backupdir = os.path.join(subdir, consts.BACKUP_DIR)
        backupbase = time.strftime("backup-%Y%m%d-%H%M%S.xml")        
        backupname = os.path.join(backupdir, backupbase)

        if os.path.exists(filename):
            if not os.path.isdir(backupdir):
                os.makedirs(backupdir)

            shutil.copyfile(filename, backupname)

        self.writer.stdout.status(self.options.name, "BACKUP")
        return True


ACTIONS = [BackupAction]
