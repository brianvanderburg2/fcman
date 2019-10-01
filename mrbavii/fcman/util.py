""" Utility classes and functions for mrbavii.fcman """
# pylint: disable=too-few-public-methods,redefined-builtin

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright 2000-2019"
__license__ = "MIT"

__all__ = [
    "TIMEDIFF", "splitval", "StreamWriter", "LogWriter", "TextFile", "StdStreamWriter"
]


import io
import sys

from . import collection


# Time difference to consider a file's timestamp changed
TIMEDIFF = 2


def splitval(val):
    """ Split a string into a list of non-empty values by comma or whitespace. """
    # Convert whitespace to comma
    tmpval = ''.join(
        "," if ch in " \t\n\r" else ch for ch in val
    )
    return list(
        word for word in tmpval.split(",") if len(word)
    )


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
            elif isinstance(path, collection.Node):
                path = path.prettypath
            self.writeln(status + ":" + path)

        if msg is not None:
            if isinstance(msg, collection.Node):
                msg = msg.prettypath
            with self.indent():
                self.writeln("> " + msg)


    def statusline(self, path, status, msg):
        """ Write a status line for a given path/status pair.
            What this does is, if the last path/status doesn't match the
            current, is writes a plain path/status by itself, so that the
            status line appears in the " > " section of the output.
        """

        check = (path, status)
        if check != self._last:
            self.status(path, status)
        self.status(path, status, msg)



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
