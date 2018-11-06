#!/usr/bin/env python
# vim: foldmethod=marker foldmarker={{{,}}}, foldlevel=0

# TODO:
# Error messages should only go to stderr
# Informational messages should only be printed to stdout if verbose
# Status messages for actions and outputs should be printed to stdout
# stderror should be though of as program error:
    # If we can't load the xml files or badly formatted, that is program error (go to stderr)
    # If a file is missing during a check, that is utility error (go to stdout)
# All string constants should be unicode
# When reading from text files convert to unicode (read file as UTF-8)
    # ini parser use readfp/readfile with codecs.open
    # Ensure lxml reads in unicode
# when reading file system (listdir), return unicode names
# when checking file system, convert unicode to file system encoding
# when writing to files, convert unicode to utf-8
# when writing to stdout/stderr, convert unicode to correct encoding

# {{{1 Meta information

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"
__version__ = "0.2.20181105.1"


# {{{1 Imports and such

import argparse
import codecs
try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser
import fnmatch
import glob
import hashlib
import io
import os
import re
import sys
import time

try:
    from lxml import etree as ET
except ImportError:
    try:
        from xml.etree import cElementTree as ET
    except ImportError:
        from xml.etree import ElementTree as ET

# {{{1 Compatibility stuff

# TODO: need better unicode handling so all loaded strings are in unicode
# (alternative, just make this python3 only, still will need some work)
try:
    u = unicode
except NameError:
    def u(s):
        if isinstance(s, bytes):
            return str(s.decode())
        else:
            return str(s)


# {{{1 Utility functions and stuff
################################################################################

# Global values
TIMEDIFF = 2

# Use namespaces
NS_COLLECTION = "{urn:mrbavii.fcman:collection}"

ET.register_namespace('c', NS_COLLECTION[1:-1])

def listdir(path):
    """ List a directory, make sure returned names are unicode by passing a unicode path. """
    # This was needed as was causing errors in some cases when joining names
    if isinstance(path, bytes):
        path = path.decode(sys.getfilesystemencoding())
    return os.listdir(path)

_case_sensitive = ('abcDEF' == os.path.normcase('abcDEF'))
def realname(path):
    """ Return true if the name is the real name, else return false. """
    # A real name means the OS represents the filename in the same case
    # as stored in the file.  

    if _case_sensitive:
        return True

    # On case insensitive systems, we want to make sure the name matches
    # what the OS tells us it would be from a directory listing.
    dir = os.path.dirname(path)
    name = os.path.basename(path)

    return name in listdir(dir)

def checksum(path):
    """ Calculate the checksum and return the result. """
    hasher = hashlib.md5()

    with open(path, 'rb') as handle:
        data = handle.read(4096000)
        while len(data):
            hasher.update(data)
            data = handle.read(4096000)

    return hasher.hexdigest()

class StreamWriter(object):
    """ Write to a given stream. """

    class _indent_ctx_mgr(object):
        def __init__(self, writer):
            self._writer = writer

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            self._writer.dedent()

    def __init__(self, stream, filename=None, indent="    "):
        """ Initialze the writer. """
        self._stream = stream
        self._indent = 0
        self._indentText = indent

    def indent(self):
        self._indent += 1
        return self._indent_ctx_mgr(self)

    def dedent(self):
        self._indent -= 1

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._stream.close()
        self._stream = None

    def writeln(self, line):
        self._stream.write(u(self._indent * self._indentText))
        self._stream.write(u(line))
        self._stream.write(u("\n"))

class LogWriter(StreamWriter):

    def __init__(self, *args, **kwargs):
        StreamWriter.__init__(self, *args, **kwargs)
        self._last = None

    def status(self, path, status, msg=None):
        check = (path, status)
        if check != self._last:
            self._last = check
            self.writeln(status + ":" + path)

        if msg:
            with self.indent():
                self.writeln("> " + msg)

class Writer(object):
    """ This class will replace logger and provide some better. """

    def __init__(self, redirect=None):

        # Perform proper encoding for the output.
        # On Python 2, stdout/stderr are 8 bit interfaces.  On Python3
        # they expect unicode data and will convert, and can also take binary
        # data.  So we really only need to handle converting on Python 2
        if sys.version[0] == '2':
            enc = sys.stdout.encoding
            if enc is None:
                enc = 'utf8'
            stdout = codecs.getwriter(enc)(sys.stdout)

            enc = sys.stderr.encoding
            if enc is None:
                enc = 'utf8'
            stderr = codecs.getwriter(enc)(sys.stderr)
        else:
            stdout = sys.stdout
            stderr = sys.stderr

        self.stdout = LogWriter(stdout)
        self.stderr = LogWriter(stderr)

    def open(self, filename):
        handle = io.open(filename, "wt", encoding="utf-8", newline="\n")
        return StreamWriter(handle, filename)
        

# {{{1 Collection classes
################################################################################

class Node(object):
    """ A node represents a file, symlink, or directory in the collection. """

    def __init__(self, parent, name):
        """ Initialize the collection with the name, parent, and collection """
        self._name = name
        self._parent = parent
        self._meta = []

        # If this is RootDirectory, self._collection is set it it's __init__
        # before calling parent __init__, otherwise we set it from parent

        if parent is not None:
            parent._children[name] = self
            self._collection = parent._collection
            self._path = parent._path + (name,)
        else:
            assert(isinstance(self, RootDirectory))
            self._path = ()


    @property
    def pathlist(self):
        return self._path

    @property
    def path(self):
        return os.path.join(
            self._collection._root,
            *self._path
        )

    @property
    def prettypath(self):
        if self._path:
            return "./" + "/".join(self._path)
        else:
            return "."

    # Load and save
    @classmethod
    def load(cls, parent, xml):
        raise NotImplementedError

    def save(self, xml):
        raise NotImplementedError

    def exists(self):
        raise NotImplementedError


class Symlink(Node):
    """ A symbolic link node. """

    def __init__(self, parent, name, target):
        Node.__init__(self, parent, name)
        self._target = target

    @classmethod
    def load(cls, parent, xml):
        name = xml.get('name')
        target = xml.get('target')

        return Symlink(parent, name, target)

    def save(self, xml):
        xml.set('name', self._name)
        xml.set('target', self._target)

    def exists(self):
        return os.path.islink(self.path) and realname(self.path)


class File(Node):
    """ A file node """

    def __init__(self, parent, name, size, timestamp, checksum):
        Node.__init__(self, parent, name)

        self._size = size
        self._timestamp = timestamp
        self._checksum = checksum

    @classmethod
    def load(cls, parent, xml):
        name = xml.get('name')
        size = xml.get('size', -1)
        timestamp = xml.get('timestamp', -1)
        checksum = xml.get('checksum')

        return File(parent, name, int(size), int(timestamp), checksum)

    def save(self, xml):
        xml.set('name', self._name)
        xml.set('size', str(self._size))
        xml.set('timestamp', str(self._timestamp))
        xml.set('checksum', self._checksum)

    def exists(self):
        return os.path.isfile(self.path) and not os.path.islink(self.path) and realname(self.path)


class Directory(Node):
    """ A directory node """

    def __init__(self, parent, name):
        Node.__init__(self, parent, name)
        self._children = {}

    @classmethod
    def load(cls, parent, xml):
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
        if not isinstance(self, RootDirectory):
            xml.set('name', self._name)

        for name in sorted(self._children):
            child = self._children[name]
            
            if isinstance(child, Symlink):
                tag = 'symlink'
            elif isinstance(child, File):
                tag = 'file'
            elif isinstance(child, Directory):
                tag = 'directory'
            else:
                pass

            element = ET.SubElement(xml, NS_COLLECTION + tag)
            child.save(element)

    def ignore(self, name):
        if isinstance(self._parent, RootDirectory) and self._name == "_collection":
            if name.lower() in ("collection.xml", "backups", "export"):
                return True
        return False

    def exists(self):
        return os.path.isdir(self.path) and not os.path.islink(self.path) and realname(self.path)


class RootDirectory(Directory):
    """ The root directory. """

    def __init__(self, collection):
        """ Initialize the root directory. """
        self._collection = collection
        Directory.__init__(self, None, None)

    def ignore(self, name):
        """ Ignore specific files in the root directory. """
        if name.lower() in ("md5sum",):
            return True

        return Directory.ignore(self, name)


class Collection(object):
    """ This is the collection object. """

    def __init__(self, root, writer, verbose):
        """ Initialize the collection with the root of the collection. """

        self._root = root
        self._writer = writer
        self._verbose = verbose
        self._rootdir = RootDirectory(self)
        self._allmeta = []
        self._filename = os.path.join(root, '_collection', 'collection.xml')
        self._fallbackname = os.path.join(root, 'collection.xml')
        self._backupname = os.path.join(root, '_collection', 'backups', 'collection.xml.' + time.strftime("%Y%m%d%H%M%S"))
        self._exportdir = os.path.join(root, '_collection', 'export')

    @classmethod
    def load(cls, root, writer, verbose):
        """ Function to load a file and return the collection object. """
        coll = Collection(root, writer, verbose)

        if os.path.isfile(coll._filename):
            filename = coll._filename
        else:
            filename = coll._fallbackname

        tree = ET.parse(filename)
        root = tree.getroot()
        if not root.tag in ('collection', NS_COLLECTION + 'collection'):
            return None

        # Load the rootdir
        coll._rootdir = RootDirectory.load(coll, root)

        return coll
    
    def save(self):
        root = ET.Element(NS_COLLECTION + 'collection')
        self._rootdir.save(root)

        tree = ET.ElementTree(root)

        for i in (os.path.dirname(j) for j in (self._backupname, self._filename)):
            if not os.path.isdir(i):
                os.makedirs(i)

        # Move old filename over
        if os.path.exists(self._fallbackname):
            if os.path.exists(self._backupname):
                os.unlink(self._backupname)
            os.rename(self._fallbackname, self._backupname)

        # Move new filename over
        if os.path.exists(self._filename):
            if os.path.exists(self._backupname):
                os.unlink(self._backupname)
            os.rename(self._filename, self._backupname)

        # We don't need to use codecs here as ElementTree actually does the
        # encoding based on the enconding= parameter, unlike xml.dom.minidom
        tree.write(self._filename, encoding='utf-8', xml_declaration=True,
                   method='xml', pretty_print=True)


    def loadmeta(self):
        """ Walk over each directory for a "fcmanmeta.xml" file """

        status = True

        # First we load all the meta files
        node = self._rootdir
        if not self._loadmeta_walk(node):
            status = False

        return status

    def _loadmeta_walk(self, node):
        status = True
        for i in sorted(node._children):
            child = node._children[i]

            if i == "fcmeta.ini":
                if not self._loadmeta(child):
                    status = False

            elif isinstance(child, Directory):
                self._loadmeta_walk(child)

        return status

    def _loadmeta(self, node):
        if self._verbose:
            self._writer.stdout.status(node.prettypath, 'LOADING')

        config = SafeConfigParser()
        read = config.read(node.prettypath)
        if not read:
            self._writer.stderr.status(node.prettypath, 'LOAD ERROR', str(e))
            return False

        # Should at least have fcmeta section
        if not config.has_section("fcman:fcmeta"):
            self._writer.stderr.status(node.prettypath, 'NOTMETAINFO')
            return False

        sections = config.sections()
        for name in sections:
            if name == "fcman:fcmeta":
                continue

            meta = MetaInfo.load(node, name, dict(config.items(name)))
            self._allmeta.append(meta)

    def applymeta(self):
        """ Walk over all loaded meta information and match the globs
            to the nodes. """

        status = True

        for meta in self._allmeta:
            node = meta._node
            pattern = meta.pattern
            parent = node._parent

            if pattern == ".":
                parent._meta.append(meta)
                meta._users.append(parent)
                continue

            if pattern[0:2] == "r:":
                pattern = pattern[2:].replace("(@)", "(?P<version>[0-9\.]+)")
                regex = re.compile(pattern)
                def matchfn(name):
                    result = regex.match(name)
                    if result:
                        try:
                            version = result.group("version")
                        except IndexError:
                            version = None
                        return (True, version)
                    else:
                        return (False, None)
            else:
                def matchfn(name):
                    return (fnmatch.fnmatchcase(name, pattern), None)

            for name in sorted(parent._children):
                (matched, version) = matchfn(name)
                if matched:
                    child = parent._children[name]
                    meta._users.append(child)

                    newmeta = meta.clone()
                    child._meta.append(newmeta)

                    if meta.autoname:
                        for autoname in meta.autoname:
                            newmeta.provides.append((autoname, version))


class MetaInfo(object):
    
    def __init__(self, node):
        self._node = node
        self._users = []


    @classmethod
    def load(cls, node, pattern, config):

        meta = MetaInfo(node)

        def stripchars(s):
            return ''.join(filter(lambda ch: ch not in " \t\r\n", s))

        # pattern
        meta.pattern = pattern
        meta.autoname = []
        if "autoname" in config:
            meta.autoname = stripchars(config["autoname"]).split(",")

        # provides
        meta.provides = []
        if "provides" in config:
            provides = stripchars(config["provides"]).split(",")
            for i in provides:
                parts = i.split(":")
                meta.provides.append((
                    parts[0],
                    parts[1] if len(parts) > 1 and len(parts[1]) else None
                ))

        # depends
        meta.depends = []
        if "depends" in config:
            depends = stripchars(config["depends"]).split(",")
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
            meta.tags = stripchars(config["tags"]).split(",")

        # description
        meta.description = None
        if "description" in config:
            desc = config["description"].strip()
            desc = " ".join([line.strip() for line in desc.splitlines() if len(line)])
            meta.description = desc


        return meta
    
    def clone(self):
        """ Make a copy of the meta but with no users. """
        m = MetaInfo(self._node)
        m.pattern = self.pattern
        m.autoname = list(self.autoname)
        m.provides = list(self.provides)
        m.depends = list(self.depends)
        m.tags = list(self.tags)
        m.description = self.description

        return m


    def dump(self):
        print(self.pattern)
        for i in self.autoname:
            print(i)
        for i in self.provides:
            print(i)
        for i in self.depends:
            print(i)
        for i in self.tags:
            print(i)
        print(self.description)

# Actions
################################################################################

class Action(object):
    """ A base action. """

    ACTION_NAME = None
    ACTION_DESC = ""
    
    def __init__(self, root, options, writer, verbose):
        self._root = root
        self._options = options
        self._writer = writer
        self._verbose = verbose

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

    ACTION_NAME="create"
    ACTION_DESC="Create a collection"
    
    def run(self):
        coll = Collection(self._root, self._writer, self._verbose)
        coll.save()
        return True

class CheckAction(Action):
    """ Check the collection. """

    ACTION_NAME="check"
    ACTION_DESC="Perform quick collection check"

    def run(self):
        coll = Collection.load(self._root, self._writer, self._verbose)
        self._fullcheck = False
        return self.handle_directory(coll._rootdir)

    def _missing_dir(self, node):
        for i in sorted(node._children):
            newnode = node._children[i]

            self._writer.stdout.status(newnode.prettypath, 'MISSING')
            if isinstance(newnode, Directory):
                self._missing_dir(newnode)

    def handle_symlink(self, node):
        target = os.readlink(node.path)
        if target != node._target:
            self._writer.stdout.status(node.prettypath, 'SYMLINK')
            return False

        return True

    def handle_file(self, node):
        status = True
        stat = os.stat(node.path)

        if abs(node._timestamp - stat.st_mtime) > TIMEDIFF:
            status = False
            self._writer.stdout.status(node.prettypath, 'TIMESTAMP')

        if node._size != stat.st_size:
            status = False
            self._writer.stdout.status(node.prettypath, 'SIZE')

        if self._fullcheck:
            if self._verbose:
                self._writer.stdout.status(node.prettypath, 'PROCESSING')
            if node._checksum != checksum(node.path):
                status = False
                self._writer.stdout.status(node.prettypath, 'CHECKSUM')

        return status

    def handle_directory(self, node):
        if self._verbose:
            self._writer.stdout.status(node.prettypath, 'PROCESSING')
        status = True

        # Check for missing
        for i in sorted(node._children):
            newnode = node._children[i]

            if node.ignore(i):
                self._writer.stdout.status(newnode.prettypath, 'SHOULDIGNORE')
            if not newnode.exists():
                self._writer.stdout.status(newnode.prettypath , 'MISSING')
                status = False

                # Report all subitems
                if isinstance(newnode, Directory):
                    self._missing_dir(newnode)


        # Check for new items
        for i in sorted(listdir(node.path)):
            if not node.ignore(i) and not i in node._children:
                self._writer.stdout.status(node.prettypath + "/" + i, 'NEW')
                status = False

                # Show new child items
                path = node.path + os.sep + i
                if os.path.isdir(path) and not os.path.islink(path):
                    newnode = Directory(node, i)
                    
                    orig = self._fullcheck
                    self._fullcheck = False
                    self.handle_directory(newnode)
                    self._fullcheck = orig

                    del node._children[i]

        # Check children
        for i in sorted(node._children):
            child = node._children[i]
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

    ACTION_NAME="verify"
    ACTION_DESC="Perform full checksum verification"

    def run(self):
        coll = Collection.load(self._root, self._writer, self._verbose)
        self._fullcheck = True
        return self.handle_directory(coll._rootdir)


class UpdateAction(Action):
    """ Update the collection. """

    ACTION_NAME="update"
    ACTION_DESC="Update the collection"

    def run(self):
        coll = Collection.load(self._root, self._writer, self._verbose)
        self.handle_directory(coll._rootdir)
        coll.save()
        return True

    def handle_symlink(self, node):
        target = os.readlink(node.path)
        if target != node._target:
            node._target = target
            self._writer.stdout.status(node.prettypath, "SYMLINK")

    def handle_file(self, node):
        stat = os.stat(node.path)

        if abs(node._timestamp - stat.st_mtime) > TIMEDIFF or node._size != stat.st_size or node._checksum == "":
            if self._verbose:
                self._writer.stdout.status(node.prettypath, 'PROCESSING')
            node._checksum = checksum(node.path)
            node._timestamp = int(stat.st_mtime)
            node._size = stat.st_size
            self._writer.stdout.status(node.prettypath, 'CHECKSUM')

    def handle_directory(self, node):
        if self._verbose:
            self._writer.stdout.status(node.prettypath, 'PROCESSING')

        # Check for missing items
        for i in sorted(node._children):
            child = node._children[i]
            if node.ignore(i):
                del node._children[i]
                self._writer.stdout.status(child.prettypath, 'IGNORED')
            elif not child.exists():
                del node._children[i]
                self._writer.stdout.status(child.prettypath, 'DELETED')

        # Add new items
        for i in sorted(listdir(node.path)):
            if not node.ignore(i) and not i in node._children:
                path = node.path + os.sep + i

                if os.path.islink(path):
                    item = Symlink(node, i, "")
                elif os.path.isfile(path):
                    item = File(node, i, 0, 0, "")
                elif os.path.isdir(path):
                    item = Directory(node, i)
                else:
                    continue # Unsupported item type, will be reported missing with check

                self._writer.stdout.status(item.prettypath, 'ADDED')

        # Update all item including newly added items
        for i in sorted(node._children):
            child = node._children[i]
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

    ACTION_NAME="export"
    ACTION_DESC="Export information"

    def run(self):
        coll = Collection.load(self._root, self._writer, self._verbose)
        coll.loadmeta()
        coll.applymeta()

        md5file = os.path.join(coll._exportdir, "md5sums.txt")
        infofile = os.path.join(coll._exportdir, "info.txt")

        md5stream = self._writer.open(md5file)
        infostream = self._writer.open(infofile)

        streams = (md5stream, infostream)

        with md5stream:
            with infostream:
                self._handle_directory(coll._rootdir, streams)

    def _handle_directory(self, node, streams):
        streams[1].writeln("Directory: {0}".format(node.prettypath))

        if node._meta:
            self._dumpmeta(node, streams)

        for child in sorted(node._children):
            streams[1].writeln("")
            childnode = node._children[child]
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
        streams[1].writeln("Target: {0}".format(node._target))

        if node._meta:
            self._dumpmeta(node, streams)

    def _handle_file(self, node, streams):
        streams[1].writeln("File: {0}".format(node.prettypath))
        streams[1].writeln("Size: {0}".format(node._size))
        streams[1].writeln("MD5: {0}".format(node._checksum))
        streams[1].writeln("Modified: {0}".format(node._timestamp))

        if node._checksum:
            streams[0].writeln(node._checksum + ' *' + node.prettypath[2:])
        else:
            self._writer.stdout.status(node.prettypath, "MISSING CHECKSUM")

        if node._meta:
            self._dumpmeta(node, streams)

    def _dumpmeta(self, node, streams):
        provides = [provided for meta in node._meta for provided in meta.provides]
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

        depends = [depended for meta in node._meta for depended in meta.depends]
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

        tags = set(tag for meta in node._meta for tag in meta.tags)
        if tags:
            streams[1].writeln("Tags: {0}".format(
                ", ".join(sorted(tags))
            ))

        descriptions = "\n".join(meta.description for meta in node._meta if meta.description)
        if descriptions:
            import textwrap
            lines = textwrap.wrap(descriptions, 75) 
            streams[1].writeln("Description:\n  {0}".format(
                "\n  ".join(lines)
            ))


class CheckMetaAction(Action):
    """ Check the metadata (dependencies/etc). """

    ACTION_NAME="checkmeta"
    ACTION_DESC="Check metadata, dependencies, etc"

    def run(self):
        coll = Collection.load(self._root, self._writer, self._verbose)
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
        self._checkdeps_walk_collect(coll._rootdir, packages)

        # Next check all dependencies from the nodes have a package to satisfy
        return self._checkdeps_walk(coll._rootdir, packages)

    def _checkdeps_walk_collect(self, node, packages):
        for meta in node._meta:
            for (name, version) in meta.provides:
                if not name in packages:
                    packages[name] = set()
                packages[name].add(version)

        if isinstance(node, Directory):
            for child in sorted(node._children):
                self._checkdeps_walk_collect(node._children[child], packages)
                
    def _checkdeps_walk(self, node, packages):
        status = True

        if node._meta:
            for meta in node._meta:
                for depends in meta.depends:
                    if not self._checkdeps_find(depends, packages):
                        status = False
                        self._writer.stdout.status(node.prettypath, "DEPENDS", str(depends))

        if isinstance(node, Directory):
            for child in sorted(node._children):
                if not self._checkdeps_walk(node._children[child], packages):
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

    def _checkdeps_compare(self, v1, v2):
        """ A simple version compare based only on numbers and periods. """

        try:
            v1 = list(map(lambda v: int(v), v1.split(".")))
            v2 = list(map(lambda v: int(v), v2.split(".")))
        except ValueError:
            return False

        # pad to the same length
        if len(v1) < len(v2):
            v1.extend([0] * (len(v2) - len(v1)))
        elif len(v2) < len(v1):
            v2.extend([0] * (len(v1) - len(v2)))

        # per element compare
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0

    def _checkmeta_used(self, coll):
        for meta in coll._allmeta:
            if not meta._users:
                self._writer.stdout.status(meta._node.prettypath, "UNUSEDMETA", meta.pattern)


# Program entry point
################################################################################

def create_arg_parser():
    parser = argparse.ArgumentParser()

    # Base arguments
    parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true")

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
    action.parse_arguments(options)

    verbose = VerboseChecker(options.verbose)
    writer = Writer()


    # Do stuff
    root = os.getcwd()

    if not action(root, options, writer, verbose).run():
        return -1

if __name__ == '__main__':
    sys.exit(main())

