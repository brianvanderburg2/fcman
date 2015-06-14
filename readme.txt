File Collection Manager
=======================

This is a small script to maintain collections of files.  It keeps track of
all the files, directories, and symbolic links, as well as tracks timestamps,
sizes, and checksums for files.


Usage:

    fcman [-v] <action>

Flags:

    -v      Show verbose information

Actions:

    create     Create the collection.xml file in the current directory
    check      Check for any new, missing, or differing files, sizes,
               timestamps, and links. Does not verify checksums.
    checkdeps  Check that dependencies are satisfied.  See below.
    verify     Perform all the checks and also verify file checksums
    update     Add new items, remove missing items, update links,
               timestamps, sizes, and checksums.
    dump       Dump checksums in an md5sum format


Originally there was a plan to migrate from XML to a database using SQLite3
due to the large amount of memory required for large file sets.  This is no
longer a problem.  Instead of migrating to Sqlite3, the code now uses
cElementTree, which uses much less memory and loads quicker.  In addition
each element is passed a state object while acting, that way they don't all
have to store a copy of the filename, which may take a lot of memory on
large file sets.

Packages and Dependency Support
===============================

It is possible to include dependency information in the collection and check
that dependencies are satisfied.  This is achieved by placing a file named
packages.xml within a directory and then describing within the file any
package that are provided.  This file may be placed in more than one directory.
Note that the file must be added to the collection via "fcman update" before
it will be used via "fcman checkdeps"

    <packages>

        <!--
            You may have more than one package in the file.
        -->
        <item name="displayname">
            <!--
                Describe what package names and versions the item provides.
            -->
            <package name="file" />
            <package name="libfile" version="1.0" />

            <!--
                Describe any dependencies of this package.
            -->
            <depends name="glib" />
            <depends name="libother" min="1.0" />
            <depends name="libnext" min="1.0" max="1.99" />
        </item>

    </packages>
