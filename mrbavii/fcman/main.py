#!/usr/bin/env python3
# vim: foldmethod=marker foldmarker={{{,}}}, foldlevel=0
# pylint: disable=too-many-lines,missing-docstring
""" File collection management utility. """

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright 2000-2019"
__license__ = "MIT"

# {{{1 Meta information

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"
__version__ = "20190303.1"


# {{{1 stdout vs stderr

# stderr should be for when a program error occurs
# - Any exception raised and not handled
# - A file unable to be opened, read or written

# stdout is used other times
# - since fcman is essentially a status program, status such as missing or
#   new items, bad dependencies, etc, should go to stdout
# - in verbose mode, non-error verbose information goes to stdout


# Still need to add better error handling and printing


# {{{1 Imports

import argparse
from configparser import SafeConfigParser
import fnmatch
import hashlib
import io
import os
import re
import sys

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


def splitval(val):
    """ Split a string into a list of non-empty values by comman or whitespace. """
    val = ''.join(map(lambda ch: ',' if ch in " \t\r\n" else ch, val))
    return list(filter(lambda i: len(i) > 0, val.split(',')))


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
                path = "/" + "/".join(path)
            elif isinstance(path, Node):
                path = path.prettypath
            self.writeln(status + ":" + path)

        if msg is not None:
            if isinstance(msg, Node):
                msg = msg.prettypath
            with self.indent():
                self.writeln("> " + msg)


class TextFile(StreamWriter):
    """ A text file based on StreamWriter. """

    def __init__(self, filename):
        """ Initialize the text file. """
        stream = io.open(filename, "wt", encoding="utf-8", newline="\n")
        StreamWriter.__init__(self, stream)


class StdStreamWriter(object):
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
        self.meta = dict()

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
        """ Return the path of the node under root. Each segment is
            separated by a forward slash. """
        return "/" + "/".join(self.pathlist)

    # Load and save meta
    def _loadmeta(self, xml):
        """ Load metadata for node. """
        self.meta = dict()
        for child in xml:
            if child.tag == "meta":
                metatype = child.get("type", "")
                metaset = self.meta.setdefault(metatype, set())
                metaset.add(frozenset(child.items()))

    def _savemeta(self, xml):
        """ Save metadata to xml. """
        for metatype in sorted(self.meta):
            for meta in self.meta[metatype]:
                ET.SubElement(xml, "meta", attrib=dict(meta))

    def addmeta(self, metatype, metadata):
        """ Add metadata. """
        metadata = dict(metadata)
        metadata["type"] = metatype

        metaset = self.meta.setdefault(metatype, set())
        metaset.add(frozenset(metadata.items()))

    def getmeta(self, metatype=None):
        """ Get metadata.  Generator yields dict for each metadata. """
        if metatype is not None:
            for metaset in self.meta.get(metatype, ()):
                yield dict(metaset)
        else:
            for metatype in sorted(self.meta):
                for metaset in self.meta[metatype]:
                    yield dict(metaset)

    def clearmeta(self):
        """ Clear metadata. """
        self.meta = dict()

    # Load and save
    @classmethod
    def load(cls, parent, xml):
        """ Load the node from the XML and load metadata from that. """
        # pylint: disable=protected-access
        node = cls._load(parent, xml)
        node._loadmeta(xml)

        return node

    @classmethod
    def _load(cls, parent, xml):
        """ Load information from the XML and create the child node under the
            parent node. """
        raise NotImplementedError

    def save(self, xml):
        """ Save the node and metadata to the XML element. """
        self._savemeta(xml)
        return self._save(xml)

    def _save(self, xml):
        """ Save information to the XML element. """
        raise NotImplementedError

    # Access/manupulate node
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

        return True

    def _update_pathlist(self):
        """ Update the path list when node is renamed or moved. """
        self.pathlist = self.parent.pathlist + (self.name,)


class Symlink(Node):
    """ A symbolic link node. """

    def __init__(self, parent, name, target):
        """ Initialize the symlink node. """
        Node.__init__(self, parent, name)
        self.target = target

    @classmethod
    def _load(cls, parent, xml):
        """ Load the symlink node from XML. """
        name = xml.get('name')
        target = xml.get('target')

        return Symlink(parent, name, target)

    def _save(self, xml):
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
    def _load(cls, parent, xml):
        """ Load the file node from XML. """
        name = xml.get('name')
        size = xml.get('size', -1)
        timestamp = xml.get('timestamp', -1)
        checksum = xml.get('checksum')

        return File(parent, name, int(size), int(timestamp), checksum)

    def _save(self, xml):
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
        self.ignore_patterns = []

    @classmethod
    def _load(cls, parent, xml):
        """ Load the directory node from XML. """
        # If parent is a collection object, then we are a RootDirectory
        if isinstance(parent, Collection):
            dir = RootDirectory(parent)
        else:
            name = xml.get('name')
            dir = Directory(parent, name)

        dir.ignore_patterns = []
        for pattern in xml.get("ignore", "").split(","):
            if pattern:
                dir.ignore_patterns.append(pattern)

        for child in xml:
            if child.tag == 'symlink':
                Symlink.load(dir, child)
            elif child.tag == 'directory':
                Directory.load(dir, child)
            elif child.tag == 'file':
                File.load(dir, child)

        return dir

    def _save(self, xml):
        """ Save the directory node to XML. """
        if not isinstance(self, RootDirectory):
            xml.set('name', self.name)

        if self.ignore_patterns:
            xml.set("ignore", ",".join(self.ignore_patterns))

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
        for i in self.ignore_patterns:
            if fnmatch.fnmatch(name, i):
                return True

        for meta in self.getmeta("ignore"):
            if fnmatch.fnmatch(name, meta.get("pattern", "")):
                return True

        return False

    def exists(self):
        """ Test if the directory exists. """
        return os.path.isdir(self.path) and not os.path.islink(self.path)

    def _update_pathlist(self):
        """ Update the path list recursively for children. """
        Node._update_pathlist(self)
        for name in self.children:
            self.children[name]._update_pathlist()


class RootDirectory(Directory):
    """ The root directory. """

    def __init__(self, collection):
        """ Initialize the root directory. """
        self.collection = collection
        Directory.__init__(self, None, None)


class Collection(object):
    """ This is the collection object. """

    def __init__(self, root):
        """ Initialize the collection with the root of the collection. """

        self.root = os.path.normpath(root) if root is not None else None
        self.rootnode = RootDirectory(self)
        self.autoroot = "."
        self.dirty = False # This flag is set externally by actions to indicate to save

    def normalize(self, path):
        """ Normalize an external path to be relative to the collection root. """
        if path is None:
            return None

        # Find the relative path, then apply corrections
        # relpath already normalizes "." and ".."
        relpath = os.path.relpath(path, self.root)

        # relpath should be a subpath (or ".") of root
        if os.path.isabs(relpath):
            return None

        parts = []
        for i in relpath.replace(os.sep, "/").split("/"):
            if i in ("..", os.pardir): # Shouldn't be in relpath from root to item
                return None

            if i == ".": # Skip "."
                continue

            if i:
                parts.append(i)

        return parts

    @classmethod
    def load(cls, filename, root=None):
        """ Function to load a file and return the collection object. """
        coll = Collection(root)

        tree = ET.parse(filename)
        root_xml_node = tree.getroot()
        if not root_xml_node.tag == 'collection':
            return None

        coll.autoroot = root_xml_node.get("root", ".").replace("/", os.sep)
        if root is None:
            coll.root = os.path.normpath(os.path.join(
                os.path.dirname(filename),
                coll.autoroot
            ))

        # Load the root node
        coll.rootnode = RootDirectory.load(coll, root_xml_node)

        return coll

    def save(self, filename):
        """ Save the collection to XML. """
        root_xml_node = ET.Element('collection')
        if self.autoroot:
            root_xml_node.set("root", self.autoroot.replace(os.sep, "/"))
        else:
            root_xml_node.set("root", ".")

        self.rootnode.save(root_xml_node)
        tree = ET.ElementTree(root_xml_node)

        # Prettify the output ourselves, similar to some code at stack overflow
        queue = [(0, root_xml_node)]
        while queue:
            (level, element) = queue.pop(0)
            children = [(level + 1, child) for child in list(element)]
            if children:
                # Child open
                element.text = "\n" + " " * (level + 1)
            if queue and queue[0][0] == level:
                # sibling open
                element.tail = "\n" + " " * queue[0][0]
            else:
                # no siblings at same level, parent close
                element.tail = "\n" + " " * (level - 1)

            queue[0:0] = children

        # We don't need to use codecs here as ElementTree actually does the
        # encoding based on the enconding= parameter, unlike xml.dom.minidom
        tree.write(filename, encoding='utf-8', xml_declaration=True,
                   method='xml')

# {{{1 Actions

class Action(object):
    """ A base action. """

    ACTION_NAME = None
    ACTION_DESC = ""

    def __init__(self, program):
        self.program = program
        self.options = program.options
        self.writer = program.writer
        self.verbose = program.verbose

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

    def normalize_path(self, path):
        """ Normalize a path. """
        result = self.program.collection.normalize(path)
        if result is None:
            self.writer.stderr.status(path, "BADPATH")

        return result

    def find_nearest_node(self, path):
        """ Find the node or the nearest parent node.
            Return is (node, remaining_path) """

        path = list(path)
        node = self.program.collection.rootnode

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


class InitAction(Action):
    """ Initialize a collection. """

    ACTION_NAME = "init"
    ACTION_DESC = "Initialize a collection."

    def run(self):
        # This is a special action, collection is not loaded at this point
        # can't use self.program.file or self.program.collection
        coll = Collection(".")
        if self.options.root is not None:
            coll.autoroot = self.options.root

        if os.path.exists(self.options.file):
            self.writer.stderr.status(self.options.file, "EXISTS")
            return False

        self.writer.stdout.status(self.options.file, "INIT")

        # Store the collection and file in the program so it will save it
        self.program.file = self.options.file
        self.program.collection = coll
        coll.dirty = True

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
                self.writer.stdout.status(node.prettypath.rstrip("/") + "/" + i, 'NEW')
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

        self.program.collection.dirty = True
        return True

    def handle_symlink(self, node):
        target = os.readlink(node.path)
        if target != node.target:
            node.target = target
            self.writer.stdout.status(node.prettypath, "SYMLINK")

    def handle_file(self, node):
        stat = os.stat(node.path)

        if (self.options.force or
                abs(node.timestamp - stat.st_mtime) > TIMEDIFF or
                node.size != stat.st_size or node.checksum == ""):

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
        else:
            self.writer.stdout.status(nodepath, "MOVE", node)

        self.program.collection.dirty = True
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
        else:
            self.writer.stdout.status(nodepath, "RENAME", node)

        self.program.collection.dirty = True
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
        else:
            self.writer.stdout.status(nodepath, "DELETE")

        self.program.collection.dirty = True
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

        self.program.collection.dirty = True
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
    # TODO: need option to control where files are generated.

    ACTION_NAME = "export"
    ACTION_DESC = "Export information"

    def run(self):
        md5file = os.path.join(self.program.collection.root, "md5sums.txt")
        infofile = os.path.join(self.program.collection.root, "info.txt")

        md5stream = TextFile(md5file)
        infostream = TextFile(infofile)

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
            # skip the "/" at the beginning
            streams[0].writeln(node.checksum + ' *' + node.prettypath[1:])
        else:
            self.writer.stdout.status(node.prettypath, "MISSING CHECKSUM")

        if node.meta:
            self._dumpmeta(node, streams)

    def _dumpmeta(self, node, streams):
        """ Dump the metadata that we know about to the information file. """
        provides = []
        depends = []
        tags = set()
        descriptions = []

        for meta in node.getmeta():
            type = meta.get("type")
            if not type:
                continue

            if type == "provides":
                provides.append((
                    meta.get("name"),
                    meta.get("version")
                ))
            elif type == "dpeends":
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

        descriptions = "\n".join(descriptions)
        if descriptions:
            import textwrap
            lines = textwrap.wrap(descriptions, 75)
            streams[1].writeln("Description:\n  {0}".format(
                "\n  ".join(lines)
            ))


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
            meta.autoname = set(splitval(config["autoname"]))

        # provides
        if "provides" in config:
            provides = splitval(config["provides"])
            for i in provides:
                parts = i.split(":")
                name = parts[0]
                version = parts[1] if len(parts) > 1 and len(parts[1]) else ""
                meta.meta.add(frozenset((
                    ("type", "provides"),
                    ("name", name),
                    ("version", version)
                )))

        # depends
        if "depends" in config:
            depends = splitval(config["depends"])
            for i in depends:
                parts = i.split(":")
                name = parts[0]
                minversion = parts[1] if len(parts) > 1 and len(parts[1]) else ""
                maxversion = parts[2] if len(parts) > 2 and len(parts[2]) else ""
                meta.meta.add(frozenset((
                    ("type", "depends"),
                    ("name", name),
                    ("minversion", minversion),
                    ("maxversion", maxversion)
                )))


        # tags
        if "tags" in config:
            tags = splitval(config["tags"])
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
            ignores = splitval(config["ignore"])
            for ignore in ignores:
                meta.meta.add(frozenset((
                    ("type", "ignore"),
                    ("pattern", ignore)
                )))

        return meta

    def apply_version(self, version):
        """ Apply a version to the autonames if specified. """
        if not self.autoname:
            return

        result = set()
        for name in self.autoname:
            result.add(frozenset((
                ("type", "provides"),
                ("name", name),
                ("version", version)
            )))

        return result


class UpdateMetaAction(Action):
    """ Update the metadata information into the XML. """

    ACTION_NAME = "updatemeta"
    ACTION_DESC = "Update metadata from fcmeta.ini files into the XML."

    def __init__(self, *args, **kwargs):
        Action.__init__(self, *args, **kwargs)
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
                if isinstance(child, Directory):
                    # if directory is named fcmeta.ini, all INI files under
                    # are loaded recursively
                    if not self.loadmeta(child, True):
                        status = False
                else:
                    # Just load the INI file
                    if not self._loadmeta(child):
                        status = False

            elif isinstance(child, Directory):
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
        if isinstance(node, Directory):
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
                if isinstance(child, Directory):
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
                parts = []
                for part in pattern.split("/"):
                    if part == ".":
                        parts.append(True) # Special flag to indicate the "."
                    else:
                        parts.append(fnmatch.translate(part).replace(
                            "FILEVERSION",
                            "(?P<version>[0-9\\.]+)"
                        ))
                regex = [re.compile(part) if part is not True else True for part in parts]

                # Recursively apply meta using regex list
                self._applymeta_walk(parent, regex, meta)

        return status

    def _applymeta_walk(self, node, regex, meta, _version=None):
        """ Apply the metadata to the matching nodes. """

        if len(regex) == 0:
            return

        # Check if the meta applies to this directory
        if len(regex) == 1 and regex[0] is True:
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

                elif len(regex) > 1 and isinstance(child, Directory):
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


class CheckMetaAction(Action):
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


        if isinstance(node, Directory):
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
        node = self.find_node(self.program.collection.normalize(os.curdir))
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
        node = self.find_node(self.program.collection.normalize(os.curdir))
        if node is None:
            self.writer.stderr.status(self.program.cwd, "BADPATH")
            return False

        return self._handle_node(node)

    def _handle_node(self, node):
        status = False

        alldescs = " ".join(
            meta.get("description", "").lower()
            for meta in node.getmeta("description")
        )
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

class VerboseChecker(object):
    """ A small class whose boolean value depends on verbose or a signal. """

    def __init__(self, verbose):
        self._verbose = verbose
        self._signalled = False

        try:
            import signal
            signal.signal(signal.SIGUSR1, self._signal)
        except ImportError:
            pass

    def _signal(self, sig, stack):
        # pylint: disable=unused-argument
        self._signalled = True

    def __bool__(self):
        result = self._verbose or self._signalled
        self._signalled = False
        return result

    __nonzero__ = __bool__


class Program(object):
    """ The main program object. """

    def __init__(self):
        """ Initialize the program object. """
        self.collection = None
        self.cwd = None
        self.file = None # The actual file loaded (options.file is the file to search for)
        self.options = None
        self.verbose = None
        self.writer = None


    def create_arg_parser(self):
        """ Create parser for main and actions """
        parser = argparse.ArgumentParser()

        # Base arguments
        parser.add_argument("-C", "--chdir", dest="chdir", default=None)
        parser.add_argument("-f", "--file", dest="file", default="fcman.xml")
        parser.add_argument("-r", "--root", dest="root", default=None)
        parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true")
        parser.add_argument("-w", "--walk", dest="walk", default=False, action="store_true")
        parser.add_argument("-x", "--no-recurse", dest="recurse", default=True, action="store_false")
        parser.add_argument("-b", "--backup", dest="backup", type=int, default=5, choices=range(0, 10))
        parser.set_defaults(action=None)

        # Add commands
        subparsers = parser.add_subparsers()

        commands = list(filter(lambda cls: cls.ACTION_NAME is not None, Action.get_subclasses()))
        commands.sort(key=lambda cls: cls.ACTION_NAME)

        for i in commands:
            subparser = subparsers.add_parser(i.ACTION_NAME, help=i.ACTION_DESC)
            i.add_arguments(subparser)
            subparser.set_defaults(action=i)

        return parser

    def main(self):
        """ Run the program. """
        # Arguments
        parser = self.create_arg_parser()
        self.options = options = parser.parse_args()

        # Handle some objects
        self.verbose = verbose = VerboseChecker(options.verbose)
        self.writer = writer = StdStreamWriter()

        # Handle current directory
        if options.chdir:
            if verbose:
                writer.stdout.status(options.chdir, "CHDIR")
            os.chdir(options.chdir)

        self.cwd = os.getcwd()

        # Handle action
        action = options.action
        if action is None:
            parser.print_help()
            parser.exit()

        if action.ACTION_NAME != "init":
            # Load the collection if needed
            self.file = self.find_file()
            action.parse_arguments(options)

            if not self.file:
                writer.stderr.status("Collection not found", "NOFILE")
                return -1
            elif verbose:
                writer.stdout.status(self.file, "COLLECTION")

            self.collection = Collection.load(self.file, self.options.root)
            if verbose:
                writer.stdout.status(self.collection.root, "ROOT")

        if not action(self).run():
            return -1

        if self.collection and self.collection.dirty:
            self.save_backup()
            self.collection.save(self.file)

        return 0

    def save_backup(self):
        """ Save a backup based on the filename if requested. """
        filename = self.file
        backup = self.options.backup
        if backup == 0:
            return

        backup_concat = tuple(".{0}bak".format(i) for i in range(1, backup + 1))

        if os.path.exists(filename):
            # Remove last backup if it exists
            if os.path.exists(filename + backup_concat[-1]):
                os.remove(filename + backup_concat[-1])

            for i in range(len(backup_concat) - 2, -1, -1):
                if os.path.exists(filename + backup_concat[i]):
                    os.rename(
                        filename + backup_concat[i],
                        filename + backup_concat[i + 1]
                    )

            os.rename(filename, filename + backup_concat[0])


    def find_file(self):
        """ Use our options to find file. """
        if not self.options.walk:
            # In this mode, file directly specified
            filename = os.path.normpath(self.options.file)
            if os.path.isfile(filename):
                return filename
            return None

        # In walk mode, walk up the directory to find the file
        head = self.cwd
        while head:
            filename = os.path.join(head, self.options.file)
            if os.path.isfile(filename):
                return os.path.relpath(filename) # relpath to keep it pretty

            (head, tail) = os.path.split(head)
            if not tail:
                break

        return None


def main():
    sys.exit(Program().main())