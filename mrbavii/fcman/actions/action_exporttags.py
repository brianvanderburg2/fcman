""" Export action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os
import re
import shutil

from .. import collection
from .. import consts
from .. import util
from .base import ActionBase


class ExportTagsAction(ActionBase):
    """ Dump information about the collection. """
    ACTION_NAME = "exporttags"
    ACTION_DESC = "Export tags as symlinks/etc"

    @classmethod
    def add_arguments(cls, parser):
        super(ExportTagsAction, cls).add_arguments(parser)
        parser.add_argument(
            "-n", "--name", dest="name", default=consts.DEFAULT_COLLECTION,
            action="store", help="Collection name"
        )
        parser.add_argument(
            "-d", "--dir", dest="dir", default=None, action="store",
            help="Tags directory"
        )

    def run(self):
        coll = self.program.load_collection(self.options.name)
        if coll is None:
            return False

        # Make directory if needed
        if self.options.dir is not None:
            self._tagsdir = os.path.normpath(self.options.dir)
        else:
            self._tagsdir = os.path.join(
                self.program.statedir,
                self.options.name,
                consts.TAG_DIR
            )

            # Only remove if using default internal directory under collection
            # state. This allows tags from multiple collections to be exported
            # to the same directory if specified
            if not os.path.isdir(self._tagsdir):
                os.makedirs(self._tagsdir)

        if not os.path.isdir(self._tagsdir):
            os.makedirs(self._tagsdir)

        return self._handle_node(coll.rootnode)

    def _handle_node(self, node):
        result = True

        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')

        if node.meta:
            if not self._dumptags(node):
                result = False

        if isinstance(node, collection.Directory):
            for child in sorted(node.children):
                if not self._handle_node(node.children[child]):
                    result = False

        return result

    def _dumptags(self, node):
        """ Dump the tags to symlinks. """
        result =  True
        tags = set()

        for meta in node.meta.get():
            type = meta.get("type") # pylint: disable=redefined-builtin
            if type == "tag":
                tags.add(meta.get("tag", ""))

        for tag in tags:
            if self.verbose:
                self.writer.stdout.status(node.prettypath, 'EXPORTTAG', tag)
        
            parts = tag.split("/")
            for i in range(len(parts)):
                parts[i] = re.sub("[^a-zA-z0-9_-]+", "", parts[i])

            tagdir = os.path.join(self._tagsdir, *parts)
            if not os.path.isdir(tagdir):
                os.makedirs(tagdir)

            relpath = os.path.relpath(node.path, tagdir)
            basename = os.path.basename(node.path)
            link = os.path.join(tagdir, basename)

            if os.path.exists(link):
                self.writer.stdout.status(node.prettypath, 'DUPLICATE', tag)
                result = False
            else:
                os.symlink(
                    relpath,
                    link
                )

        return result


ACTIONS = [ExportTagsAction]
