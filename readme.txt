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
It is also possible to create a directory named packages.xml and any XML
files in that directory and subdirectories will be read as packages as well.
Note that the file must be added to the collection via "fcman update" before
it will be used via "fcman checkdeps"

Note that the checkdeps command only checks dependencies.  It does not check
that the "packages.xml" files exists.  If a packages file is in the collection
but missing from disc, it is silently skipped. Use the check command to make
sure all files in the collection are present.  Also, if a packages file is
not an fcman packages file, by missing the namespace, it is ignored and a
message is printed.  This does not cause an error status code.  This is to
ensure that if fcman is used on a documents folder with some documents
that may be named packages.xml by some chance, it doesn't treat those as
errors.

    <packages xmlns="urn:mrbavii.fcman:packages">

        <!--
            You may have more than one package in the file. Also, a check
            value can be used to check if something exists relative to the
            location of the packages.xml file.  This uses Python glob.glob
        -->
        <item name="displayname">
            <!--
                Provide a check for the existence of a file or directory.
                Multiple check elements may be specified.  An autoname and
                autoversion attribute can be used to automatically generate
                packages from the checked item.  The autoname attribute is
                a plain name, or multiple names separated by colons.  The
                autoversion attribute is a regular expression which will be
                searched against each item returned by the glob.  If the search
                succeeds, then a special group used as "(@)" will be used
                to extract the version numbers.  "(@)" is replaced with
                "(?P<version>[0-9\.]+)" for the regular expression.  The
                search method is used, so it is not anchored to the beginning
                or ending of the complete path unless the regular expression
                causes it to be so.
            -->
            <check path="displayname-app*.exe" autoname="package:package2"
             autoversion="displayname-app(@).tar.*$"/>
            <check path="displayname-data*.exe />

            <!--
                Describe what package names and versions the item provides.
                Multiple package names can be defined in a single element by
                separating the names with a colon.  All such names will use
                the same version information, if specified.
            -->
            <package name="file" />
            <package name="libfile" version="1.0" />
            <package name="foo:bar" /> <!-- Proviles "foo" and "bar" -->

            <!--
                Describe any dependencies of this package.  Multiple dependency
                names can be defined in a single element by separating the names
                with a color.  All such names will use the same min and max
                version information, if specified.
            -->
            <depends name="glib" />
            <depends name="libother" min="1.0" />
            <depends name="libnext" min="1.0" max="1.99" />
            <depends name="libsdl:libsdl-image:libsdl-mixer" />
        </item>

    </packages>

