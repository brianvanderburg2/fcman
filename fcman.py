#!/usr/bin/env python
# vim: foldmethod=marker foldmarker={{{,}}}, foldlevel=0

# TODO:
# Error messages should only go to stderr
# Informational messages should only be printed to stdout if verbose
# Status messages for actions and outputs should be printed to stdout
# stderror should be though of as program error:
    # If we can't load the xml files or badly formatted, that is program error (go to stderr)
    # If a file is missing during a check, that is utility error (go to stdout)

# {{{1 Meta information

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"
__version__ = "0.2.20181105.1"


# {{{1 Imports and such

import argparse
import codecs
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


# {{{1 Utility functions and stuff
################################################################################

# Global values
TIMEDIFF = 2

# Use namespaces
NS_COLLECTION = "{urn:mrbavii.fcman:collection}"
NS_METAINFO =   "{urn:mrbavii.fcman:metainfo}"

ET.register_namespace('c', NS_COLLECTION[1:-1])
ET.register_namespace('m', NS_METAINFO[1:-1])

def checkattr(xml, attr, prettypath):
    """ Check that only the specified attributes are present on an xml node. """
    if not isinstance(attr, (tuple, list)):
        attr = (attr,)

    for i in xml.keys():
        if not i in attr:
            line = getattr(xml, 'sourceline', None)
            Logger.status(prettypath, 'XML', 'Unknown attribute: "' + i + ('" line: ' + str(line) if line else '"'), stderr=True)

def checkchild(xml, children, prettypath):
    """ Check that only the specified child nodes are present on an xml node. """
    if not isinstance(children, (tuple, list)):
        children = (children,)

    for i in list(xml):
        # Make sure it has a tag, not a comment or processing instruction
        if not isinstance(i.tag, str):
            continue

        if not i.tag in children:
            line = getattr(i, 'sourceline', None)
            Logger.status(prettypath, 'XML', 'Unknown element: "' + str(i.tag) + ('" line: ' + str(line) if line else '"'), stderr=True)

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

    def __init__(self, stream, filename=None):
        """ Initialze the writer. """
        self._stream = stream
        self._indent = 0
        self._indentText = "    "

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
        self._stream.write(self._indent * self._indentText)
        self._stream.write(line)
        self._stream.write("\n")

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
        

# Collection classes
################################################################################

class Node(object):
    """ A node represents a file, symlink, or directory in the collection. """

    def __init__(self, parent, name):
        """ Initialize the collection with the name, parent, and collection """
        self._name = name
        self._parent = parent
        self._mata = []

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
        name = xml.get('name')

        # If parent is a collection object, then we are a RootDirectory
        # and parent is actually None
        if isinstance(parent, Collection):
            dir = RootDirectory(parent)
        else:
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

    def __init__(self, root):
        """ Initialize the collection with the root of the collection. """

        self._root = root
        self._rootdir = RootDirectory(self)
        self._meta = []
        self._filename = os.path.join(root, '_collection', 'collection.xml')
        self._fallbackname = os.path.join(root, 'collection.xml')
        self._backup = os.path.join(root, '_collection', 'backups', 'collection.xml.' + time.strftime("%Y%m%d%H%M%S"))

    @classmethod
    def load(cls, root):
        """ Function to load a file and return the collection object. """
        coll = Collection(root)

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

        for i in (os.path.dirname(j) for j in (self._backup, self._filename)):
            if not os.path.isdir(i):
                os.makedirs(i)

        # Move old filename over
        if os.path.exists(self._fallbackname):
            if os.path.exists(self._backup):
                os.unlink(self._backup)
            os.rename(self._fallbackname, self._backup)

        # Move new filename over
        if os.path.exists(self._filename):
            if os.path.exists(self._backup):
                os.unlink(self._backup)
            os.rename(self._filename, self._backup)

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

            if i == "fcmanmeta.xml":
                if not self._loadmeta(child):
                    status = False

            elif isinstance(child, Directory):
                self._loadmeta_walk(child)

        return status

    def _loadmeta(self, node):
        Logger.verbose(node.prettypath, 'LOADING')
        try:
            tree = ET.parse(node.path)
        except (IOError, ET.ParseError) as e:
            Logger.status(node.prettypath, 'LOAD ERROR', str(e), stderr=True)
            return False

        root = tree.getroot()
        if not root.tag in ('metainfo', NS_METAINFO + 'metainfo'):
            Logger.status(node.prettypath, 'NOTMETAINFO', stderr=True)
            return False

        # Load the items
        print("Items")
        checkchild(root, NS_METAINFO + 'item', node.prettypath)
        for i in root.findall(NS_METAINFO + 'item'):
            self._meta.append(MetaInfo.load(node, i))


#    def check(self, a, b):
#        node = self._rootdir
#        self.loadmeta()
#        self._check(node)

#    def _check(self, node):
#        for i in sorted(node._children):
#            child = node._children[i]
#            print(child.prettypath)
#            if isinstance(child, Directory):
#                self._check(child)
            


class MetaInfo(object):
    
    def __init__(self, node):
        self._node = node
        self._users = []


    @classmethod
    def load(cls, node, xml):

        meta = MetaInfo(node)

        checkchild(xml, [NS_METAINFO + i for i in ('glob', 'package', 'depends', 'description', 'todo')], node.prettypath)
        checkattr(xml, 'name', node.prettypath)

        meta.name = xml.get("name", "")

        # Globs
        meta._globs = []
        for c in xml.findall(NS_METAINFO + "glob"):
            checkattr(c, ("path", "autoname", "autoversion"), node.prettypath)

            glob = c.get("path")
            autoname = c.get("autoname", None)
            autoversion = c.get("autoversion", None)

            if autoname:
                autoname = autoname.split(":")

            meta._globs.append( (glob, autoname, autoversion) )

        # Packages
        meta._packages = []
        for p in xml.findall(NS_METAINFO + "package"):
            checkattr(p, ("name", "version"), node.prettypath)
            name = p.get("name", "").split(":")
            version = p.get("version")
            for part in name:
                meta._packages.append((part, version))

        # Depends
        meta._depends = []
        for d in xml.findall(NS_METAINFO + "depends"):
            checkattr(d, ("name", "min", "max"), node.prettypath)
            name = d.get("name").split(":")
            minver = d.get("min")
            maxver = d.get("max")
            for part in name:
                meta._depends.append((part, minver, maxver))

        # Descriptions

        meta._description = xml.get("description")
        meta._todo = xml.get("todo")



        return meta

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
    
    def run(self):
        coll = Collection(self._root)
        coll.save()
        return True

class CheckAction(Action):
    """ Check the collection. """

    ACTION_NAME = "check"
    ACTION_DESC = "Perform quick collection check"

    def run(self):
        coll = Collection.load(self._root)
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
        coll = Collection.load(self._root)
        self._fullcheck = True
        return self.handle_directory(coll._rootdir)


class UpdateAction(Action):
    """ Update the collection. """

    ACTION_NAME="update"
    ACTION_DESC="Update the collection"

    def run(self):
        coll = Collection.load(self._root)
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

