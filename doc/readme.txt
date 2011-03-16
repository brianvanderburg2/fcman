FCM - A file collection manager


Introduction
============

FCM is a general purpose collection manager to keep track of files that are
part of a collection.  A data file is placed in the root of a file collection
and for each file it can store some information.  It can also provide simple
dependency checking to make sure for any file all other needed files are
present.


File Format
===========

<?xml version="1.0" encoding="UTF-8" ?>
<collection>
    <contents>
        <dir name="directory">
            <file name="filename" checksum="type:value" size="filesize" dirty="yes|no">
                <package name="name" version="version" />
                <dependency name="name" minversion="minversion" maxversion="maxversion" />
                <description>Description of item</description>
            </file>
        </dir>
    </contents>
</collection>


The interface
=============

The directory list allows you to move, rename, and delete directories in the
collection manager.  You can also right-click on a directory to get a menu of
actions that can be performed on that directory and subdirectories.  The file
list shows the files in the selected directory.  You can rename or delete them,
or move them to another directory.  You can right-click to get a menu of
actions that can be performed on teh selected files.  For both, you can rename
by editing the name in the label, delete by pressing delete, and move by
dragging to the new directory.

An edit panel allows editing information about the selected file, such as the
description of the file, as well as packages and dependencies of the file.  A
log window logs the results of various actions.  It can be cleared in the menu
bar.


Real Mode
=========

In real mode, actions performed on the collection while moving or renamin
gare also performed on the real file system.  Real mode is activated when
the Control key is pressed while performing the action of dropping an item
during a move or pressing enter during a rename.

Actions
=======

NOTE: Actions only affect the data in the collection file and do not make any
changes to the files on disk.

New Directory (Directory list only) - This action creates a new directory in
the collection manager, so that existing items can be moved to into the new
directory and keep any information for those items, especially file information
such as descriptions and dependencies.

Verify Sanity (Directory list only) - This action will perform some checks to
make sure the collection is valid.  It will scan for and log any missing items,
files with mismatched file sizes, new items, duplicate items, and missing
dependencies.  This should be the first action to perform to check that
everything is as it should be.

Add New Items (Directory list only) - This action will scan for any new items
and add them to the collection.  It does not automatically calculate the file
checksums.

Rename Missing Items (Directory list only) - This action will attempt to find
any missing items and see if a rename is possible.  The user will be prompted
for any renames to perform.  This is good when a new version of a file has
been added, such as removing "myfile-0.1.zip" and adding "myfile-0.2.zip".
While the same can be achieved by removing missing items and adding new items,
this action will keep any information already in the items.  This action does
not update the file size information or recalculate the checksum.

Remove Missing Items (Directory list only) - This action will remove from the
collection any items which are missing on the disk.

Calculate New Checksums - This action will calculate checksums for new files.
A file is considered new if it does not have any checksum information or if
the file size does not match the stored size.  This can be useful to update
the checksums for files after a rename, as the new file will usually have
a different size and will be considered new.  After calculating the checksum
the file size will be updated to match the real file size.  If the checksum
differs from the previous value, the file will be marked as dirty.

Calculate All Checksums - This action will calculate the checksums for all
files even if they allready have checksum information.

Verify Checksums - This action will verify that the file checksums match
their stored checksums.

Mark Dirty - This will mark a file as dirty.

Mark Clean - When a file is added or the checksum changes, it is marked as
dirty, so later you can make sure package and dependency information is correct.
Even after an update to the checksum, it will still be considered dirty until
explicitly marked as clean.


Packages and Dependencies
=========================

A file can make available packages that it provides, and can also depend on
other packages.  A package can be thought of as a feature that is either
provided by a file (a package) or required by a file (a dependency).

A package has a name as well as an optional version.  A dependency has a name
as well as an optional minimum and maximum version.  If a dependency does not
specify any minimum or maximum version, then it can match any version of the
specified package, even if the package has no version.  If a dependency has
a minimum version, a maximum version, or both, then it will only match the
package with a compatible version and will not match if the package does not
have a version.

In a version number, only letters and numbers are considered.  Any other symbol
is considered a separator and used to break the version into parts.  Also any
transitions from letter to number or number to letter causes a break into a new
part.  When comparing two versions, the lists of parts are made the same length
by padding the smallest with zeros, then each part is compared until there is a
difference.  Only the following letter parts are recognized and are considered
progressively higher:

    Less than 0: 

        "alpha", "beta", "pre", "rc"

    Greater than 0, but less than 1:
        
       "a" thru "z", "final"


Version Number Calculation
==========================

A value for a part is calculate as follows:

If a part is in the less than 0 list, then the position in that list is
subtracted from the number of items to produce the value, so the last item in
the list has a value of -1.

If the part is in the greater than 0, less than 1 list, then the position in
that list is added by one to produce the value, so the first item has a value
of 1.

If not in any list the item is converted to a number.  If it is 0, then it has
a value of 0.  If greater than 0, then the value is added to the length of the
greater than 0, less than one list, so that a version value of one will have
a value higher than that of the last item in the list.

Using the above Pre-0 and Post-0 lists:

1.0beta1 = (28, 0, -3, 28)
1.0.1 = (28, 0, 28)
28 > -3, so 1.0.1 > 1.0beta1

