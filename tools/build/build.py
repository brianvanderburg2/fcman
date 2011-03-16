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


# Detect if not specified
if not defenv['BUILD']:
    if os.name == 'nt':
        defenv['BUILD'] = 'windows'
    elif os.name == 'posix':
        defenv['BUILD'] = 'linux'

if not defenv['BUILD']:
    raise SCons.Errors.UserError('BUILD not detected. Specify manually.')

# Load
defenv.SConscript('${BUILD}.py')

