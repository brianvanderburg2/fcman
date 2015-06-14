#!/usr/bin/env python

import sys
import os

import time
import hashlib

try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET


version = "20150614-1"

# Utility functions and stuff
################################################################################

def listdir(path):
    # Make os.listdir return unicode names by passing it a unicode path
    if isinstance(path, bytes):
        path = path.decode(sys.getfilesystemencoding())
    return os.listdir(path)

_case_sensitive = ('abcDEF' == os.path.normcase('abcDEF'))
def realname(path):
    """ Return true if the name is the real name, else return false. """

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

class Logger(object):
    """ Show logging information """
    _signaled = False
    @classmethod
    def handler(cls, signum, frame):
        Logger._signaled = True

    def __init__(self, verbose):
        self._verbose = verbose

    def output(self, msg):
        sys.stdout.write(msg + '\n')
        sys.stdout.flush()

    def status(self, path, status):
        sys.stdout.write(status + ': ' + path + '\n')
        sys.stdout.flush()

    def verbose(self, path, status):
        if Logger._signaled or self._verbose:
            Logger._signaled = False
            sys.stderr.write(status + ': ' + path + '\n')
            sys.stderr.flush()

try:
    import signal
    signal.signal(signal.SIGUSR1, Logger.handler)
except ImportError:
    pass

# Collection classes
################################################################################
class State(object):
    def __init__(self, path, prettypath=None):
        self._path = path
        self._prettypath = prettypath if prettypath else '.'

    def clone(self, name):
        return State(self._path + os.sep + name, self._prettypath + '/' + name)

    @property
    def path(self):
        return self._path

    @property
    def prettypath(self):
        return self._prettypath if self._prettypath else '.'
        


class Node(object):
    """ A node represents a file, symlink, or directory in the collection. """

    def __init__(self, parent, name):
        """ Initialize the collection with the name, parent, and collection """
        self._name = name

        if not parent is None:
            parent._children[name] = self
        else:
            assert(isinstance(self, Collection))

    # Load and save
    @staticmethod
    def load(parent, xml):
        raise NotImplementedError

    def save(self, xml):
        raise NotImplementedError

    # Check and verify
    def check(self, state, log, full=False):
        raise NotImplementedError

    def update(self, state, log):
        raise NotImplementedError
    
    def exists(self, state):
        raise NotImplementedError

    def dumpchecksum(self, state, log):
        raise NotImplementedError

class Symlink(Node):
    """ A symbolic link node. """
    def __init__(self, parent, name, target):
        Node.__init__(self, parent, name)
        self._target = target

    @staticmethod
    def load(parent, xml):
        name = xml.get('name')
        target = xml.get('target')

        return Symlink(parent, name, target)

    def save(self, xml):
        child = ET.SubElement(xml, 'symlink')
        child.set('name', self._name)
        child.set('target', self._target)

        return child

    def check(self, state, log, full=False):
        target = os.readlink(state.path)
        if target != self._target:
            log.status(state.prettypath, 'SYMLINK')
            return False

        return True

    def update(self, state, log):
        target = os.readlink(state.path)
        if(target != self._target):
            self._target = target
            log.status(state.prettypath, 'SYMLINK')

    def exists(self, state):
        return os.path.islink(state.path) and realname(state.path)

    def dumpchecksum(self, state, log):
        log.verbose(state.prettypath, 'PROCESSING')

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
        name = xml.get('name')
        size = xml.get('size')
        timestamp = xml.get('timestamp')
        checksum = xml.get('checksum')

        return File(parent, name, int(size), int(timestamp), checksum)

    def save(self, xml):
        child = ET.SubElement(xml, 'file')
        child.set('name', self._name)
        child.set('size', str(self._size))
        child.set('timestamp', str(self._timestamp))
        child.set('checksum', self._checksum)

        return child

    def check(self, state, log, full=False):
        status = True
        stat = os.stat(state.path)

        if abs(self._timestamp - stat.st_mtime) > self.TIMEDIFF:
            status = False
            log.status(state.prettypath, 'TIMESTAMP')

        if self._size != stat.st_size:
            status = False
            log.status(state.prettypath, 'SIZE')

        if full:
            log.verbose(state.prettypath, 'PROCESSING')
            if self._checksum != checksum(state.path):
                status = False
                log.status(state.prettypath, 'CHECKSUM')

        return status

    def update(self, state, log):
        stat = os.stat(state.path)

        if abs(self._timestamp - stat.st_mtime) > self.TIMEDIFF or self._size != stat.st_size or self._checksum == "":
            log.verbose(state.prettypath, 'PROCESSING')
            self._checksum = checksum(state.path)
            self._timestamp = int(stat.st_mtime)
            self._size = stat.st_size
            log.status(state.prettypath, 'CHECKSUM')

    def exists(self, state):
        return os.path.isfile(state.path) and not os.path.islink(state.path) and realname(state.path)

    def dumpchecksum(self, state, log):
        if self._checksum:
            log.output(self._checksum + ' *' + state.prettypath[1:]) # Remove leading '/'
        else:
            log.verbose(self.prettypath, 'MISSING CHECKSUM')
    
class Directory(Node):
    """ A directory node """

    def __init__(self, parent, name):
        Node.__init__(self, parent, name)
        self._children = {}

    @staticmethod
    def load(parent, xml):
        name = xml.get('name')
        dir = Directory(parent, name)

        for child in xml:
            if child.tag == 'symlink':
                Symlink.load(dir, child)
            elif child.tag == 'directory':
                Directory.load(dir, child)
            elif child.tag == 'file':
                File.load(dir, child)

        return dir

    def save(self, xml):
        child = ET.SubElement(xml, 'directory')
        child.set('name', self._name)

        for name in sorted(self._children):
            self._children[name].save(child)

        return child

    def ignore(self, name):
        return False

    def check(self, state, log, full=False):
        log.verbose(state.prettypath, 'PROCESSING')
        status = True

        # Check for missing
        for i in sorted(self._children):
            newstate = state.clone(i)
            if not self._children[i].exists(newstate):
                log.status(newstate.prettypath , 'MISSING')
                status = False

        # Check for new items
        for i in sorted(listdir(state.path)):
            newstate = state.clone(i)
            if not self.ignore(i) and not i in self._children:
                log.status(newstate.prettypath, 'NEW')
                status = False

                # Show new child items
                path = state.path + os.sep + i
                if os.path.isdir(path) and not os.path.islink(path):
                    item = Directory(self, i)
                    item.check(newstate, log, False) # New directory, no need to calc checksums
                    del self._children[i]

        # Check children
        for i in sorted(self._children):
            newstate = state.clone(i)
            if self._children[i].exists(newstate):
                if self._children[i].check(newstate, log, full) == False:
                    status = False

        return status

    def update(self, state, log):
        log.verbose(state.prettypath, 'PROCESSING')

        # Check for missing items
        for i in sorted(self._children):
            newstate = state.clone(i)
            if not self._children[i].exists(newstate):
                item = self._children[i]
                del self._children[i]
                log.status(newstate.prettypath, 'DELETED')

        # Add new items
        for i in sorted(listdir(state.path)):
            newstate = state.clone(i)
            if not self.ignore(i) and not i in self._children:
                path = newstate.path

                if os.path.islink(path):
                    item = Symlink(self, i, "")
                elif os.path.isfile(path):
                    item = File(self, i, 0, 0, "")
                elif os.path.isdir(path):
                    item = Directory(self, i)
                else:
                    continue # Unsupported item type, will be reported missing with check

                log.status(newstate.prettypath, 'ADDED')

        # Update all item including newly added items
        for i in sorted(self._children):
            newstate = state.clone(i)
            self._children[i].update(newstate, log)

    def exists(self, state):
        return os.path.isdir(state.path) and not os.path.islink(state.path) and realname(state.path)

    def dumpchecksum(self, state, log):
        if not isinstance(self, Collection):
            log.verbose(state.prettypath, 'PROCESSING')
        for i in sorted(self._children):
            newstate = state.clone(i)
            self._children[i].dumpchecksum(newstate, log)


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
        tree = ET.parse(coll._filename)

        root = tree.getroot()
        if root.tag != 'collection':
            return None

        for child in root:
            if child.tag == 'symlink':
                Symlink.load(coll, child)
            elif child.tag == 'directory':
                Directory.load(coll, child)
            elif child.tag == 'file':
                File.load(coll, child)

        return coll

    def save(self):
        root = ET.Element('collection')

        for name in sorted(self._children):
            self._children[name].save(root)

        tree = ET.ElementTree(root)
        if os.path.exists(self._filename):
            if os.path.exists(self._backup):
                os.unlink(self._backup)
            os.rename(self._filename, self._backup)

        # We don't need to use codecs here as ElementTree actually does the
        # encoding based on the enconding= parameter, unlike xml.dom.minidom
        tree.write(self._filename, encoding='utf-8', xml_declaration=True)

    def checkdeps(self, state, log):
        checker = DependencyChecker()
        return checker.check(self, state, log)


# Package/dependency classes
################################################################################
class Package(object):
    """ This represents a named/versioned package. """

    def __init__(self, name, version=None):
        """ Initialize the package. """
        self._name = name
        self._version = version

    def satisfies(self, depends):
        """ Determine if a package satisfies a dependency. """

        # Name must match
        if depends._name != self._name:
            return False

        if depends._min is not None or depends._max is not None:

            # If any dependency version is set, package version must be set to match
            if self._version is None:
                return False

            if depends._min is not None and self._compare(self._version, depends._min) < 0:
                return False

            if depends._max is not None and self._compare(self._version, depends._max) > 0:
                return False

        # If we got here, everything matched
        return True

    def _compare(self, us, them):
        """ Compare two version numbers. """
        # Split
        us = map(int, us.split('.'))
        them = map(int, them.split('.'))

        # Make the same length
        diff = len(us) - len(them)
        if diff > 0:
            them.extend([0] * diff)
        elif diff < 0:
            us.extend([0] * -diff)

        # compare
        return cmp(us, them)


class Dependency(object):
    """ This represents a dependency. """

    def __init__(self, prettypath, item, name, min=None, max=None):
        """ Initialize the package. """
        self._prettypath = prettypath
        self._item = item
        self._name = name
        self._min = min
        self._max = max

    def __str__(self):
        """ Compute a string. """
        s = self._name

        if self._min is not None or self._max is not None:
            s += ' ('

            if self._min is not None:
                s += '>=' + self._min
                if self._max is not None:
                    s += ', '

            if self._max is not None:
                s += '<=' + self._max

            s += ')'

        return s

    def satisfied(self, packages):
        """ Determine if this dependency is satisfied by any available package. """
        if self._name in packages:
            for p in packages[self._name]:
                if p.satisfies(self):
                    return True

        return False


class DependencyChecker(object):
    """ Dependency checker """

    def __init__(self):
        """ Initialize the dependency checker. """
        self._packages = {}
        self._dependencies = []

    def _load(self, node, state, log):
        """ Load information from the node. """
        status = True
        for i in sorted(node._children):
            newstate = state.clone(i)
            newnode = node._children[i]

            if isinstance(newnode, File) and newnode._name == 'packages.xml' and newnode.exists(newstate):
                if not self._loadFile(newstate, log):
                    status = False
            elif isinstance(newnode, Directory):
                if not self._load(newnode, newstate, log):
                    status = False

        return status

    def _loadFile(self, state, log):
        """ Load package information from a file. """
        log.verbose(state.prettypath, "LOADING")

        # Parse file and get root
        try:
            tree = ET.parse(state.path)
        except ET.ParseError as e:
            log.status(state.prettypath, 'LOAD ERROR')
            log.output(str(e))
            return False

        root = tree.getroot()
        if root.tag != 'packages':
            log.status(state.prettypath, 'LOAD ERROR')
            return False

        # Load all items
        for i in root.findall('item'):
            self._loadItem(i, state, log)

        # Loaded successfully
        return True

    def _loadItem(self, item, state, log):
        """ Load item specific information from the package. """

        name = item.get('name', '')

        # Packages
        for p in item.findall('package'):
            pname = p.get('name', '')
            pversion = p.get('version')

            if not pname in self._packages:
                self._packages[pname] = []

            self._packages[pname].append(Package(pname, pversion))

        # Dependencies
        for d in item.findall('depends'):
            dname = d.get('name', '')
            dmin = d.get('min')
            dmax = d.get('max')

            self._dependencies.append(Dependency(state.prettypath, name, dname, dmin, dmax))

    def check(self, coll, state, log):
        """ Check the dependencies. """
        status = True

        # Load the information
        if not self._load(coll, state, log):
            status = False

        # Still try to check what we have loaded
        last = None
        for i in self._dependencies:
            if not i.satisfied(self._packages):
                status = False
                if not last == i._prettypath:
                    log.status(i._prettypath, 'DEPENDS')
                    last = i._prettypath
                log.output(i._item + ": " + str(i))

        return status

# Program entry point
################################################################################
def usage():
    print('Usage: ' + sys.argv[0] + ' [-v] <action>')
    print('')
    print('  -v:        Verbose status messages')
    print('  action:    create, check, checkdeps, verify, update, dump')
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

    if not action in ('create', 'check', 'checkdeps', 'verify', 'update', 'dump'):
        usage()
        sys.exit(-1)

    # Do stuff
    root = os.getcwd()
    state = State(root)
    log = Logger(verbose)

    if action == 'create':
        coll = Collection.new(root)
        coll.save()
    elif action == 'check':
        coll = Collection.load(root)
        if not coll.check(state, log):
            sys.exit(-1)
    elif action == 'checkdeps':
        coll = Collection.load(root)
        if not coll.checkdeps(state, log):
            sys.exit(-1)
    elif action == 'verify':
        coll = Collection.load(root)
        if not coll.check(state, log, True):
            sys.exit(-1)
    elif action == 'update':
        coll = Collection.load(root)
        coll.update(state, log)
        coll.save()
    elif action == 'dump':
        coll = Collection.load(root)
        coll.dumpchecksum(state, log)

if __name__ == '__main__':
    main()
