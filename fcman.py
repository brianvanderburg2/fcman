#!/usr/bin/env python3
# vim: foldmethod=marker foldmarker={{{,}}}, foldlevel=0
""" File collection management utility. """

# {{{1 Meta information

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"
__version__ = "20181107.1"


# {{{1 Imports

import argparse
from configparser import SafeConfigParser
import fnmatch
import hashlib
import io
import os
import re
import sys
import time

try:
    from lxml import etree as ET
    PRETTY_PRINT = True
except ImportError:
    PRETTY_PRINT = False
    try:
        from xml.etree import cElementTree as ET
    except ImportError:
        from xml.etree import ElementTree as ET

# {{{1 Checks

if sys.version_info[0:2] < (3, 2):
    sys.exit("This program requires Python 3.2 or greater")

# {{{1 Utilities and constants

# Time difference to consider a file's timestamp changed
TIMEDIFF = 2

# Use namespaces for reading, but now only write without namespaces
NS_COLLECTION = "{urn:mrbavii.fcman:collection}"


class StreamWriter(object):
    """ Write to a given stream. """

    class _IndentContextManager(object):
        """ Provide a context manager for the indentation of a stream. """

        def __init__(self, writer):
            self._writer = writer

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            self._writer.dedent()

    def __init__(self, stream, indent="    "):
        """ Initialze the writer. """
        self._stream = stream
        self._indent_level = 0
        self._indent_text = indent

    def indent(self):
        """ Increase the indent. """
        self._indent_level += 1
        return self._IndentContextManager(self)

    def dedent(self):
        """ Decrease the indent. """
        self._indent_level -= 1

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._stream.close()
        self._stream = None

    def writeln(self, line):
        """ Write a line of text to the stream. """
        self._stream.write(self._indent_level * self._indent_text)
        self._stream.write(line)
        self._stream.write("\n")


class LogWriter(StreamWriter):
    """ A stream writer with status methods. """

    def __init__(self, *args, **kwargs):
        """ Initialize the writer. """
        StreamWriter.__init__(self, *args, **kwargs)
        self._last = None

    def status(self, path, status, msg=None):
        """ Show the status with optional message.
            If the same path/status is used consecutively, only the message
            will be shown after the first status until the path/status changes
        """
        check = (path, status)
        if check != self._last:
            self._last = check
            self.writeln(status + ":" + path)

        if msg:
            with self.indent():
                self.writeln("> " + msg)


class TextFile(StreamWriter):
    """ A text file based on StreamWriter. """

    def __init__(self, filename):
        """ Initialize the text file. """
        stream = io.open(filename, "wt", encoding="utf-8", newline="\n")
        StreamWriter.__init__(self, stream)


class Writer(object):
    """ Wrapper for stdout and stderr streams. """

    def __init__(self):
        """ Initialize teh writer. """

        self.stdout = LogWriter(sys.stdout)
        self.stderr = LogWriter(sys.stderr)

# {{{1 Collection classes

class Node(object):
    """ A node represents a file, symlink, or directory in the collection. """

    def __init__(self, parent, name):
        """ Initialize the node with the parent and name. """
        self.name = name
        self.parent = parent
        self.meta = []

        if parent is not None:
            parent.children[name] = self
            self.collection = parent.collection
            self.pathlist = parent.pathlist + (name,)
        else:
            assert isinstance(self, RootDirectory)
            assert name is None
            self.pathlist = ()

    @property
    def path(self):
        """ Return the filesystem path of the node. """
        return os.path.join(
            self.collection.root,
            *self.pathlist
        )

    @property
    def prettypath(self):
        """ Return the relative path of the node under root. Each segment is
            separated by a forward slash. """
        if self.pathlist:
            return "./" + "/".join(self.pathlist)
        else:
            return "."

    # Load and save
    @classmethod
    def load(cls, parent, xml):
        """ Load information from the XML and create the child node under the
            parent node. """
        raise NotImplementedError

    def save(self, xml):
        """ Save information to the XML element. """
        raise NotImplementedError

    def exists(self):
        """ Test if the filesystem path exists. """
        raise NotImplementedError


class Symlink(Node):
    """ A symbolic link node. """

    def __init__(self, parent, name, target):
        """ Initialize the symlink node. """
        Node.__init__(self, parent, name)
        self.target = target

    @classmethod
    def load(cls, parent, xml):
        """ Load the symlink node from XML. """
        name = xml.get('name')
        target = xml.get('target')

        return Symlink(parent, name, target)

    def save(self, xml):
        """ Save the symlink node to XML. """
        xml.set('name', self.name)
        xml.set('target', self.target)

    def exists(self):
        """ Test if the symlink exists. """
        return os.path.islink(self.path)


class File(Node):
    """ A file node """

    def __init__(self, parent, name, size, timestamp, checksum):
        """ Initialize the file node. """
        Node.__init__(self, parent, name)

        self.size = size
        self.timestamp = timestamp
        self.checksum = checksum

    @classmethod
    def load(cls, parent, xml):
        """ Load the file node from XML. """
        name = xml.get('name')
        size = xml.get('size', -1)
        timestamp = xml.get('timestamp', -1)
        checksum = xml.get('checksum')

        return File(parent, name, int(size), int(timestamp), checksum)

    def save(self, xml):
        """ Save the file node to XML. """
        xml.set('name', self.name)
        xml.set('size', str(self.size))
        xml.set('timestamp', str(self.timestamp))
        xml.set('checksum', self.checksum)

    def calc_checksum(self):
        """ Calculate the checksum and return the result. """
        hasher = hashlib.md5()

        with open(self.path, 'rb') as handle:
            data = handle.read(4096000)
            while len(data):
                hasher.update(data)
                data = handle.read(4096000)

        return hasher.hexdigest()

    def exists(self):
        """ Test if the file exists. """
        return os.path.isfile(self.path) and not os.path.islink(self.path)


class Directory(Node):
    """ A directory node """

    def __init__(self, parent, name):
        """ Initialize the directory node. """
        Node.__init__(self, parent, name)
        self.children = {}

    @classmethod
    def load(cls, parent, xml):
        """ Load the directory node from XML. """
        # If parent is a collection object, then we are a RootDirectory
        if isinstance(parent, Collection):
            dir = RootDirectory(parent)
        else:
            name = xml.get('name')
            dir = Directory(parent, name)

        for child in xml:
            if child.tag in ('symlink', NS_COLLECTION + 'symlink'):
                Symlink.load(dir, child)
            elif child.tag in ('directory', NS_COLLECTION + 'directory'):
                Directory.load(dir, child)
            elif child.tag in ('file', NS_COLLECTION + 'file'):
                File.load(dir, child)

        return dir

    def save(self, xml):
        """ Save the directory node to XML. """
        if not isinstance(self, RootDirectory):
            xml.set('name', self.name)

        for name in sorted(self.children):
            child = self.children[name]

            if isinstance(child, Symlink):
                tag = 'symlink'
            elif isinstance(child, File):
                tag = 'file'
            elif isinstance(child, Directory):
                tag = 'directory'
            else:
                pass

            element = ET.SubElement(xml, tag)
            child.save(element)

    def ignore(self, name):
        """ Ignore certain files under the directory. """
        if self.pathlist == ("_collection",):
            if name.lower() in ("collection.xml", "backups", "export"):
                return True
        return False

    def exists(self):
        """ Test if the directory exists. """
        return os.path.isdir(self.path) and not os.path.islink(self.path)


class RootDirectory(Directory):
    """ The root directory. """

    def __init__(self, collection):
        """ Initialize the root directory. """
        self.collection = collection
        Directory.__init__(self, None, None)


class Collection(object):
    """ This is the collection object. """

    def __init__(self, root, writer, verbose):
        """ Initialize the collection with the root of the collection. """

        self.root = root
        self.writer = writer
        self.verbose = verbose
        self.rootnode = RootDirectory(self)
        self.allmeta = []
        self.datadir = os.path.join(root, "_collection")
        self._filename = os.path.join(self.datadir, 'collection.xml')
        self._backupname = os.path.join(
            self.datadir, 'backups', 'collection.xml.' +
            time.strftime("%Y%m%d%H%M%S")
        )

    @classmethod
    def load(cls, root, writer, verbose):
        """ Function to load a file and return the collection object. """
        coll = Collection(root, writer, verbose)

        tree = ET.parse(coll._filename)
        root = tree.getroot()
        if not root.tag in ('collection', NS_COLLECTION + 'collection'):
            return None

        # Load the root node
        coll.rootnode = RootDirectory.load(coll, root)

        return coll

    def save(self):
        """ Save the collection to XML. """
        root = ET.Element('collection')
        self.rootnode.save(root)

        tree = ET.ElementTree(root)

        for i in (os.path.dirname(j) for j in (self._backupname, self._filename)):
            if not os.path.isdir(i):
                os.makedirs(i)

        # Move new filename over
        if os.path.exists(self._filename):
            if os.path.exists(self._backupname):
                os.unlink(self._backupname)
            os.rename(self._filename, self._backupname)

        # We don't need to use codecs here as ElementTree actually does the
        # encoding based on the enconding= parameter, unlike xml.dom.minidom
        if PRETTY_PRINT:
            kwargs = {"pretty_print": True}
        else:
            kwargs = {}

        tree.write(self._filename, encoding='utf-8', xml_declaration=True,
                   method='xml', **kwargs)

    def loadmeta(self):
        """ Walk over each directory for a "fcmanmeta.xml" file """

        status = True

        # First we load all the meta files
        node = self.rootnode
        if not self._loadmeta_walk(node):
            status = False

        return status

    def _loadmeta_walk(self, node):
        status = True
        for i in sorted(node.children):
            child = node.children[i]

            if i == "fcmeta.ini":
                if not self._loadmeta(child):
                    status = False

            elif isinstance(child, Directory):
                self._loadmeta_walk(child)

        return status

    def _loadmeta(self, node):
        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'LOADING')

        config = SafeConfigParser()
        read = config.read(node.prettypath)
        if not read:
            self.writer.stderr.status(node.prettypath, 'LOAD ERROR')
            return False

        # Should at least have fcmeta section
        if not config.has_section("fcman:fcmeta"):
            self.writer.stderr.status(node.prettypath, 'NOTMETAINFO')
            return False

        sections = config.sections()
        for name in sections:
            if name == "fcman:fcmeta":
                continue

            meta = MetaInfo.load(node, name, dict(config.items(name)))
            self.allmeta.append(meta)

    def applymeta(self):
        """ Walk over all loaded meta information and match the patterns
            to the nodes. """

        for meta in self.allmeta:
            node = meta.node
            pattern = meta.pattern
            parent = node.parent

            if pattern == ".":
                newmeta = meta.clone()
                parent.meta.append(newmeta)
                meta.users.append(parent)
                continue

            if pattern[0:2] == "r:":
                pattern = pattern[2:].replace("(@)", "(?P<version>[0-9\\.]+)")
                regex = re.compile(pattern)
                def matchfn(name, _regex=regex):
                    result = _regex.match(name)
                    if result:
                        try:
                            version = result.group("version")
                        except IndexError:
                            version = None
                        return (True, version)
                    else:
                        return (False, None)
            else:
                def matchfn(name, _pattern=pattern):
                    return (fnmatch.fnmatchcase(name, _pattern), None)

            for name in sorted(parent.children):
                (matched, version) = matchfn(name)
                if matched:
                    child = parent.children[name]
                    meta.users.append(child)

                    newmeta = meta.clone()
                    child.meta.append(newmeta)

                    if meta.autoname:
                        for autoname in meta.autoname:
                            newmeta.provides.append((autoname, version))


class MetaInfo(object):
    """ Represent metadata. """

    def __init__(self, node):
        """ Initial state of metadata. """
        self.node = node
        self.users = []
        self.name = None
        self.pattern = None
        self.autoname = []
        self.provides = []
        self.depends = []
        self.tags = []
        self.description = None


    @classmethod
    def load(cls, node, name, config):
        """ Load metadata from an INI config section. """

        meta = MetaInfo(node)

        def splitval(val):
            val = ''.join(map(lambda ch: ',' if ch in " \t\r\n" else ch, val))
            return list(filter(lambda i: len(i) > 0, val.split(',')))

        meta.name = name

        # pattern
        if "pattern" in config:
            meta.pattern = config.get("pattern")
        else:
            # Allow using the config section name as the pattern when possible
            # so the user can just do [*.txt] instead of [textfiles]\npattern=*.txt
            meta.pattern = name

        if "autoname" in config:
            meta.autoname = splitval(config["autoname"])

        # provides
        if "provides" in config:
            provides = splitval(config["provides"])
            for i in provides:
                parts = i.split(":")
                meta.provides.append((
                    parts[0],
                    parts[1] if len(parts) > 1 and len(parts[1]) else None
                ))

        # depends
        if "depends" in config:
            depends = splitval(config["depends"])
            for i in depends:
                parts = i.split(":")
                meta.depends.append((
                    parts[0],
                    parts[1] if len(parts) > 1 and len(parts[1]) else None,
                    parts[2] if len(parts) > 2 and len(parts[2]) else None
                ))
        # tags
        meta.tags = []
        if "tags" in config:
            meta.tags = splitval(config["tags"])

        # description
        if "description" in config:
            desc = config["description"].strip()
            desc = " ".join([line.strip() for line in desc.splitlines() if len(line)])
            meta.description = desc


        return meta

    def clone(self):
        """ Make a copy of the meta but with no users. """
        newmeta = MetaInfo(self.node)
        newmeta.name = self.name
        newmeta.pattern = self.pattern
        newmeta.autoname = list(self.autoname)
        newmeta.provides = list(self.provides)
        newmeta.depends = list(self.depends)
        newmeta.tags = list(self.tags)
        newmeta.description = self.description

        return newmeta

# {{{1 Actions

class Action(object):
    """ A base action. """

    ACTION_NAME = None
    ACTION_DESC = ""

    def __init__(self, root, options, writer, verbose):
        self.root = root
        self.options = options
        self.writer = writer
        self.verbose = verbose

    def run(self):
        raise NotImplementedError

    @classmethod
    def get_subclasses(cls):
        my_subclasses = set(cls.__subclasses__())
        return my_subclasses.union(
            [s for c in cls.__subclasses__() for s in c.get_subclasses()]
        )

    @classmethod
    def add_arguments(cls, parser):
        pass

    @classmethod
    def parse_arguments(cls, options):
        pass


class CreateAction(Action):

    ACTION_NAME = "create"
    ACTION_DESC = "Create a collection"

    def run(self):
        coll = Collection(self.root, self.writer, self.verbose)
        coll.save()
        return True


class CheckAction(Action):
    """ Check the collection. """

    ACTION_NAME = "check"
    ACTION_DESC = "Perform quick collection check"

    def __init__(self, *args, **kwargs):
        Action.__init__(self, *args, **kwargs)
        self._fullcheck = False

    def run(self):
        coll = Collection.load(self.root, self.writer, self.verbose)
        return self.handle_directory(coll.rootnode)

    def _missing_dir(self, node):
        for i in sorted(node.children):
            newnode = node.children[i]

            self.writer.stdout.status(newnode.prettypath, 'MISSING')
            if isinstance(newnode, Directory):
                self._missing_dir(newnode)

    def handle_symlink(self, node):
        target = os.readlink(node.path)
        if target != node.target:
            self.writer.stdout.status(node.prettypath, 'SYMLINK')
            return False

        return True

    def handle_file(self, node):
        status = True
        stat = os.stat(node.path)

        if abs(node.timestamp - stat.st_mtime) > TIMEDIFF:
            status = False
            self.writer.stdout.status(node.prettypath, 'TIMESTAMP')

        if node.size != stat.st_size:
            status = False
            self.writer.stdout.status(node.prettypath, 'SIZE')

        if self._fullcheck:
            if self.verbose:
                self.writer.stdout.status(node.prettypath, 'PROCESSING')
            if node.checksum != node.calc_checksum():
                status = False
                self.writer.stdout.status(node.prettypath, 'CHECKSUM')

        return status

    def handle_directory(self, node):
        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')
        status = True

        # Check for missing
        for i in sorted(node.children):
            newnode = node.children[i]

            if node.ignore(i):
                self.writer.stdout.status(newnode.prettypath, 'SHOULDIGNORE')
            if not newnode.exists():
                self.writer.stdout.status(newnode.prettypath, 'MISSING')
                status = False

                # Report all subitems
                if isinstance(newnode, Directory):
                    self._missing_dir(newnode)


        # Check for new items
        for i in sorted(os.listdir(node.path)):
            if not node.ignore(i) and not i in node.children:
                self.writer.stdout.status(node.prettypath + "/" + i, 'NEW')
                status = False

                # Show new child items
                path = node.path + os.sep + i
                if os.path.isdir(path) and not os.path.islink(path):
                    newnode = Directory(node, i)

                    orig = self._fullcheck
                    self._fullcheck = False
                    self.handle_directory(newnode)
                    self._fullcheck = orig

                    del node.children[i]

        # Check children
        for i in sorted(node.children):
            child = node.children[i]
            if child.exists():
                if isinstance(child, Symlink):
                    if not self.handle_symlink(child):
                        status = False
                elif isinstance(child, File):
                    if not self.handle_file(child):
                        status = False
                elif isinstance(child, Directory):
                    if not self.handle_directory(child):
                        status = False
                else:
                    pass

        return status


class VerifyAction(CheckAction):
    """ Verify the collection. """

    ACTION_NAME = "verify"
    ACTION_DESC = "Perform full checksum verification"

    def __init__(self, *args, **kwargs):
        CheckAction.__init__(self, *args, **kwargs)
        self._fullcheck = True

    def run(self):
        coll = Collection.load(self.root, self.writer, self.verbose)
        return self.handle_directory(coll.rootnode)


class UpdateAction(Action):
    """ Update the collection. """

    ACTION_NAME = "update"
    ACTION_DESC = "Update the collection"

    def run(self):
        coll = Collection.load(self.root, self.writer, self.verbose)
        self.handle_directory(coll.rootnode)
        coll.save()
        return True

    def handle_symlink(self, node):
        target = os.readlink(node.path)
        if target != node.target:
            node.target = target
            self.writer.stdout.status(node.prettypath, "SYMLINK")

    def handle_file(self, node):
        stat = os.stat(node.path)

        if abs(node.timestamp - stat.st_mtime) > TIMEDIFF or node.size != stat.st_size or node.checksum == "":
            if self.verbose:
                self.writer.stdout.status(node.prettypath, 'PROCESSING')
            node.checksum = node.calc_checksum()
            node.timestamp = int(stat.st_mtime)
            node.size = stat.st_size
            self.writer.stdout.status(node.prettypath, 'CHECKSUM')

    def handle_directory(self, node):
        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')

        # Check for missing items
        for i in sorted(node.children):
            child = node.children[i]
            if node.ignore(i):
                del node.children[i]
                self.writer.stdout.status(child.prettypath, 'IGNORED')
            elif not child.exists():
                del node.children[i]
                self.writer.stdout.status(child.prettypath, 'DELETED')

        # Add new items
        for i in sorted(os.listdir(node.path)):
            if not node.ignore(i) and not i in node.children:
                path = node.path + os.sep + i

                if os.path.islink(path):
                    item = Symlink(node, i, "")
                elif os.path.isfile(path):
                    item = File(node, i, 0, 0, "")
                elif os.path.isdir(path):
                    item = Directory(node, i)
                else:
                    continue # Unsupported item type, will be reported missing with check

                self.writer.stdout.status(item.prettypath, 'ADDED')

        # Update all item including newly added items
        for i in sorted(node.children):
            child = node.children[i]
            if isinstance(child, Symlink):
                self.handle_symlink(child)
            elif isinstance(child, File):
                self.handle_file(child)
            elif isinstance(child, Directory):
                self.handle_directory(child)
            else:
                pass


class ExportAction(Action):
    """ Dump information about the collection. """

    ACTION_NAME = "export"
    ACTION_DESC = "Export information"

    def run(self):
        coll = Collection.load(self.root, self.writer, self.verbose)
        coll.loadmeta()
        coll.applymeta()

        exportdir = os.path.join(coll.datadir, "export")
        if not os.path.isdir(exportdir):
            os.makedirs(exportdir)

        md5file = os.path.join(exportdir, "md5sums.txt")
        infofile = os.path.join(exportdir, "info.txt")

        md5stream = TextFile(md5file)
        infostream = TextFile(infofile)

        streams = (md5stream, infostream)

        with md5stream:
            with infostream:
                self._handle_directory(coll.rootnode, streams)

    def _handle_directory(self, node, streams):
        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')

        streams[1].writeln("Directory: {0}".format(node.prettypath))

        if node.meta:
            self._dumpmeta(node, streams)

        for child in sorted(node.children):
            streams[1].writeln("")
            childnode = node.children[child]
            if isinstance(childnode, Symlink):
                self._handle_symlink(childnode, streams)
            elif isinstance(childnode, File):
                self._handle_file(childnode, streams)
            elif isinstance(childnode, Directory):
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
            streams[0].writeln(node.checksum + ' *' + node.prettypath[2:])
        else:
            self.writer.stdout.status(node.prettypath, "MISSING CHECKSUM")

        if node.meta:
            self._dumpmeta(node, streams)

    def _dumpmeta(self, node, streams):
        provides = [provided for meta in node.meta for provided in meta.provides]
        if provides:
            streams[1].writeln("Provides: {0}".format(
                ", ".join(
                    "{0}{1}".format(
                        name,
                        ":" + version if version is not None else ""
                    )
                    for (name, version) in provides
                )
            ))

        depends = [depended for meta in node.meta for depended in meta.depends]
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

        tags = set(tag for meta in node.meta for tag in meta.tags)
        if tags:
            streams[1].writeln("Tags: {0}".format(
                ", ".join(sorted(tags))
            ))

        descriptions = "\n".join(meta.description for meta in node.meta if meta.description)
        if descriptions:
            import textwrap
            lines = textwrap.wrap(descriptions, 75)
            streams[1].writeln("Description:\n  {0}".format(
                "\n  ".join(lines)
            ))


class CheckMetaAction(Action):
    """ Check the metadata (dependencies/etc). """

    ACTION_NAME = "checkmeta"
    ACTION_DESC = "Check metadata, dependencies, etc"

    def run(self):
        coll = Collection.load(self.root, self.writer, self.verbose)
        coll.loadmeta()
        coll.applymeta()

        status = True
        if not self._checkdeps(coll):
            status = False

        if not self._checkmeta_used(coll):
            status = False

        return status

    def _checkdeps(self, coll):
        """ Check the dependencies. """

        # First gather all known packages that are actaully attached to a node
        packages = {}
        self._checkdeps_walk_collect(coll.rootnode, packages)

        # Next check all dependencies from the nodes have a package to satisfy
        return self._checkdeps_walk(coll.rootnode, packages)

    def _checkdeps_walk_collect(self, node, packages):
        for meta in node.meta:
            for (name, version) in meta.provides:
                if not name in packages:
                    packages[name] = set()
                packages[name].add(version)

        if isinstance(node, Directory):
            for child in sorted(node.children):
                self._checkdeps_walk_collect(node.children[child], packages)

    def _checkdeps_walk(self, node, packages):
        status = True

        if node.meta:
            for meta in node.meta:
                for depends in meta.depends:
                    if not self._checkdeps_find(depends, packages):
                        status = False
                        self.writer.stdout.status(node.prettypath, "DEPENDS", str(depends))

        if isinstance(node, Directory):
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

    def _checkdeps_compare(self, ver1, ver2):
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

    def _checkmeta_used(self, coll):
        for meta in coll.allmeta:
            if not meta.users:
                self.writer.stdout.status(meta.node.prettypath, "UNUSEDMETA", meta.name)


class UpgradeAction(Action):

    ACTION_NAME = "upgrade"
    ACTION_DESC = "Upgrade collection information. """

    def run(self):
        if not self._upgrade1():
            return False

        return True

    def _upgrade1(self):
        orig_filename = os.path.join(self.root, "collection.xml")
        new_filename = os.path.join(self.root, "_collection", "collection.xml")

        if not os.path.exists(new_filename) and os.path.exists(orig_filename):
            self.writer.stdout.status("./", "UPGRADE", "Moving collection.xml to _collection/collection.xml")

            dirname = os.path.join(self.root, "_collection")
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            os.rename(orig_filename, new_filename)
            return True



# {{{1 Program entry point

def create_arg_parser():
    parser = argparse.ArgumentParser()

    # Base arguments
    parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true")
    parser.set_defaults(action=None)

    # Add commands
    commands = filter(lambda cls: cls.ACTION_NAME is not None, Action.get_subclasses())
    subparsers = parser.add_subparsers()

    for i in commands:
        subparser = subparsers.add_parser(i.ACTION_NAME, help=i.ACTION_DESC)
        i.add_arguments(subparser)
        subparser.set_defaults(action=i)

    return parser


class VerboseChecker(object):

    def __init__(self, verbose):
        self._verbose = verbose
        self._signalled = False

        try:
            import signal
            signal.signal(signal.SIGUSR1, self._signal)
        except ImportError:
            pass

    def _signal(self):
        self._signalled = True

    def __bool__(self):
        result = self._verbose or self._signalled
        self._signalled = False
        return result

    __nonzero__ = __bool__


def main():
    # Check arguments
    parser = create_arg_parser()
    options = parser.parse_args()
    action = options.action
    if action is None:
        parser.print_help()
        parser.exit()
    action.parse_arguments(options)

    verbose = VerboseChecker(options.verbose)
    writer = Writer()


    # Do stuff
    root = os.getcwd()

    if not action(root, options, writer, verbose).run():
        return -1

if __name__ == '__main__':
    sys.exit(main())

