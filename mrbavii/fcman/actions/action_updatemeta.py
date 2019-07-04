""" Update meta action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


from configparser import SafeConfigParser
import fnmatch
import re

from .. import collection
from .. import util
from .base import ActionBase


class _MetaInfo(object):
    """ Represent metadata. """

    def __init__(self, node, options):
        """ Initial state of metadata. """
        self.node = node
        self.users = []
        self.name = None
        self.pattern = None
        self.autoname = []
        self.meta = set()

        self.target = options.get("target", ".")


    @classmethod
    def load(cls, node, name, config, options):
        """ Load metadata from an INI config section. """
        # pylint: disable=too-many-locals
        meta = _MetaInfo(node, options)
        meta.name = name

        # pattern
        if "pattern" in config:
            meta.pattern = config.get("pattern")
        else:
            # Allow using the config section name as the pattern when possible
            # so the user can just do [*.txt] instead of [textfiles]\npattern=*.txt
            meta.pattern = name

        if "autoname" in config:
            meta.autoname = set(util.splitval(config["autoname"]))

        # provides
        if "provides" in config:
            provides = util.splitval(config["provides"])
            for i in provides:
                parts = i.split(":")
                name = parts[0]
                version = parts[1] if len(parts) > 1 and parts[1] else ""
                meta.meta.add(frozenset((
                    ("type", "provides"),
                    ("name", name),
                    ("version", version)
                )))

        # depends
        if "depends" in config:
            depends = util.splitval(config["depends"])
            for i in depends:
                parts = i.split(":")
                name = parts[0]
                minversion = parts[1] if len(parts) > 1 and parts[1] else ""
                maxversion = parts[2] if len(parts) > 2 and parts[2] else ""
                meta.meta.add(frozenset((
                    ("type", "depends"),
                    ("name", name),
                    ("minversion", minversion),
                    ("maxversion", maxversion)
                )))


        # tags
        if "tags" in config:
            tags = util.splitval(config["tags"])
            for tag in tags:
                meta.meta.add(frozenset((
                    ("type", "tag"),
                    ("tag", tag)
                )))

        # description
        if "description" in config:
            desc = config["description"].strip()
            desc = " ".join([line.strip() for line in desc.splitlines() if len(line)])
            meta.meta.add(frozenset((
                ("type", "description"),
                ("description", desc)
            )))

        # ignore
        if "ignore" in config:
            ignores = util.splitval(config["ignore"])
            for ignore in ignores:
                meta.meta.add(frozenset((
                    ("type", "ignore"),
                    ("pattern", ignore)
                )))

        return meta

    def apply_version(self, version):
        """ Apply a version to the autonames if specified. """
        if not self.autoname:
            return None

        result = set()
        for name in self.autoname:
            result.add(frozenset((
                ("type", "provides"),
                ("name", name),
                ("version", version)
            )))

        return result


class UpdateMetaAction(ActionBase):
    """ Update the metadata information into the XML. """

    ACTION_NAME = "updatemeta"
    ACTION_DESC = "Update metadata from fcmeta.ini files into the XML."

    def __init__(self, *args, **kwargs):
        ActionBase.__init__(self, *args, **kwargs)
        self._allmeta = []

    def run(self):
        if not self.loadmeta(self.program.collection.rootnode):
            return False

        self.resetmeta(self.program.collection.rootnode)
        if not self.applymeta():
            return False

        self.program.collection.dirty = True

        for meta in self._allmeta:
            if not meta.users:
                self.writer.stdout.status(meta.node.prettypath, "UNUSEDMETA", meta.name)

        return True

    def loadmeta(self, node, force=False):
        status = True
        for i in sorted(node.children):
            child = node.children[i]

            if i == "fcmeta.ini":
                # Handle the special name "fcmeta.ini"
                if isinstance(child, collection.Directory):
                    # if directory is named fcmeta.ini, all INI files under
                    # are loaded recursively
                    if not self.loadmeta(child, True):
                        status = False
                else:
                    # Just load the INI file
                    if not self._loadmeta(child):
                        status = False

            elif isinstance(child, collection.Directory):
                # Not fcmeta.ini, process subdirs with same force setting
                if not self.loadmeta(child, force):
                    status = False

            elif force and i.lower().endswith(".ini") and not i[0:1] in (".", "~"):
                # If force is enabled the load all other INI files as well
                if not self._loadmeta(child):
                    status = False

        return status

    def _loadmeta(self, node):
        if self.verbose:
            self.writer.stdout.status(node, 'LOADING')

        config = SafeConfigParser()
        read = config.read(node.path)
        if not read:
            self.writer.stderr.status(node, 'LOAD ERROR')
            return False

        # Should at least have fcmeta options section
        if not config.has_section("fcman:fcmeta"):
            self.writer.stderr.status(node, 'NOTMETAINFO')
            return False

        options = dict(config.items("fcman:fcmeta"))

        # Handle the sections
        sections = config.sections()
        for name in sections:
            if name == "fcman:fcmeta": # Skip options section
                continue

            meta = _MetaInfo.load(node, name, dict(config.items(name)), options)
            self._allmeta.append(meta)

        return True

    def resetmeta(self, node):
        """ Clear the meta of a node and all child nodes. """
        node.clearmeta()
        if isinstance(node, collection.Directory):
            for child in node.children:
                self.resetmeta(node.children[child])

    def find_target(self, meta):
        """ Find the target the meta shold apply to. """

        parts = meta.target.strip().split("/")

        # First find the starting node
        if not parts[0]:
            # First part empty, means started with "/"
            node = self.program.collection.rootnode
            parts = parts[1:]
        else:
            node = meta.node.parent

        # Process remaining parts
        for part in parts:
            if not part:
                continue

            if part == ".":
                continue

            elif part == "..":
                if node.parent:
                    node = node.parent
                    continue

            elif part in node.children:
                child = node.children[part]
                if isinstance(child, collection.Directory):
                    node = child
                    continue

            # if we got here, we didn't handle the part
            return None

        # hanlded all parts so must have found the target
        return node

    def applymeta(self):
        """ Apply meta information to matching nodes. """
        status = True
        for meta in self._allmeta:
            parent = self.find_target(meta)
            if parent is None:
                self.writer.stderr.status(meta.node, "ERROR BAD TARGET")
                status = False
                continue

            patterns = meta.pattern.split(",")
            for pattern in patterns:
                # Split by "/" and create regex for each path component
                regex = []
                for part in pattern.split("/"):
                    if part in (".", ".."):
                        regex.append(part) # just pass through the . and ..
                    else:
                        regex_str = fnmatch.translate(part).replace(
                            "FILEVERSION",
                            "(?P<version>[0-9\\.]+)"
                        )
                        regex.append(re.compile(regex_str))

                # Recursively apply meta using regex list
                self._applymeta_walk(parent, regex, meta)

        return status

    def _applymeta_walk(self, node, regex, meta, _version=None):
        """ Apply the metadata to the matching nodes. """

        if not regex:
            return

        # Check for "." and ".."
        while regex and regex[0] in (".", ".."):
            if regex.pop(0) == "..":
                if node.parent:
                    node = node.parent
                else:
                    pass # TODO: ERROR

        # Check if the meta applies to this directory
        if not regex: # After any . and .., nothing left
            meta.users.append(node)
            self.addmeta(node, meta, meta.meta)
            return

        # Find matching child nodes
        for name in sorted(node.children):
            child = node.children[name]

            match = regex[0].match(name)
            if match:
                # Get the version if specified
                try:
                    _version = match.group("version")
                except IndexError:
                    # keep current version value
                    pass

                if len(regex) == 1:
                    # last part of the regex so it applies to the found node
                    meta.users.append(child)
                    self.addmeta(child, meta, meta.meta)
                    if _version is not None:
                        self.addmeta(child, meta, meta.apply_version(_version))

                elif len(regex) > 1 and isinstance(child, collection.Directory):
                    # more nested regex to match, recurse if node is directory
                    self._applymeta_walk(child, regex[1:], meta, _version)

    def addmeta(self, node, meta, values):
        """ Add the metadata to the node. """

        # Accumulate the new meta
        for entry in values:
            entry = dict(entry)
            node.addmeta(entry.get("type", ""), entry)

        # Log
        if self.verbose:
            self.writer.stdout.status(
                node.prettypath,
                "META", "FROM: {0}:{1}".format(meta.node.prettypath, meta.name)
            )
            for entry in values:
                self.writer.stdout.status(node.prettypath, "META", str(dict(entry)))


ACTIONS = [UpdateMetaAction]
