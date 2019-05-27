""" Collection classes. """

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"

__all__ = ["Node", "Symlink", "File", "Directory", "RootDirectory", "Collection"]


import os
import fnmatch
import hashlib

try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET


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

    def __init__(self):
        """ Initialize the collection with the root of the collection. """

        self.root = None
        self.rootnode = RootDirectory(self)
        self.autoroot = "."
        self.dirty = False # This flag is set externally by actions to indicate to save

    def set_root(self, root):
        """ Set the root the collection represents. """
        self.root = os.path.normpath(root) if root is not None else None

    def normalize(self, path):
        """ Normalize an external path to be relative to the collection root. """
        if path is None or self.root is None:
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
    def load(cls, filename):
        """ Function to load a file and return the collection object. """
        coll = Collection()

        tree = ET.parse(filename)
        root_xml_node = tree.getroot()
        if not root_xml_node.tag == 'collection':
            return None

        coll.autoroot = root_xml_node.get("root", ".").replace("/", os.sep)

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


