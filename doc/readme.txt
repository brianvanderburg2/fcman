File Collection Manager
==========================================================================

File Collection Manager is a simple application to manage collections of
files.  Planned features are:

 * A file-browser interface
 * Keep a list of all files/directories that are part of the collection
 * Keep track of file checksums to verify that file have not been
   changed or corrupted
 * Keep track of dependencies between files
 * Automatically download updates based on rules
 * Automatically merge downloads into the collection, optionally removing
   old files from the collection or moving them to a history.
 * During download, automatically check the checksum and/or verify
   signatures.  This would require keeping a list of public keys for
   signature verification.
 * Support for MetaLink download updates.
 * Support to compress/recompress files when downloading by executing a
   script.  All scripts are globally defined so they can be easily checked
   for any problems and made sure they are safe.
 * Keep track of which files/directories are dirty.  A file is considered
   dirty once it has changed, indicating that information associated with
   it such as dependencies may need to be updated.  Files and directories
   can be marked as always-clean, meaning even when they change they are
   never dirty.  A directory is considered dirty if any of it's child
   items are dirty.  New items are also considered dirty.  If a directory
   is marked as always-clean, then by default any files or directories
   added will have the always-clean flag set.
 * Search based on keywords, tags, size, properties, dependencies, etc.
 * Autotag, automatically tag certain types of files with information.
 * File/directory have property dialogs.  Plugins can create property
   pages that can show/modify information.
 * Overlay icons show status information.  Plugins can create overlay
   icons.
 * Etc
    

Source Layout
==========================================================================

bin/     - The launchers for the application
doc/     - Documents and readme files
lib/     - The library path containing the Python modules
src/     - Other source code for compiled python modules, etc
install/ - Installable files
scripts/ - Other scripts used for build/etc


