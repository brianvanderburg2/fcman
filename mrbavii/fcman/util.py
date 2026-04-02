""" Utility classes and functions for mrbavii.fcman """
# pylint: disable=too-few-public-methods,redefined-builtin

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright 2000-2026"
__license__ = "MIT"

__all__ = [
    "TIMEDIFF", "splitval", "StreamWriter", "LogWriter", "TextFile", "StdStreamWriter",
    "VerboseChecker", "open_xml_compressed"
]


import contextlib
import io
import re
import signal
import sys

from . import collection


# Time difference to consider a file's timestamp changed
TIMEDIFF = 2


def splitval(val):
    """ Split a string into a list of non-empty values by comma or whitespace. """
    return list(re.findall(r"[^,\s\n\r\t]+", val))


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


class VerboseChecker(object):
    """ A small class whose boolean value depends on verbose or a signal. """

    def __init__(self, verbose):
        self._verbose = verbose
        self._signalled = False

        try:
            signal.signal(signal.SIGUSR1, self._signal)
        except ImportError:
            pass

    def _signal(self, sig, stack):
        # pylint: disable=unused-argument
        self._signalled = True

    def __bool__(self):
        result = self._verbose or self._signalled
        self._signalled = False
        return result

    __nonzero__ = __bool__


def open_compressed(filename, mode):
    """ Return a file object fo reading/writting based onextension."""
    assert mode in ("r", "w"), "mode must be 'r' or 'w'"

    fn = filename.lower()
    _opener = None


    if fn.endswith(".gz"):
        import gzip as _opener
    elif fn.endswith(".bz2"):
        import bz2 as _opener
    elif fn.endswith(".xz"):
        import lzma as _opener
    else:
        _opener = io # call io.open

    return _opener.open(filename, "rb" if mode == "r" else "wb")

def files_match(a, b):
    """ Compare two files to see if they match """

    with (
        contextlib.closing(open_compressed(a, "r")) as ha,
        contextlib.closing(open_compressed(b, "r")) as hb
    ):
        while True:
            ba = ha.read(1024000)
            bb = hb.read(1024000)

            if ba != bb:
                return False

            if len(ba) == 0 or len(bb) == 0:
                break

    # If reads ever didn't match it would return false above
    return True

def valid_collection_name(name):
    """ Test that a collection name is valid. """
    return re.match("^[a-zA-Z0-9_]+(-[a-zA-Z0-9_]+)*$", name) is not None
