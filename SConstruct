# vim: set filetype=python:
#
# This file is part of File Collection Manager
# Copyright (C) 2009 Brian Allen Vanderburg II
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.


# Requirements
import os

from tools.scons.variables import Variables
from tools.scons.libinfo import LibraryInfo
from tools.scons.subst import TOOL_SUBST
from tools.scons.install import TOOL_INSTALL

from tools import sconf


# Application information
appinfo = {'APP_NAME':          'fcman',
           'APP_DISPLAY_NAME':  'File Collection Manager',
           'APP_VERSION':       '0.21',
           'APP_COPYRIGHT':     'Copyright (C) 2009 Brian Allen Vanderburg II',
           'APP_DESCRIPTION':   'A file collection management utility',
           'APP_WEBSITE':       'http://sourceforge.net/projects/fdepcheck'}

# Environment, variables, and libraries
root = Dir('#').abspath
config = ARGUMENTS.get('CONFIG')
if config:
    config = os.path.join(root, config)

defvars = Variables(config, ARGUMENTS)
defenv = LibraryInfo(TOOLS=[], ENV=os.environ)
deflibs = {}

Export('defvars', 'defenv', 'deflibs')

# Set up some variables
defvars.Add('BUILD', 'Which build to produce', '')
defvars.Add('BUILDDIR', 'Where to place built files', '.output/build')
defvars.Add('DESTDIR', 'Where to place installed files', '.output/install')
defvars.Add(BoolVariable('DEBUG', 'Build in debug mode', 0))
defvars.Update(defenv)

# Set up environment
defenv['BUILDTARGETS'] = {}
defenv['ROOTDIR'] = root
defenv['BUILDDIR'] = os.path.normpath(os.path.join(root, defenv['BUILDDIR']))
defenv['DESTDIR'] = os.path.normpath(os.path.join(root, defenv['DESTDIR']))
defenv['DESTDIR'] = defenv['DESTDIR'].rstrip(os.sep)

# Build system files also go in build directory
if not os.path.isdir(defenv['BUILDDIR']):
    os.makedirs(defenv['BUILDDIR'])

defenv.SConsignFile('${BUILDDIR}/.sconsign')
defenv['CONFIGUREDIR'] = '${BUILDDIR}/.sconf_temp'
defenv['CONFIGURELOG'] = '${BUILDDIR}/sconf_log.txt'

# Load commong builders
defenv.Tool('install')

TOOL_SUBST(defenv)
TOOL_INSTALL(defenv)
defenv.InstallExclude('.*', '*.~', '*.pyc', '*.pyo', '*.in', 'SConscript', 'SConstruct')

# Merge application information
for i in appinfo:
    defenv[i] = appinfo[i]

# Build specific settings
SConscript('tools/build/build.py')

# wxWidgets
defvars.Add('WX_FLAGS', 'wxWidgets compilation flags', '')
defvars.Add('WX_CONFIG', 'wxWidgets configure script', 'wx-config')
defvars.UpdateNew(defenv)

deflibs['wx'] = defenv.LibraryInfo()
conf = deflibs['wx'].Configure(custom_tests = {'ConfigureWX': sconf.ConfigureWX})

if not conf.ConfigureWX('2.8.7',
                        wx_flags=defenv['WX_FLAGS'],
                        wx_config=defenv['WX_CONFIG'],
                        wx_debug=defenv['DEBUG']):
    print('wxWidgets >= 2.8.7 is required.')
    Exit(1)

deflibs['wx'] = conf.Finish()
                            
# mhash
defvars.Add('MHASH_FLAGS', 'MHASH compilation flags', '')
defvars.UpdateNew(defenv)

deflibs['mhash'] = defenv.LibraryInfo()
conf = deflibs['mhash'].Configure(custom_tests = {'ConfigureMHash': sconf.ConfigureMHash})

if not conf.ConfigureMHash(mhash_flags=defenv['MHASH_FLAGS']):
    print('mhash is required.')
    Exit(1)

deflibs['mhash'] = conf.Finish()

# Build
for path in ['src', 'doc', 'data', 'packaging']:
    defenv.SConscript(path + '/SConscript',
                      variant_dir='${BUILDDIR}/' + path,
                      duplicate=0)

# Save
Help(defvars.GenerateHelpText(defenv))
defvars.Save(defenv.subst('${BUILDDIR}/config.cache'), defenv)


