File Collection Manager
-----------------------

This is a small script to maintain collections of files.  It keeps track of
all the files, directories, and symbolic links, as well as tracks timestamps,
sizes, and checksums for files.


Usage:

    fcman [-v] <action>

Flags:

    -v      Show verbose information

Actions:

    create  Create the collection.xml file in the current directory
    check   Check for any new, missing, or differing files, sizes,
            timestamps, and links. Does not verify checksums.
    verify  Perform all the checks and also verify file checksums
    update  Add new items, remove missing items, update links,
            timestamps, sizes, and checksums.
    dump    Dump checksums in an md5sum format


