File Collection Manager
=======================

This is a small script to maintain collections of files.  It keeps track of
all the files, directories, and symbolic links, as well as tracks timestamps,
sizes, and checksums for files.


Usage:

    fcman [global option] <action> [action option]

Global options:

    -h, --help
        Show help

    -C <DIR>, --chdir <DIR>
        Change to the specified directory before processing

    -f <FILE>, --file <FILE>
        Specify the file to use for the collection data.  The "init" action
        this is the path of the file created.  For other actions this is the
        file to load. If the walk option is specified, this is the file to
        search for while walking up the directory tree.

    -r <ROOT>, --root <ROOT>
        Specify the root of the directory.  If this is not specified, the root
        is determined from the file's root attribute.  If that is also not
        specified, then the root directory is the directory that contains the
        file.  During "init", this specifies the literal value to store in the
        "root" attribute of the data file.

    -v, --verbose
        Show verbose information.  Without this option, a one-time verbose
        status can be triggered by sending the USR1 signal to the program.

    -w, --walk
        Walk up the directory tree from the current location to find the data
        file.  Some actions will then treat the current directory as the path
        to use when performing actions

    -x, --no-recurse
        For various actions, do not recurse into the subdirectories.

    -b <BACKUPS>, --backup <BACKUPS>
        Create at moset BACKUPS backups of the data file.

Actions:


add
---

Add an item to the collection, optionally with any missing parent directories.

-f, --force
    Always update the checksum even if timestamps and sizes match

-p, --parents
    Create parend directory nodes if possible and needed

<path>
    The path of the item to add, relative to the current directory. The path
    must still be under the collection.  Paths starting with "/" are treated
    relative to the collection root. Defaults to "."


check
-----

Perform a basic check of items on the collection such as new or missing items
and any timestamp or size changes.

<path>
    The path to check. Defaults to "."


checkmeta
---------

Check any metadata and report any inconsistancies (sp?).


delete
------

Delete an item from the collection.

<path>
    The path of the node to delete from the collection.  Defaults to "."


export
------

Export information from the collection to "md5sums.txt" and "info.txt".
Currently these are stored in the root of the collection.


finddesc
--------

Find items with description metadata.

-a, --all
    Only report results which match all descriptions specified.

<path>
    Specify the path to start the scan

<desc>*
    May be specified more than once, specifies the text of the description
    to find.  Case is not important.


findpath
--------

Find items which match certain path data.  This applies to an entries "pretty
path", which is the path of item and all parent items, starting with "/" and
with "/" separating each path component.

-c, --no-case
    Ignore case of the path. This does not apply if the pattern is a regular
    expression instead of a glob pattern.

<path>
    Specify the path to start the scan

<pattern>
    Specifies a pattern to find.  fnmatch.fnmatch is used normally, however if
    pattern starts with "r:", the remaining of the pattern is treated as a
    regular expression.


findtag
-------

Find items with tag metadata.

-a, --all
    Only report results which match all tags specified.

<path>
    Specify the path to start the scan

<tag>*
    May be specified more than once, specifies the tag to find. Case is not
    important.


init
----

Initialze the collection.  The root and file options take a slightly different
meaning here.  The file options specifies the file to be created, and the
root optino if specified is the value to store in the data files root attribute.
File defaults to "fcman.xml" and root defaults to "."


move
----

Move an item to a different parent directory.

<path>
    The path of the item to move

<parent>
    The path of a directory item to move the path to.


rename
------

Rename an item.

<path>
    The path of the item to rename

<newname>
    The new name of the item>


update
------

Update the file, scanning for new or change items and removing ignored or
missing items.

-f, --force
    Force an update of checksums for any existing files even if timestamp and
    size have not changed.

<path>
    The path of the item to update


updatemeta
----------

Updates metadata into the collection data file.


verify
------

Performs the same checks as the check action, in addition verifies file
checksums.

<path>
    The path to verify


Packages and Dependency Support
===============================

It is possible to include dependency information in the collection and check
that dependencies are satisfied.  This is achieved by placing a file named
fcmeta.ini within a directory and then describing within the file any 
package that are provided.  This file may be placed in more than one directory.
Note that the checkmeta command only checks the state of the meta dependencies
based on whether the node is present in the collection, not whether the files
actually exist.

fcmeta.ini Format:
==================

fcmeta.ini uses the Python config parser.  Values can span multiple lines as
long as they are indented on hanging lines, and can be specified with either
name= or name: syntax.  If a directory is named "fcmeta.ini", then any INI
files found in that directory or any directory under it will be treated as a
metadata INI file.  Not that the files are only loaded if they are part of the
collection as it is the collection tree and not the directory tree that is
scanned for the items.

[fcman.fcmeta]
; This section must exist for the file to be considered a metadata file

; If target is specified, it specifies the directory node that any patterns in
; the INI file should apply to.  If relative then it is to the directory that
; contains the INI file.  If it starts with "/" then it is absolute to the
; collection root.
target=/

[name]
; represent a name for a metadata section

pattern=fsglob
; specify a pattern to match items that are children of the current directory
; node.  If pattern is ".", then it will apply to the current directory node
; pattern can be anything matched with fnmatch.fnmatchcase. Internally it is
; split by "/" and then compiled into regular expressions using fnmatch.
; If the pattern "FILEVERSION" is found in a part, it is translated such that
; it will match repeading digits 0-9 and "." and be used as the version of the
; file.   If FILEVERSION is found in more than one segment, only the last
; segment will be used to determine the file version. Multiple patterns can
; be split by a comma.

autoname=name
; Automatically add additional provides items to nodes that match the pattern.
; if the pattern is a regular expression and includes a version group, then
; the portion of the node name that matches the version group will become the
; provides version.  Multiple names can be specified by separating with space,
; newlines, or commas.  The names are not created as additional packages if
; a version was not found.

provides=package
; Specify a package provided by the matched item.  The format is "name" or
; "name:version".  Multiple packages can be specified by separating with space,
; newlines, or commas

depends=package:minversion:maxversion
; Specify a dependency the matched node has as "name", "name:minversion",
; "name::maxversion", or "name:minversion:maxversion". Multiple depdends can
; be specified by separating with space, newlines, or commas

tags=name name name
; Specify a tag for the matched node.  Multiple tags can be specified by
; separatig with space, newlines, or comman

description=
; Specify a description for the matched item
; newlines, or commas



