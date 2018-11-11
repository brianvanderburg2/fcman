#!/usr/bin/env python3
# vim: foldmethod=marker foldmarker={{{,}}}, foldlevel=0
""" File collection management utility. """

# {{{1 Meta information

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"
__version__ = "20181110.1"


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
        self._stream.flush()


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
            if isinstance(path, (list, tuple)):
                path = "./" + "/".join(path)
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

    def reparent(self, parent):
        """ Move the node to the given parent. """

        assert parent.collection is self.collection

        # We must have a parent (can't reparent the root directory)
        if self.parent is None:
            return False

        # Must move to a directory
        if not isinstance(parent, Directory):
            return False

        # First walk up the parent and make sure it is not a child of ours
        node = parent
        while node:
            if node is self:
                return False
            node = node.parent

        # The new parent can't have a node with the same name
        if self.name in parent.children:
            return False

        # Remove from our parent and insert into new parent
        assert self.parent.children[self.name] is self
        self.parent.children.pop(self.name)

        # Add to new parent and update path
        self.parent = parent
        parent.children[self.name] = self
        self._update_pathlist()

        return True

    def rename(self, newname):
        """ Rename the node. """

        # Can't rename the root directory
        if self.parent is None:
            return False

        # Must have a name
        if not newname:
            return False

        # Check if name already exists
        if newname in self.parent.children:
            return False

        # Remove the current name
        assert self.parent.children[self.name] is self
        self.parent.children.pop(self.name)

        # Set and insert the new name and update the path
        self.name = newname
        self.parent.children[newname] = self
        self._update_pathlist()

        return True

    def delete(self):
        """ Remove this node. """

        # Can't remove the root directory
        if self.parent is None:
            return False

        # Remove the node from the parent
        assert self.parent.children[self.name] is self
        self.parent.children.pop(self.name)
        self.parent = None

        # If metadata is loaded (unlikely if this method is being called),
        # then some metadata may still point to this node.  Since the
        # application is a run and exit, no point release all the references

        return True

    def _update_pathlist(self):
        """ Recursively update the path list. """
        self.pathlist = self.parent.pathlist + (self.name,)
        if isinstance(self, Directory):
            for name in self.children:
                self.children[name]._update_pathlist()


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
        read = config.read(node.path)
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
        """ Apply meta information to matching nodes. """
        for meta in self.allmeta:
            parent = meta.node.parent
            pattern = meta.pattern

            # Split by "/" and create regex for each path component
            parts = [
                fnmatch.translate(part).replace(
                    "FILEVERSION",
                    "(?P<version>[0-9\\.]+)"
                )
                for part in pattern.split("/") if len(part)
            ]
            regex = [re.compile(part) for part in parts]

            # Recursively apply meta using regex list
            self._applymeta_walk(parent, regex, meta)

    def _applymeta_walk(self, node, regex, meta, _version=None):
        """ Apply the metadata to the matching nodes. """

        if len(regex) == 0:
            return

        # Check if the meta applies to this directory
        if len(regex) == 1 and regex[0].match("."):
            newmeta = meta.clone()
            node.meta.append(newmeta)
            meta.users.append(node)
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

                    newmeta = meta.clone()
                    child.meta.append(newmeta)

                    if _version is not None:
                        # Only apply autoname/autoversion if version was found
                        newmeta.provides.extend(
                            [(autoname, _version) for autoname in meta.autoname]
                        )

                elif len(regex) > 1 and isinstance(child, Directory):
                    # more nested regex to match, recurse if node is directory
                    self._applymeta_walk(child, regex[1:], meta, _version)


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

    def __init__(self, options, writer, verbose):
        self.collection = None
        self.root = os.getcwd() # A default, may be changed in child classes
        self.subpath = []
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

    def find_root(self):
        """ Find the root directory and set self.root, self.subpath.
            Return True on success or False on failure. """

        # We look for _collection/collection.xml
        head = os.getcwd()
        subpath = []

        while head:
            if os.path.isfile(os.path.join(head, "_collection", "collection.xml")):
                self.root = head
                self.subpath = subpath
                return True

            (head, tail) = os.path.split(head)
            if tail:
                subpath.insert(0, tail)
            else:
                break

        return False

    def load(self, find=None):
        if find is None:
            find = self.options.walk

        if find and not self.find_root():
            self.writer.stderr.status(os.getcwd(), "NOROOT")
            return False

        if self.verbose:
            self.writer.stdout.status(self.root, "ROOT")
            if self.subpath:
                self.writer.stdout.status(self.subpath, "SUBPATH")

        self.collection = Collection.load(self.root, self.writer, self.verbose)
        return True

    def normalize_path(self, path):
        """ Normalize a path and turn the normalized result.
            Return None if the path cannot be normalized. """

        if path is None or len(path) == 0:
            return self.subpath

        if not isinstance(path, (list, tuple)):
            path = [i for i in path.replace(os.sep, "/").split("/")]

        if path[0] == "": # started with "/"
            result = []
            path = path[1:]
        else:
            result = list(self.subpath)


        for part in path:
            if len(part) == 0:
                continue
            elif part == ".":
                continue
            elif part == "..":
                if len(result):
                    result.pop()
                else:
                    self.writer.stderr.status(path, "BADPATH")
                    return None
            else:
                result.append(part)

        return result

    def find_nearest_node(self, path):
        """ Find the node or the nearest parent node.
            Return is (node, remaining_path) """

        path = list(path)
        node = self.collection.rootnode

        while len(path):
            if not isinstance(node, Directory):
                break

            for name in node.children:
                if name == path[0]:
                    node = node.children[name]
                    path.pop(0)
                    break # break out of for loop
            else:
                break # break out of while loop if for loop wasn't broken

        # len(path) == 0 means we found the node, else just the nearest parent
        return (node, path)

    def find_node(self, path):
        """ Find the exact node or return None. """
        (node, remaining_path) = self.find_nearest_node(path)
        return node if not remaining_path else None


class CreateAction(Action):

    ACTION_NAME = "create"
    ACTION_DESC = "Create a collection"

    def run(self):
        # we always create in the current directory
        # TODO: don't create if already exists
        self.collection = Collection(self.root, self.writer, self.verbose)
        self.collection.save()
        return True


class CheckAction(Action):
    """ Check the collection. """

    ACTION_NAME = "check"
    ACTION_DESC = "Perform quick collection check"

    def __init__(self, *args, **kwargs):
        Action.__init__(self, *args, **kwargs)
        self._fullcheck = False

    @classmethod
    def add_arguments(cls, parser):
        super(CheckAction, cls).add_arguments(parser)
        parser.add_argument("path", nargs="?", default=".", help="Path to " + cls.ACTION_NAME)

    def run(self):
        if not self.load():
            return False

        path = self.normalize_path(self.options.path)
        if path is None:
            return False
        elif self.verbose:
            self.writer.stdout.status(path, "WORKPATH")

        node = self.find_node(path)
        if node is None:
            self.writer.stderr.status(path, "NONODE")
            return False


        if isinstance(node, Symlink):
            return self.handle_symlink(node)
        elif isinstance(node, File):
            return self.handle_file(node)
        elif isinstance(node, Directory):
            return self.handle_directory(node)
        else:
            return False

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
                if isinstance(newnode, Directory) and self.options.recurse:
                    self._missing_dir(newnode)


        # Check for new items
        for i in sorted(os.listdir(node.path)):
            if not node.ignore(i) and not i in node.children:
                self.writer.stdout.status(node.prettypath + "/" + i, 'NEW')
                status = False

                # Show new child items
                path = node.path + os.sep + i
                if os.path.isdir(path) and not os.path.islink(path) and self.options.recurse:
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
                elif isinstance(child, Directory) and self.options.recurse:
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


class UpdateAction(Action):
    """ Update the collection. """

    ACTION_NAME = "update"
    ACTION_DESC = "Update the collection"

    @classmethod
    def add_arguments(cls, parser):
        super(UpdateAction, cls).add_arguments(parser)
        parser.add_argument(
            "-f", "--force", dest="force", default=False,
            action="store_true", help="Always update the checksum."
        )
        parser.add_argument("path", nargs="?", default=".", help="Path to update")

    def run(self):
        if not self.load():
            return False

        path = self.normalize_path(self.options.path)
        if path is None:
            return False
        elif self.verbose:
            self.writer.stdout.status(path, "WORKPATH")

        node = self.find_node(path)
        if node is None:
            self.writer.stderr.status(path, "NONODE")
            return False

        if isinstance(node, Symlink):
            self.handle_symlink(node)
        elif isinstance(node, File):
            self.handle_file(node)
        elif isinstance(node, Directory):
            self.handle_directory(node)
        else:
            return False

        self.collection.save()
        return True

    def handle_symlink(self, node):
        target = os.readlink(node.path)
        if target != node.target:
            node.target = target
            self.writer.stdout.status(node.prettypath, "SYMLINK")

    def handle_file(self, node):
        stat = os.stat(node.path)

        if self.options.force or abs(node.timestamp - stat.st_mtime) > TIMEDIFF or node.size != stat.st_size or node.checksum == "":
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
            elif isinstance(child, Directory) and self.options.recurse:
                self.handle_directory(child)
            else:
                pass


class MoveAction(Action):
    """ Move a node to a new parent. """

    ACTION_NAME = "move"
    ACTION_DESC = "Move node to a new parent."

    @classmethod
    def add_arguments(cls, parser):
        """ Add our arguments. """
        super(MoveAction, cls).add_arguments(parser)
        parser.add_argument("path", help="The path of the node to move.")
        parser.add_argument("parent", help="The path of the new parent.")

    def run(self):
        if not self.load():
            return False

        nodepath = self.normalize_path(self.options.path)
        parentpath = self.normalize_path(self.options.parent)

        if nodepath is None or parentpath is None:
            return False

        node = self.find_node(nodepath)
        parent = self.find_node(parentpath)

        if node is None:
            self.writer.stderr.status(nodepath, "NONODE")

        if parent is None:
            self.writer.stderr.status(parentpath, "NONODE")

        if node is None or parent is None:
            return False

        if not node.reparent(parent):
            self.writer.stderr.status(nodepath, "NOMOVE")
            return False

        self.collection.save()
        return True


class RenameAction(Action):
    """ Rename a node. """

    ACTION_NAME = "rename"
    ACTION_DESC = "Rename a node."

    @classmethod
    def add_arguments(cls, parser):
        """ Add our arguments. """
        super(RenameAction, cls).add_arguments(parser)
        parser.add_argument("path", help="The path of the node to rename.")
        parser.add_argument("name", help="The name to rename to.")

    def run(self):
        if not self.load():
            return False

        nodepath = self.normalize_path(self.options.path)
        if nodepath is None:
            return False

        node = self.find_node(nodepath)
        if node is None:
            self.writer.stderr.status(nodepath, "NONODE")
            return False

        if not node.rename(self.options.name):
            self.writer.stderr.status(nodepath, "NORENAME")
            return False

        self.collection.save()
        return True


class DeleteAction(Action):
    """ Delete a node. """

    ACTION_NAME = "delete"
    ACTION_DESC = "Delete a node."

    @classmethod
    def add_arguments(cls, parser):
        """ Add our arguments. """
        super(DeleteAction, cls).add_arguments(parser)
        parser.add_argument("path", help="The path of the node to delete.")

    def run(self):
        if not self.load():
            return False

        nodepath = self.normalize_path(self.options.path)
        if nodepath is None:
            return False

        node = self.find_node(nodepath)
        if node is None:
            self.writer.stderr.status(nodepath, "NONODE")
            return False

        if not node.delete():
            self.writer.stderr.status(nodepath, "NODELETE")
            return False

        self.collection.save()
        return True


class AddAction(UpdateAction):
    """ Action to add a filesystem item to the collection. """
    ACTION_NAME = "add"
    ACTION_DESC = "Add a filesystem item to the collection"

    @classmethod
    def add_arguments(cls, parser):
        super(AddAction, cls).add_arguments(parser)

        parser.add_argument(
            "-p", "--parents", dest="parents", default=False,
            action="store_true", help="Create parent directory nodes if possible and needed"
        )
        parser.add_argument("path", help="The file system item to add.")

    def run(self):
        if not self.load():
            return False

        path = self.normalize_path(self.options.path)
        if path is None:
            return False

        (node, remaining) = self.find_nearest_node(path)
        if len(remaining) == 0:
            self.writer.stderr.status(path, "EXISTS")
            return False

        node = self._handle_parents(node, remaining[0:-1])
        if node is None:
            return False

        # Now we want to add the item to the node
        name = remaining[-1]
        path = os.path.join(node.path, name)

        if os.path.islink(path):
            item = Symlink(node, name, "")
            self.writer.stdout.status(item.prettypath, "ADDED")
            self.handle_symlink(item)
        elif os.path.isfile(path):
            item = File(node, name, 0, 0, "")
            self.writer.stdout.status(item.prettypath, "ADDED")
            self.handle_file(item)
        elif os.path.isdir(path):
            item = Directory(node, name)
            self.writer.stdout.status(item.prettypath, "ADDED")
            if self.options.recurse:
                self.handle_directory(item)
        else:
            return False

        self.collection.save()
        return True

    def _handle_parents(self, node, parts):
        """ Create each directory part (only if the given directory actually exists). """

        path = list(node.pathlist)
        while True:
            # All nodes should be directories
            if not isinstance(node, Directory):
                self.writer.stderr.status(path, "NOTDIRECTORY")
                return None

            # We can't add if the node's fs component does not exist
            if not node.exists():
                self.writer.stderr.status(path, "NOTEXIST")
                return None

            # If no more parts, return the directory node
            if len(parts) == 0:
                return node

            if not self.options.parents:
                self.writer.stderr.status(path, "NOPARENTS")
                return None

            # Check if the part is in the directory
            name = parts.pop(0)
            path.append(name)

            if name in node.children:
                # Should never happen since if it did exist, find_nearest_node would have it
                node = node.children[name]
            else:
                node = Directory(node, name)
                self.writer.stdout.status(node.prettypath, "ADDED")


class ExportAction(Action):
    """ Dump information about the collection. """

    ACTION_NAME = "export"
    ACTION_DESC = "Export information"

    def run(self):
        if not self.load():
            return False

        self.collection.loadmeta()
        self.collection.applymeta()

        exportdir = os.path.join(self.collection.datadir, "export")
        if not os.path.isdir(exportdir):
            os.makedirs(exportdir)

        md5file = os.path.join(exportdir, "md5sums.txt")
        infofile = os.path.join(exportdir, "info.txt")

        md5stream = TextFile(md5file)
        infostream = TextFile(infofile)

        streams = (md5stream, infostream)

        with md5stream:
            with infostream:
                self._handle_directory(self.collection.rootnode, streams)

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
        if not self.load():
            return False
        self.collection.loadmeta()
        self.collection.applymeta()

        status = True
        if not self._checkdeps():
            status = False

        if not self._checkmeta_used():
            status = False

        return status

    def _checkdeps(self):
        """ Check the dependencies. """

        # First gather all known packages that are actaully attached to a node
        packages = {}
        self._checkdeps_walk_collect(self.collection.rootnode, packages)

        # Next check all dependencies from the nodes have a package to satisfy
        return self._checkdeps_walk(self.collection.rootnode, packages)

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

    def _checkmeta_used(self):
        for meta in self.collection.allmeta:
            if not meta.users:
                self.writer.stdout.status(meta.node.prettypath, "UNUSEDMETA", meta.name)


class UpgradeAction(Action):
    """ Perform upgrade of collection. """

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


class FindTagAction(Action):
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
        parser.add_argument(
            "tags",
            nargs="+",
            help="List of tags to find."
        )

    def run(self):
        if not self.load():
            return False

        self.collection.loadmeta()
        self.collection.applymeta()

        node = self.find_node(self.subpath)
        if node is None:
            self.writer.stderr.status(self.subpath, "NONODE")
            return False

        return self._handle_node(node)

    def _handle_node(self, node):
        status = False

        alltags = set(tag.lower() for meta in node.meta for tag in meta.tags)
        findtags = set(tag.lower() for tag in self.options.tags)

        found = findtags.intersection(alltags)

        if self.options.match_all:
            matched = (found == findtags)
        else:
            matched = len(found) > 0

        if matched:
            status = True
            self.writer.stdout.status(node.prettypath, "FINDTAG", ",".join(sorted(found)))

        if isinstance(node, Directory):
            for child in sorted(node.children):
                if self._handle_node(node.children[child]):
                    status = True

        return status


class FindDescAction(Action):
    """ Find paths that match specific descriptions. """

    ACTION_NAME = "finddesc"
    ACTION_DESC = "Find paths that match specific descriptions."

    @classmethod
    def add_arguments(cls, parser):
        super(FindDescAction, cls).add_arguments(parser)

        parser.add_argument(
            "-a", "--all",
            dest="match_all",
            default=False,
            action="store_true",
            help="Report paths only if the path has all descriptions specified."
        )
        parser.add_argument(
            "descs",
            nargs="+",
            help="List of descriptions to find."
        )

    def run(self):
        if not self.load():
            return False

        node = self.find_node(self.subpath)
        if node is None:
            self.writer.stderr.status(self.subpath, "NONODE")
            return False

        self.collection.loadmeta()
        self.collection.applymeta()

        return self._handle_node(node)

    def _handle_node(self, node):
        status = False

        alldescs = "".join(meta.description.lower() for meta in node.meta if meta.description)
        finddescs = set(i.lower() for i in self.options.descs)
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

        if isinstance(node, Directory):
            for child in sorted(node.children):
                if self._handle_node(node.children[child]):
                    status = True

        return status


# {{{1 Program entry point

def create_arg_parser():
    parser = argparse.ArgumentParser()

    # Base arguments
    parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true")
    parser.add_argument("-w", "--walk", dest="walk", default=False, action="store_true")
    parser.add_argument("-x", "--no-recurse", dest="recurse", default=True, action="store_false")
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

    def _signal(self, sig, stack):
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
    if not action(options, writer, verbose).run():
        return -1

if __name__ == '__main__':
    sys.exit(main())

