""" Base action class. """
# pylint: disable=missing-docstring
__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"

__all__ = ["ActionBase", "MultiActionBase"]


import glob
import os

from .. import collection


class ActionBase(object):
    """ A base action. """

    ACTION_NAME = None
    ACTION_DESC = ""
    ACTION_LOAD_STATE = True

    def __init__(self, program):
        self.program = program
        self.options = program.options
        self.writer = program.writer
        self.verbose = program.verbose

    def run(self):
        raise NotImplementedError

    @classmethod
    def add_arguments(cls, parser):
        pass

    @classmethod
    def parse_arguments(cls, options):
        pass

    def normalize_path(self, coll, path):
        """ Normalize a path. """
        result = coll.normalize(path)
        if result is None:
            self.writer.stderr.status(path, "BADPATH")

        return result

    def find_nearest_node(self, coll, path):
        """ Find the node or the nearest parent node.
            Return is (node, remaining_path) """

        path = list(path)
        node = coll.rootnode

        while len(path):
            if not isinstance(node, collection.Directory):
                break

            for name in node.children:
                if name == path[0]:
                    node = node.children[name]
                    path.pop(0)
                    break # break for
            else:
                break # break while

        # len(path) == 0 means we found the node, else just the nearest parent
        return (node, path)

    def find_node(self, coll, path):
        """ Find the exact node or return None. """
        (node, remaining_path) = self.find_nearest_node(coll, path)
        return node if not remaining_path else None

    def handle_sigint(self):
        """ Handle CTRL-C """
        pass


class MultiActionBase(ActionBase):
    """ A base action for multi-collection actions. """

    def __init__(self, program):
        ActionBase.__init__(self, program)

        self._collections = {}

    @classmethod
    def add_arguments(cls, parser):
        ActionBase.add_arguments(parser)

        parser.add_argument(
            "-m", "--multi",
            dest="multi",
            action="extend",
            nargs="+",
            required=True,
            help="List of collection files to load.  May contain glob.glob characters."
        )

    @classmethod
    def parse_arguments(cls, options):
        ActionBase.parse_arguments(options)

    def load_collections(self):
        """ Load the list of collections. """

        all_collections = []
        for pattern in self.options.multi:
            all_collections.extend(glob.glob(pattern))

        for filename in all_collections:
            relpath = os.path.relpath(filename)

            if self.verbose:
                self.writer.stdout.status(filename, "LOADMULTI")
            self._collections[relpath] = collection.Collection.load(filename)

    def run(self):
        self.load_collections()
        self.run_multi()

    def run_multi(self):
        raise NotImplementedError
