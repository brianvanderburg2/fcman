""" Check meta action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


from .. import collection
from .base import ActionBase


class CheckMetaAction(ActionBase):
    """ Check the metadata (dependencies/etc). """

    ACTION_NAME = "checkmeta"
    ACTION_DESC = "Check metadata, dependencies, etc"

    def run(self):
        status = True
        if not self._checkdeps():
            status = False

        return status

    def _checkdeps(self):
        """ Check the dependencies. """

        # First gather all known packages that are actaully attached to a node
        packages = {}
        self._checkdeps_walk_collect(self.program.collection.rootnode, packages)

        # Next check all dependencies from the nodes have a package to satisfy
        return self._checkdeps_walk(self.program.collection.rootnode, packages)

    def _checkdeps_walk_collect(self, node, packages):
        for meta in node.getmeta("provides"):
            name = meta.get("name")
            if not name:
                continue

            version = meta.get("version")
            if not version:
                version = None

            if not name in packages:
                packages[name] = set()
            packages[name].add(version)


        if isinstance(node, collection.Directory):
            for child in sorted(node.children):
                self._checkdeps_walk_collect(node.children[child], packages)

    def _checkdeps_walk(self, node, packages):
        status = True

        for meta in node.getmeta("depends"):

            name = meta.get("name")
            if not name:
                continue

            minver = meta.get("minversion")
            maxver = meta.get("maxversion")
            if not minver:
                minver = None
            if not maxver:
                maxver = None

            depends = (name, minver, maxver)

            if not self._checkdeps_find(depends, packages):
                status = False
                self.writer.stdout.status(node.prettypath, "DEPENDS", str(depends))

        if isinstance(node, collection.Directory):
            for child in sorted(node.children):
                if not self._checkdeps_walk(node.children[child], packages):
                    status = False

        return status

    def _checkdeps_find(self, depends, packages):
        (name, minver, maxver) = depends

        # Check package exists
        if not name in packages:
            return False

        # If no version in dependency, package exists so it is satisfied
        if minver is None and maxver is None:
            return True

        for version in packages[name]:
            if version is None:
                continue # Can't compare to a package without a version

            if minver is not None and self._checkdeps_compare(version, minver) < 0:
                continue

            if maxver is not None and self._checkdeps_compare(version, maxver) > 0:
                continue

            # Found a version that is within the range
            return True

    @staticmethod
    def _checkdeps_compare(ver1, ver2):
        """ A simple version compare based only on numbers and periods. """

        try:
            ver1 = list(map(lambda ver: int(ver), ver1.split(".")))
            ver2 = list(map(lambda ver: int(ver), ver2.split(".")))
        except ValueError:
            return False

        # pad to the same length
        if len(ver1) < len(ver2):
            ver1.extend([0] * (len(ver2) - len(ver1)))
        elif len(ver2) < len(ver1):
            ver2.extend([0] * (len(ver1) - len(ver2)))

        # per element compare
        if ver1 < ver2:
            return -1
        elif ver1 > ver2:
            return 1
        else:
            return 0


ACTIONS = [CheckMetaAction]
