""" Find desc action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


from .. import collection
from .. import consts
from .base import ActionBase, MultiActionBase


class FindDescMixin:
    """ Mixin for FindDesc/MultiFindDesc """

    def _handle_node(self, node):
        status = False

        alldescs = " ".join(
            meta.get("description", "").lower()
            for meta in node.meta.get("description")
        )
        finddescs = set(i.lower() for i in self.options.pattern)
        found = set()

        for desc in finddescs:
            if desc in alldescs:
                found.add(desc)

        if self.options.match_all:
            matched = (found == finddescs)
        else:
            matched = len(found) > 0

        if matched:
            status = True
            self.writer.stdout.status(node.prettypath, "FINDDESC", ",".join(sorted(found)))

        if isinstance(node, collection.Directory):
            for child in sorted(node.children):
                if self._handle_node(node.children[child]):
                    status = True

        return status


class FindDescAction(ActionBase, FindDescMixin):
    """ Find paths that match specific descriptions. """

    ACTION_NAME = "finddesc"
    ACTION_DESC = "Find paths that match specific descriptions."

    @classmethod
    def add_arguments(cls, parser):
        super(FindDescAction, cls).add_arguments(parser)

        parser.add_argument(
            "-n", "--name", dest="name", default=consts.DEFAULT_COLLECTION,
            action="store", help="Collection name"
        )
        parser.add_argument(
            "-a", "--all",
            dest="match_all",
            default=False,
            action="store_true",
            help="Report paths only if the path has all descriptions specified."
        )
        parser.add_argument(
            "-p", "--pattern", action="extend", nargs="+", required=True,
            help="Pattern of descriptions to find."
        )
        parser.add_argument("path", nargs="?", default=".", help="Path to search")


    def run(self):
        coll = self.program.load_collection(self.options.name)
        if coll is None:
            return False

        node = self.find_node(coll, coll.normalize(self.options.path))

        if node is None:
            self.writer.stderr.status(self.program.cwd, "BADPATH")
            return False

        return self._handle_node(node)


class MultiFindDescAction(MultiActionBase, FindDescMixin):
    """ Find paths that match specific descriptions. """

    ACTION_NAME = "multifinddesc"
    ACTION_DESC = "Find paths that match specific descriptions."

    @classmethod
    def add_arguments(cls, parser):
        super(MultiFindDescAction, cls).add_arguments(parser)

        parser.add_argument(
            "-a", "--all",
            dest="match_all",
            default=False,
            action="store_true",
            help="Report paths only if the path has all descriptions specified."
        )
        parser.add_argument(
            "-p", "--pattern", action="extend", nargs="+", required=True,
            help="Pattern of descriptions to find."
        )

    def run_multi(self):
        status = False

        for relpath in sorted(self._collections):
            self.writer.stdout.status(relpath, "COLLECTION")
            coll = self._collections[relpath]
            node = coll.rootnode
            if self._handle_node(node):
                status = True

        return status


ACTIONS = [FindDescAction] #, MultiFindDescAction]
