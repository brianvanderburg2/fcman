""" Export action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os

from .. import collection
from .. import util
from .base import ActionBase


class ExportAction(ActionBase):
    """ Dump information about the collection. """
    # TODO: need option to control where files are generated.

    ACTION_NAME = "export"
    ACTION_DESC = "Export information"

    def run(self):
        md5file = os.path.join(self.program.collection.root, "md5sums.txt")
        infofile = os.path.join(self.program.collection.root, "info.txt")

        md5stream = util.TextFile(md5file)
        infostream = util.TextFile(infofile)

        streams = (md5stream, infostream)

        with md5stream:
            with infostream:
                self._handle_directory(self.program.collection.rootnode, streams)

    def _handle_directory(self, node, streams):
        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')

        streams[1].writeln("Directory: {0}".format(node.prettypath))

        if node.meta:
            self._dumpmeta(node, streams)

        for child in sorted(node.children):
            streams[1].writeln("")
            childnode = node.children[child]
            if isinstance(childnode, collection.Symlink):
                self._handle_symlink(childnode, streams)
            elif isinstance(childnode, collection.File):
                self._handle_file(childnode, streams)
            elif isinstance(childnode, collection.Directory):
                self._handle_directory(childnode, streams)
            else:
                pass

    def _handle_symlink(self, node, streams):
        streams[1].writeln("Symlink: {0}".format(node.prettypath))
        streams[1].writeln("Target: {0}".format(node.target))

        if node.meta:
            self._dumpmeta(node, streams)

    def _handle_file(self, node, streams):
        streams[1].writeln("File: {0}".format(node.prettypath))
        streams[1].writeln("Size: {0}".format(node.size))
        streams[1].writeln("MD5: {0}".format(node.checksum))
        streams[1].writeln("Modified: {0}".format(node.timestamp))

        if node.checksum:
            # skip the "/" at the beginning
            streams[0].writeln(node.checksum + ' *' + node.prettypath[1:])
        else:
            self.writer.stdout.status(node.prettypath, "MISSING CHECKSUM")

        if node.meta:
            self._dumpmeta(node, streams)

    @staticmethod
    def _dumpmeta(node, streams):
        """ Dump the metadata that we know about to the information file. """
        provides = []
        depends = []
        tags = set()
        descriptions = []

        for meta in node.getmeta():
            type = meta.get("type") # pylint: disable=redefined-builtin
            if not type:
                continue

            if type == "provides":
                provides.append((
                    meta.get("name"),
                    meta.get("version")
                ))
            elif type == "depends":
                depends.append((
                    meta.get("name"),
                    meta.get("minversion"),
                    meta.get("maxversion")
                ))
            elif type == "tag":
                tags.add(meta.get("tag"))
            elif type == "description":
                descriptions.append(meta.get("description"))

        if provides:
            streams[1].writeln("Provides: {0}".format(
                ", ".join(
                    "{0}{1}".format(
                        name,
                        ":" + version if version else ""
                    )
                    for (name, version) in provides
                )
            ))

        if depends:
            streams[1].writeln("Depends: {0}".format(
                ", ".join(
                    "{0}{1}{2}".format(
                        name,
                        ":" + minver if minver is not None else ":" if maxver is not None else "",
                        ":" + maxver if maxver is not None else ""
                    )
                    for (name, minver, maxver) in depends
                )
            ))

        if tags:
            streams[1].writeln("Tags: {0}".format(
                ", ".join(sorted(tags))
            ))

        descriptions = "\n".join(descriptions) # pylint: disable=redefined-variable-type
        if descriptions:
            import textwrap
            lines = textwrap.wrap(descriptions, 75)
            streams[1].writeln("Description:\n  {0}".format(
                "\n  ".join(lines)
            ))


ACTIONS = [ExportAction]
