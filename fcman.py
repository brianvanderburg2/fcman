#!/usr/bin/env python

import sys
import os

import codecs
import time
from xml.dom import minidom
import hashlib

# Utility functions and stuff
################################################################################

_case_sensitive = ('abcDEF' == os.path.normcase('abcDEF'))
def realname(path):
    """ Return true if the name is the real name, else return false. """

    if _case_sensitive:
        return True

    # On case insensitive systems, we want to make sure the name matches
    # what the OS tells us it would be from a directory listing.
    dir = os.path.dirname(path)
    name = os.path.basename(path)

    return name in os.listdir(dir)

def checksum(path):
    """ Calculate the checksum and return the result. """
    hasher = hashlib.md5()

    with open(path, 'rb') as handle:
        data = handle.read(4096000)
        while len(data):
            hasher.update(data)
            data = handle.read(4096000)

    return hasher.hexdigest()

class Logger(object):
    """ Show logging information """

    def __init__(self, verbose):
        self._verbose = verbose

    def output(self, msg):
        sys.stdout.write(msg + '\n')
        sys.stdout.flush()

    def message(self, msg):
        sys.stderr.write(msg + '\n');
        sys.stderr.flush()
    
    def status(self, path, status):
        self.message(status + ': ' + path)

    def verbose(self, msg, status):
        if self._verbose:
            self.status(msg, status)


# Collection classes
################################################################################
class Node(object):
    """ A node represents a file, symlink, or directory in the collection. """

    def __init__(self, parent, name):
        """ Initialize the collection with the name, parent, and collection """
        self._parent = parent
        self._name = name

        if not parent is None:
            self._collection = parent._collection
            self._path = parent._path + os.sep + name
            parent._children[name] = self
        else:
            assert(isinstance(self, Collection))
            self._collection = self
            self._path = name

    # Load and save
    @staticmethod
    def load(parent, xml):
        raise NotImplementedError

    def save(self, xml):
        raise NotImplementedError

    # Check and verify
    def check(self, log, full=False):
        raise NotImplementedError

    def update(self, log):
        raise NotImplementedError
    
    def exists(self):
        raise NotImplementedError

    def dumpchecksum(self, log):
        raise NotImplementedError

    @property
    def prettypath(self):
        return self._path[len(self._collection._path):]


class Symlink(Node):
    """ A symbolic link node. """
    # TODO: track the linked target

    def __init__(self, parent, name, target):
        Node.__init__(self, parent, name)
        self._target = target

    @staticmethod
    def load(parent, xml):
        name = xml.getAttribute('name')
        target = xml.getAttribute('target')

        return Symlink(parent, name, target)

    def save(self, xml):
        doc = xml.ownerDocument

        child = doc.createElement('symlink')
        child.setAttribute('name', self._name)
        child.setAttribute('target', self._target)

        xml.appendChild(child)
        return child

    def check(self, log, full=False):
        target = os.readlink(self._path)
        if target != self._target:
            log.status(self.prettypath, 'SYMLINK')
            return False

        return True

    def update(self, log):
        target = os.readlink(self._path)
        if(target != self._target):
            self._target = target
            log.status(self.prettypath, 'SYMLINK')

    def exists(self):
        return os.path.islink(self._path) and realname(self._path)

    def dumpchecksums(self, log):
        pass

class File(Node):
    """ A file node """
    TIMEDIFF = 2

    def __init__(self, parent, name, size, timestamp, checksum):
        Node.__init__(self, parent, name)

        self._size = size
        self._timestamp = timestamp
        self._checksum = checksum

    @staticmethod
    def load(parent, xml):
        name = xml.getAttribute('name')
        size = xml.getAttribute('size')
        timestamp = xml.getAttribute('timestamp')
        checksum = xml.getAttribute('checksum')

        return File(parent, name, int(size), int(timestamp), checksum)

    def save(self, xml):
        doc = xml.ownerDocument

        child = doc.createElement('file')
        child.setAttribute('name', self._name)
        child.setAttribute('size', str(self._size))
        child.setAttribute('timestamp', str(self._timestamp))
        child.setAttribute('checksum', self._checksum)

        xml.appendChild(child)
        return child

    def check(self, log, full=False):
        status = True
        stat = os.stat(self._path)

        if abs(self._timestamp - stat.st_mtime) > self.TIMEDIFF:
            status = False
            log.status(self.prettypath, 'TIMESTAMP')

        if self._size != stat.st_size:
            status = False
            log.status(self.prettypath, 'SIZE')

        if full:
            log.verbose(self.prettypath, 'CALCULATING')
            if self._checksum != checksum(self._path):
                status = False
                log.message(self.prettypath, 'CHECKSUM')

        return status

    def update(self, log):
        stat = os.stat(self._path)

        if abs(self._timestamp - stat.st_mtime) > self.TIMEDIFF or self._size != stat.st_size or self._checksum == "":
            log.verbose(self.prettypath, 'CALCULATING')
            self._checksum = checksum(self._path)
            self._timestamp = int(stat.st_mtime)
            self._size = stat.st_size
            log.status(self.prettypath, 'CHECKSUM')

    def exists(self):
        return os.path.isfile(self._path) and not os.path.islink(self._path) and realname(self._path)

    def dumpchecksum(self, log):
        if self._checksum:
            log.output(self._checksum + ' *' + self.prettypath.lstrip(os.sep).replace(os.sep, '/'))
    
class Directory(Node):
    """ A directory node """

    def __init__(self, parent, name):
        Node.__init__(self, parent, name)
        self._children = {}

    @staticmethod
    def load(parent, xml):
        name = xml.getAttribute('name')
        dir = Directory(parent, name)

        for child in xml.childNodes:
            if child.nodeType != child.ELEMENT_NODE:
                continue;
            
            if child.nodeName == 'symlink':
                Symlink.load(dir, child)
            elif child.nodeName == 'directory':
                Directory.load(dir, child)
            elif child.nodeName == 'file':
                File.load(dir, child)

        return dir

    def save(self, xml):
        doc = xml.ownerDocument

        child = doc.createElement('directory')
        child.setAttribute('name', self._name)

        for name in sorted(self._children):
            self._children[name].save(child)

        xml.appendChild(child)

    def ignore(self, name):
        return False

    def check(self, log, full=False):
        log.verbose(self.prettypath, 'PROCESSING')
        status = True

        # Check for missing
        for i in sorted(self._children):
            if not self._children[i].exists():
                log.status(self._children[i].prettypath, 'MISSING')
                status = False

        # Check for new items
        for i in sorted(os.listdir(self._path)):
            if not self.ignore(i) and not i in self._children:
                log.status(self.prettypath + os.sep + i, 'NEW')
                status = False

                # Show new child items
                path = self._path + os.sep + i
                if os.path.isdir(path) and not os.path.islink(path):
                    item = Directory(self, i)
                    item.check(log, False) # New directory, no need to calc checksums
                    del self._children[i]

        # Check children
        for i in sorted(self._children):
            if self._children[i].exists():
                if self._children[i].check(log, full) == False:
                    status = False

        return status

    def update(self, log):
        log.verbose(self.prettypath, 'PROCESSING')

        # Check for missing items
        for i in sorted(self._children):
            if not self._children[i].exists():
                item = self._children[i]
                del self._children[i]
                log.status(item.prettypath, 'DELETED')

        # Add new items
        for i in sorted(os.listdir(self._path)):
            if not self.ignore(i) and not i in self._children:
                path = self._path + os.sep + i

                if os.path.islink(path):
                    item = Symlink(self, i, "")
                elif os.path.isfile(path):
                    item = File(self, i, 0, 0, "")
                elif os.path.isdir(path):
                    item = Directory(self, i)
                else:
                    continue # Unsupported item type, will be reported missing with check

                log.status(item.prettypath, 'ADDED')

        # Update all item including newly added items
        for i in sorted(self._children):
            self._children[i].update(log)

    def exists(self):
        return os.path.isdir(self._path) and not os.path.islink(self._path) and realname(self._path)

    def dumpchecksum(self, log):
        for i in sorted(self._children):
            self._children[i].dumpchecksum(log)


class Collection(Directory):
    """ This is the collection object. """

    def __init__(self, root):
        """ Initialize the collection with the root of the collection. """
        Directory.__init__(self, None, root)

        self._filename = os.path.join(root, 'collection.xml')
        self._backup = os.path.join(root, 'collection.xml.' + time.strftime("%Y%m%d%H%M%S"))
    
    def ignore(self, name):
        if name.startswith('collection.xml'):
            return True

        if name.lower().startswith('md5sum'):
            return True

        return False

    @staticmethod
    def new(root):
        coll = Collection(root)
        return coll

    @staticmethod
    def load(root):
        """ Function to load a file and return the collection object. """
        coll = Collection(root)
        dom = minidom.parse(coll._filename)

        root = dom.documentElement
        if root.nodeName != 'collection':
            return None

        for child in root.childNodes:
            if child.nodeType != child.ELEMENT_NODE:
                continue

            if child.nodeName == 'symlink':
                Symlink.load(coll, child)
            elif child.nodeName == 'directory':
                Directory.load(coll, child)
            elif child.nodeName == 'file':
                File.load(coll, child)

        return coll

    def save(self):
        doc = minidom.Document()
        root = doc.createElement('collection')

        for name in sorted(self._children):
            self._children[name].save(root)

        doc.appendChild(root)

        if os.path.exists(self._filename):
            if os.path.exists(self._backup):
                os.unlink(self._backup)
            os.rename(self._filename, self._backup)

        with codecs.open(self._filename, 'w', encoding='utf-8') as handle:
            doc.writexml(handle, '', '  ', '\n', 'utf-8')

# Program entry point
################################################################################
def usage():
    print('Usage: ' + sys.argv[0] + ' [-v] <action>')
    print('')
    print('  -v:        Verbose status messages')
    print('  action:    create, check, verify, update, dump')
    print('')

def main():
    # Check arguments
    if len(sys.argv) < 2:
        usage()
        sys.exit(-1)

    if sys.argv[1] == '-v':
        if len(sys.argv) != 3:
            usage()
            sys.exit(-1)

        verbose = True
        action = sys.argv[2]
    else:
        verbose = False
        action = sys.argv[1]

    if not action in ('create', 'check', 'verify', 'update', 'dump'):
        usage()
        sys.exit(-1)

    # Do stuff
    root = os.getcwd()
    log = Logger(verbose)

    if action == 'create':
        coll = Collection.new(root)
        coll.save()
    elif action == 'check':
        coll = Collection.load(root)
        if not coll.check(log):
            sys.exit(-1)
    elif action == 'verify':
        coll = Collection.load(root)
        if not coll.check(log, True):
            sys.exit(-1)
    elif action == 'update':
        coll = Collection.load(root)
        coll.update(log)
        coll.save()
    elif action == 'dump':
        coll = Collection.load(root)
        coll.dumpchecksum(log)

if __name__ == '__main__':
    main()

