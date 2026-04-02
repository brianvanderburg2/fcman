""" Configuration code. """
# pylint: disable=line-too-long,missing-docstring,too-few-public-methods

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright 2000-2026"
__license__ = "MIT"


import os
import toml

from . import collection
from . import consts


class Config:
    """ Represent a configuration file """
        
    def __init__(self, path=None):
        self.toml = {}
        if path:
            self.toml = toml.decoder.load(path)

    def save(self, path):
        with open(path, "wt", encoding="UTF-8") as handle:
            toml.encoder.dump(self.toml, handle)

    def get_table(self, name, create=False):
        """ Return a config table, create an empty one if it doesn't exist. """
        parts = name.split(".")
        last = len(parts) - 1

        table = self.toml
        for (pos, part) in enumerate(parts):
            if part in table:
                table = table[part]
                if not isinstance(table, dict):
                    return None
            elif create:
                table[part] = dict()
                table = table[part]
            else:
                return None

        return table

    def get_value(self, name, default=None):
        """ Return a configuration value. """
        parts = name.rsplit(".", 1)

        table = self.get_table(parts[0])
        if table is None:
            return default

        if len(parts) == 1:
            return table
        else:
            return table.get(parts[1], default)


class NoConfig(Config):

    def __init__(self, program):
        ConfigBase.__init__(program)

        self.toml = {"fcman" : {} }

    def load_collection(self, name):
        if name in self.collections:
            return self.collections[name]

        collections = self.toml.setdefault("collection", {})
        if not name in collections:
            self.writer.stderr.status(name, "NOCOLLECTION")
            return None

        root = collections[name].get("root", None)
        if root is not None:
            root = os.path.join(self.program.topdir, root)

        filename = os.path.join(
            self.program.statedir,
            consts.COLLECTION_DIR,
            name,
            STAGED_FILE
        )

        coll = collection.Collection.load(filename)
        self.collections[name] = coll

        if root:
            coll.set_root(root)

        return coll

    def save_collection(self, name, coll):
        if not name in self.collections:
            self.writer.stderr.status(name, "NOCOLLECTION")
            return False

        filename = os.path.join(
            self.program.statedir,
            consts.COLLECTION_DIR,
            name,
            consts.STAGED_FILE
        )

        self.collections[name].save(filename)
        return True

    def new_collection(self, name, root):
        if name in self.collections:
            self.writer.stderr.status(name, "EXISTS")
            return False

        collections = self.toml.getdefault("collections", {})

        dirname = os.path.join(
            self.program.statedir,
            consts.COLLECTION_DIR,
            name
        )

        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        filename = os.path.join(
            dirname,
            contsts.STAGED_FILE
        )

        coll = collection.Collection()
        coll.set_root(root)
        coll.save(filename)




class CollectionConfig:
    """ Represent the config of a single collection. """

    BACKUP_DIR = "backups"
    SAVE_DIR = "saves"
    EXPORT_DIR = "exports"
    TAG_DIR = "tags"

    def __init__(self, config):
        self.config = config
        self.program = config.program
        self.collection = None

        self.name = None
        self.rootdir = None
        self.statedir = None


