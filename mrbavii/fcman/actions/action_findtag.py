""" Find tag action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


from .. import collection
from .base import ActionBase


class FindTagAction(ActionBase):
    """ Find paths that match specific tags. """

    ACTION_NAME = "findtag"
    ACTION_DESC = "Find paths that match specific tags."

    @classmethod
    def add_arguments(cls, parser):
        super(FindTagAction, cls).add_arguments(parser)

        parser.add_argument(
            "-a", "--all",
            dest="match_all",
            default=False,
            action="store_true",
            help="Report paths only if the path has all tags specified."
        )
        parser.add_argument("path", help="Path to search")
        parser.add_argument(
            "tags",
            nargs="+",
            help="List of tags to find."
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

        alltags = set(
            meta.get("tag", "").lower()
            for meta in node.getmeta("tag")
        )
        findtags = set(tag.lower() for tag in self.options.tags)

        found = findtags.intersection(alltags)

        if self.options.match_all:
            matched = (found == findtags)
        else:
            matched = len(found) > 0

        if matched:
            status = True
            self.writer.stdout.status(node.prettypath, "FINDTAG", ",".join(sorted(found)))

        if isinstance(node, collection.Directory):
            for child in sorted(node.children):
                if self._handle_node(node.children[child]):
                    status = True

        return status


ACTIONS = [FindTagAction]
