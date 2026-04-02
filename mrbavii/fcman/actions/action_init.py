""" Init action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-202026 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os

from .  import base
from .. import collection
from .. import config
from .. import consts
from .. import util


class InitAction(base.ActionBase):
    """ Initialize a collection. """

    ACTION_NAME = "init"
    ACTION_DESC = "Initialize a collection."
    ACTION_LOAD_STATE = False

    @classmethod
    def add_arguments(cls, parser):
        """ Add arguments """
        super(InitAction, cls).add_arguments(parser)
        parser.add_argument("-n", "--name", dest="name", required=True, help="The name of the collection")
        parser.add_argument("-r", "--root", dest="root", required=True, help="The root of the action relative to the top directory")

    def run(self):
        # The current directory is being used as the top directory since we don't
        # have the state directory loaded yet

        if not util.valid_collection_name(self.options.name):
            self.writer.stderr.status(name, "BAD NAME")
            return False

        if self.options.raw:
            statedir = os.path.join(self.program.cwd)
        else:
            statedir = os.path.join(self.program.cwd, consts.STATEDIR_NORMAL)

        # main 'program' config file
        config_file = os.path.join(statedir, consts.MAIN_CONFIG_FILE)
        if not os.path.exists(config_file):
            if not os.path.isdir(statedir):
                os.makedirs(statedir)

            if self.verbose:
                self.writer.stdout.status(config_file, "CONFIG")

            cfg = config.Config()
            cfg.get_table("fcman", create=True)
            cfg.save(config_file)

        # new collection
        subdir = os.path.join(
            statedir,
            self.options.name
        )

        if os.path.exists(subdir):
            self.writer.stderr.status(self.options.name, "EXISTS")
            return False

        os.makedirs(subdir)
        self.writer.stdout.status(self.options.name, "INIT")

        filename = os.path.join(subdir, consts.COLLECTION_FILE)
        coll = collection.Collection()
        coll.save(filename)

        filename = os.path.join(subdir, consts.COLLECTION_CONFIG_FILE)
        cfg = config.Config()
        table = cfg.get_table("config", create=True)
        table["root"] = self.options.root
        cfg.save(filename)

        return True

ACTIONS = [InitAction]
