""" Visit action. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2026 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import inspect
import os

from .. import collection
from .. import util
from .base import ActionBase



class _Wrapper:
    """ Wrapper to handle calling the visitor function """

    def __init__(self, func):
        self._func = func

        if inspect.isclass(func):
            self._instance = func()
        else:
            self._instance = None

    def initialize(self, args, program, data):
        if self._instance:
            instance_initialize = getattr(self._instance, "initialize", None)
            if callable(instance_initialize):
                return instance_initialize(args, program, data)
        
        return  True

    def visit(self, node, args, program, data):
        if self._instance:
            return self._instance.visit(node, args, program, data)
        else:
            return self._func(node, args, program, data)

    def finalize(self, args, program, data):
        if self._instance:
            instance_finalize = getattr(self._instance, "finalize", None)
            if callable(instance_finalize):
                return instance_finalize(args, program, data)

        return True


class VisitAction(ActionBase):
    """ Visit each node and execute a script or function. """

    ACTION_NAME = "visit"
    ACTION_DESC = "Visit each node executing a script or function"

    @classmethod
    def add_arguments(cls, parser):
        super(VisitAction, cls).add_arguments(parser)
        parser.add_argument(
            "--code", dest="code", required=True,
            help="filename containing the function to execute"
        )
        parser.add_argument(
            "--func", dest="func", required=True,
             help="function to execute as the vistor function."
        )
        parser.add_argument("args", nargs="*", help="Extra arguments to pass to the vistor function")

    def __init__(self, program):
        super(VisitAction, self).__init__(program)
        self._visitor = None
        self._data = {}

    def run(self):
        if not self._load_code():
            return False

        if not self._visitor.initialize(self.options.args, self.program, self._data):
            return False

        if not self.handle_node(self.program.collection.rootnode):
            return False

        return self._visitor.finalize(self.options.args, self.program, self._data)

    def _load_code(self):
        filename = self.options.code
        function = self.options.func

        if self.verbose:
            self.writer.stdout.status(filename, "LOADCODE", function)

        if os.path.isfile(filename):
            with open(filename, "rU") as handle:
                code = handle.read()
        else:
            self.writer.stderr.status(filename, "NOFILE")
            return False

        obj = compile(code, filename, "exec", dont_inherit=True)
        # TODO: need a better way to display errors

        data = dict()
        data["__file__"] = filename
        
        exec(obj, data, data)

        if function in data:
            self._visitor = _Wrapper(data[function])
        else:
            self.writer.stderr.status(filename, "NOFUNCTION", function)
            return False

        return True

    def handle_node(self, node):
        result = True

        if self.verbose:
            self.writer.stdout.status(node.prettypath, 'PROCESSING')

        if not self._visitor.visit(node, list(self.options.args), self.program, self._data):
            result = False

        if isinstance(node, collection.Directory):
            for i in sorted(node.children):
                child = node.children[i]
                if not self.handle_node(child):
                    result = False

        return result


ACTIONS = [VisitAction]
