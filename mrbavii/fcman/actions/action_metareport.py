""" Report information about metadta. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2019 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os

from .. import collection
from .base import ActionBase
from .action_checkmeta import CheckMetaAction as CMA

class _DiagNode:
    """ Helper node to keep track of ID value """
    _counter = 0

    @classmethod
    def next_id(cls):
        _DiagNode._counter += 1
        return "N{0}".format(cls._counter)

class _NodeDiagNode(_DiagNode):
    def __init__(self, node, deps):
        self.id = self.next_id()
        self.node = node
        self.deps_ids = list(deps)

class _DepDiagNode(_DiagNode):
    def __init__(self, name, minver, maxver):
        self.name = name
        self.minver = minver
        self.maxver = maxver
        self.id = self.next_id()
        self.satisfy_ids = [] # ID of file diag nodes that satisfy this

class _Info:
    def __init__(self):
        self.dep_diag_nodes = {} # (name, minver, maxver): node
        self.node_diag_nodes = {} # collection node: node
        self.provided_packages = {} # package name: [(collection node, version)]


class MetaReportAction(ActionBase):
    """ Create a map of the dependencies. """

    ACTION_NAME = "metareport"
    ACTION_DESC = "Report information about metadata"""

    @classmethod
    def add_arguments(cls, parser):
        """ Add the arguments. """
        super(MetaReportAction, cls).add_arguments(parser)

        parser.add_argument(
            "-a", "--all",
            dest="report_all",
            action="store_true",
            default=False,
            help="Report all instead of brief information about metadata."
        )
        parser.add_argument(
            "-t", "--type",
            dest="report_type",
            action="store",
            default="a",
            help="Report (a)ll, (d)escription, (t)ags, (p)rovides, d(e)pends, (o)ther"
        )

    def run(self):
        """ Run the action """

        self._packages = {}
        self._report_all = self.program.options.report_all
        self._report_type = self.program.options.report_type.upper()
        # format: {package: [(node, version),...]}

        # First scan the nodes for useful information
        self._collect_meta(self.program.collection.rootnode)

        # Now report the meta information
        self._report_meta(self.program.collection.rootnode)
        
        # reportmeta simply reports the information, so missing dependencies
        # don't result in an error code like checkmeta does
        return True


    def _collect_meta(self, node):
        """ Scan nodes to collect information (first pass) """

        # Just determine the package of the node.
        for meta in node.getmeta("provides"):
            name = meta.get("name")
            version = meta.get("version")

            if name in ("", None):
                continue
            if version == "":
                version = None

            packages_list = self._packages.setdefault(name, [])
            packages_list.append((node, version))

        # Handle children
        if isinstance(node, collection.Directory):
            for child in sorted(node.children):
                self._collect_meta(node.children[child])

    def _report_meta(self, node):
        """ Report the meta. """
        import textwrap

        # Description
        if "A" in self._report_type or "D" in self._report_type:
            desc = []
            for meta in node.getmeta("description"):
                value = meta.get("description")
                if value is None:
                    continue

                value = value.strip().replace("\n", " ")
                if not value:
                    continue

                lines = textwrap.wrap(value, 70)
                self.writer.stdout.statusline(node, "META", "DESCRIPTION")
                for line in lines:
                    self.writer.stdout.statusline(node, "META", "    " + line)

        # Tags:
        if "A" in self._report_type or "T" in self._report_type:
            first = True
            for meta in node.getmeta("tag"):
                tag = meta.get("tag")
                if tag in ("", None):
                    continue

                if first:
                    first = False
                    self.writer.stdout.statusline(node, "META", "TAGS")

                self.writer.stdout.statusline(node, "META", "    " + tag)

        # Packages:
        if "A" in self._report_type or "P" in self._report_type:
            first = True
            for meta in node.getmeta("provides"):
                name = meta.get("name")
                version = meta.get("version")
                if name in ("", None):
                    continue
                if version in ("", None):
                    version = ""
                else:
                    version = ":" + version

                if first:
                    first = False
                    self.writer.stdout.statusline(node, "META", "PROVIDES")

                self.writer.stdout.statusline(node, "META", "    {0}{1}".format(
                    name, version
                ))

        # Dependencies
        if "A" in self._report_type or "E" in self._report_type:
            first = True
            for meta in node.getmeta("depends"):
                name = meta.get("name")
                minver = meta.get("minversion")
                maxver = meta.get("maxversion")

                if name in ("", None):
                    continue
                if minver == "":
                    minver = None
                if maxver == "":
                    maxver = None

                # Accumulate satisfying packages
                satisfiers = []
                for (packagenode, version) in self._packages.get(name, []):

                    if minver is None and maxver is None:
                        # Package always provides if no version check
                        satisfiers.append(packagenode)
                    elif version is None:
                        # need version if checking minver or maxver
                        continue
                    elif minver is not None and CMA._checkdeps_compare(version, minver) < 0:
                        continue
                    elif maxver is not None and CMA._checkdeps_compare(version, maxver) > 0:
                        continue
                    else:
                        satisfiers.append(packagenode)

                # Report dependency info
                line = name
                if minver is not None:
                    line = "{0} >= {1}".format(line, minver)
                if maxver is not None:
                    line = "{0} <= {1}".format(line, maxver)

                if not satisfiers:
                    line = "{0} (NO MATCHING PACKAGES)".format(line)

                if first:
                    first = False
                    self.writer.stdout.statusline(node, "META", "DEPENDS")

                self.writer.stdout.statusline(node, "META", "    " + line)
                if self._report_all:
                    for satisfier in satisfiers:
                        self.writer.stdout.statusline(node, "META", "        " + satisfier.prettypath)

        # Other unknown tags
        if "A" in self._report_type or "O" in self._report_type:
            first = True
            for meta in node.getmeta():
                type = meta.get("type")
                if type in ("description", "tag", "provides", "depends"):
                    continue

                if first:
                    first = False
                    self.writer.stdout.statusline(node, "META", "OTHER")
                self.writer.stdout.statusline(node, "META", "    " + repr(meta))

        # Handle children
        if isinstance(node, collection.Directory):
            for child in sorted(node.children):
                self._report_meta(node.children[child])
        


ACTIONS = [MetaReportAction]
