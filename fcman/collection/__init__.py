""" This file manages the collection object, as well as loading and saving the collection. """

import sys
import os

from xml.dom import minidom


class Error(Exception):
    pass


class Node(object):
    """ A node represents either a file or directory in the collection. """

    def __init__(self, name, parent):
        """ Initialize the name with the name, parent, and collection """
        self._name = name
        self._parent = parent
        if not parent is None:
            self._collection = parent._collection
            parent._children.append(self)
        else:
            assert(isinstance(self, Collection))
            self._collection = self
        self._properties = {}

        self.dirty = True
        self.update()

    # Load and save
    def save(self, node):
        raise NotImplementedError

    def saveProperties(self, node):
        """" Save the properties as children of the specified XML node. """
        doc = node.ownerDocument
        for (key, value) in self._properties.iteritems():
            propNode = doc.createElement('property')
            propNode.setAttribute('name', key)
            propNode.setAttribute('value', value)
            node.appendChild(propNode)

    def loadProperties(self, node):
        """ Load properties from the specified XML node. """
        self._properties = {}
        raise NotImplementedError

    # Update methods
    def update(self):
        """ Update values after adding/moving/renaming """
        if self._parent:
            self._path = self._parent._path + os.sep + self._name
        else:
            self._path = self._name

    # Property methods
    def get(self, prop):
        """ Return the property value, or None """
        return self._properties.get(prop, None)

    def set(self, prop, value):
        """ Set a property value """
        self._properties[prop] = value
    
    # Common properties
    @property
    def collection(self):
        return self._collection

    @property
    def parent(self):
        return self._parent

    @property
    def name(self):
        return self._name

    @property
    def properties(self):
        return self._properties.iteritems()

    @property
    def path(self):
        return self._path

    @property
    def exists(self):
        raise NotImplementedError

    def move(self, parent):
        raise NotImplementedError

    @property
    def canmove(self, parent):
        raise NotImplementedError

    def rename(self, name):
        raise NotImplementedError
    
    @property
    def canrename(self, name):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError
    
    @property
    def candelete(self):
        raise NotImplementedError

class File(Node):
    """ A file node """

    @staticmethod
    def load(self, parent, xml):
        raise NotImplementedError

    def save(self, node):
        doc = node.ownerDocument
        fileNode = doc.createElement('file')

        fileNode.setAttribute('name', self._name)
        self.saveProperties(fileNode)

        node.appendChild(fileNode)

    @property
    def exists(self):
        return os.path.isfile(self._path)
    

class Directory(Node):
    """ A directory node """

    def __init__(self, name, parent):
        Node.__init__(self, name, parent)    
        self._children = []
    
    @staticmethod
    def load(self, parent, xml):
        raise NotImplementedError

    def save(self, node):
        doc = node.ownerDocument
        dirNode = doc.createElement('directory')

        dirNode.setAttribute('name', self._name)
        self.saveProperties(dirNode)

        for child in self._children:
            child.save(dirNode)

        node.appendChild(dirNode)

    def udpate(self):
        Node.update(self)
        for child in self._children:
            child.update()

    @property
    def exists(self):
        return os.path.isdir(self._path)


class Collection(Directory):
    """ This is the collection object. """

    def __init__(self, root):
        """ Initialize the collection with the root of the collection. """
        Directory.__init__(self, root, None)

        self._filename = os.path.join(root, 'collection.xml')
        self._backup = os.path.join(root, 'collection.bak')

    @property
    def filename(self):
        return self._filename

    @property
    def backup(self):
        return self._backup

    @staticmethod
    def load(root):
        """ Function to load a file and return the collection object. """
        coll = Collection(root)
        dom = minidom.parse(coll.filename)

    def save(self):
        doc = minidom.Document()
        rootNode = doc.createElement('collection')

        self.saveProperties(rootNode)

        for child in self._children:
            child.save(rootNode)

        doc.appendChild(rootNode)

        return doc






