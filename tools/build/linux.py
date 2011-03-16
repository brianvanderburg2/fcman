# This file is part of File Collection Manager
# Copyright (C) 2009 Brian Allen Vanderburg II
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.


# Requirements
import os

import SCons.Errors

Import('*')


# Variables
defvars.Add('PREFIX', 'Installation prefix', '/usr/local')
defvars.UpdateNew(defenv)


# Environment
os.umask(0022)

if not os.path.isabs(defenv['PREFIX']):
    raise SCons.Errors.UserError('PREFIX must be an absolute path')
else:
    defenv['PREFIX'] = os.path.normpath(defenv['PREFIX'])

# Prepare tools
defenv.Tool('gcc')
defenv.Tool('g++')
defenv.Tool('gnulink')

defenv.Append(CCFLAGS='-W -Wall')
defenv.Append(CCFLAGS='-fno-strict-aliasing')
defenv.Append(CCFLAGS='-g')

if not defenv['DEBUG']:
    defenv.Append(CCFLAGS='-O2 --fast-math')


