File Collection Manager
=======================

This is a small script to maintain collections of files.  It keeps track of
all the files, directories, and symbolic links, as well as tracks timestamps,
sizes, and checksums for files.


Usage:

    fcman [-v] <action>

Flags:

    -v      Show verbose information
    -h      Show help

Actions:

    create     Create the collection data in the _collection subdirectory
    check      Check for any new, missing, or differing files, sizes,
               timestamps, and links. Does not verify checksums.
    verify     Same as check, but also verify checksums
    update     Add new items, remove missing items, update links, timestamps,
               sizes, and checksums.
    checkmeta  Check the status of the metadata including dependencies and
               report any unused metadata sections.
    export     Export md5sums and information to _collection/export
    upgrade    Upgrade collections from the older version by moving the file
               from collection.xml to _collection/collection.xml

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
name= or name: syntax

[fcman.fcmeta]
; This section must exist for the file to be considered a metadata file

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
; segment will be used to determine the file version.

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

