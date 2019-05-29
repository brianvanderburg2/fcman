""" Find path action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import fnmatch
import re

from .. import collection
from .base import ActionBase


class FindPathAction(ActionBase):
    """ Find paths that match specific tags. """

    ACTION_NAME = "findpath"
    ACTION_DESC = "Find paths that match specific pattern."

    @classmethod
    def add_arguments(cls, parser):
        super(FindPathAction, cls).add_arguments(parser)

        parser.add_argument(
            "-c", "--no-case", dest="nocase", default=False, action="store_true",
            help="Perform case insensitive match for path names."
        )
        parser.add_argument("path", help="Path to search")
        parser.add_argument(
            "pattern",
            help="path pattern to find."
        )

    def run(self):
        node = self.find_node(
            self.program.collection.normalize(self.options.path)
        )

        if node is None:
            self.writer.stderr.status(self.program.cwd, "BADPATH")
            return False

        return self._handle_node(node)

    def _handle_node(self, node):
        status = False

        pattern = self.options.pattern
        path = node.prettypath

        matched = False
        if pattern[0:2] == "r:":
            matched = re.search(pattern[2:], path)
        else:
            if self.options.nocase:
                pattern = pattern.lower()
                path = path.lower()

            if fnmatch.fnmatch(path, pattern):
                matched = True

        if matched:
            status = True
            self.writer.stdout.status(node.prettypath, "FINDPATH")

        if isinstance(node, collection.Directory):
            for child in sorted(node.children):
                if self._handle_node(node.children[child]):
                    status = True

        return status


ACTIONS = [FindPathAction]
