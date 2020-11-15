""" Base action class. """
# pylint: disable=missing-docstring
__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"

__all__ = ["ActionBase"]


from .. import collection


class ActionBase(object):
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
            if not isinstance(node, collection.Directory):
                break

            for name in node.children:
                if name == path[0]:
                    node = node.children[name]
                    path.pop(0)
                    break # break for
            else:
                break # break while

        # len(path) == 0 means we found the node, else just the nearest parent
        return (node, path)

    def find_node(self, path):
        """ Find the exact node or return None. """
        (node, remaining_path) = self.find_nearest_node(path)
        return node if not remaining_path else None

    def handle_sigint(self):
        """ Handle CTRL-C """
        pass
