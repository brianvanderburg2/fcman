# File:         variables.py
# Author:       Brian Allen Vanderburg II
# Purpose:      SCons variables wrapper
# Copyright:    This file is placed in the public domain
#
# With the normal varialble usage, any time the variables are updated
# on an enviroment, they will overwrite any changes that were made to
# existing variable, such as fixing paths, etc.  This wrapper behaves
# pretty much like a regular scons Variables object, but has an extra
# function, UpdateNew, which can update the environment with only the
# variables that have not been seen for the specified environment.
#
# Example:
#
# vars = Variables(cache, ARGUMENTS)
# vars.Add('BUILDDIR', 'Where to build', 'build')
# env = Environment(variables=vars)
#
# env['BUILDDIR'] = os.path.normpath(env['BUILDDIR'])
#
# ...
#
# # Maybe in another SConscript file
# vars.Add('ENABLE_PLUGIN', 1)
# vars.UpdateNew(env) # Does not replace modified BUILDDIR
#
# ...
# vars.Save(cache, env)
##############################################################################


# Requirements
##############################################################################

from SCons.Variables import Variables as _Base


# Variables object
##############################################################################
class Variables(_Base):
    def Update(self, env, args=None):
        self.unknown = {}
        _Base.Update(self, env, args)

        # Remember all known variables as being updated (even those with
        # default value of None and no specified value that have not been
        # changed).  A variable updated in a cloned environment is not
        # automatically considered udpated in the parent environment, but
        # a value updated in the parent environment before being cloned will
        # be considered updated in the cloned environment. 
        env['_UPDATED_VARIABLES_'] = [option.key for option in self.options]


    def UpdateNew(self, env, args=None):
        # Remember original values of already updated existing variables
        original = {}
        nonexist = []

        try:
            updated = env['_UPDATED_VARIABLES_']
        except KeyError:
            updated = None

        for option in self.options:
            if updated and option.key in updated:
                try:
                    original[option.key] = env[option.key]
                except KeyError:
                    nonexist.append(option.key)

        self.Update(env, args)

        # Restore original values for previously updated keys
        for key in original:
            env[key] = original[key]

        for key in nonexist:
            try:
                del env[key]
            except KeyError:
                pass

