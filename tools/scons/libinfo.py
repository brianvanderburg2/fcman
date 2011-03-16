# File:         libinfo.py
# Author:       Brian Allen Vanderburg II
# Purpose:      SCons library information
# Copyright:    This file is placed in the public domain
#
# Example:
#
# env = LibraryInfo(...)
#
# libraries['fftw3'] = env.LibraryInfo()
# libraries['fftw3'].ParseConfig('pkg-config fftw3 --cflags --libs')
#
# conf = libraries['fftw3'].Configure(custom_tests=...)
# do tests
# conf.Finish()
# 
# ...
# buildenv = env.Clone()
# buildenv.Merge(libraries['fftw3'])
#
##############################################################################


# Requirements
##############################################################################

from SCons import Script
from SCons.Environment import Environment as _Base

# LibraryInfo object (can also be used as an environment)
##############################################################################

class LibraryInfo(_Base):
    def __init__(self, *args, **kwargs):
        _Base.__init__(self, *args, **kwargs)

    def Merge(self, others):
        """ Merge other environments into this one """
        others = Script.Flatten(others)

        for other in others:
            # Preprocessor flags
            self.AppendUnique(CPPPATH = other.get('CPPPATH', []))
            self.AppendUnique(CPPDEFINES = other.get('CPPDEFINES', []))
            self.Append(CPPFLAGS = other.get('CPPFLAGS', []))
            
            # Compile flags
            self.Append(CFLAGS = other.get('CFLAGS', []))
            self.Append(CCFLAGS = other.get('CCFLAGS', []))
            self.Append(CXXFLAGS = other.get('CXXFLAGS', []))

            # Link flags
            self.AppendUnique(LIBPATH = other.get('LIBPATH', []))
            self.Append(LIBS = other.get('LIBS', []))
            self.Append(LINKFLAGS = other.get('LINKFLAGS', []))

    def LibraryInfo(self):
        """ Copy the environment with cleared variables """
        env = self.Clone()

        # Preprocessor flags
        env.Replace(CPPPATH = [])
        env.Replace(CPPDEFINES = [])
        env.Replace(CPPFLAGS = [])

        # Compile flags
        env.Replace(CFLAGS = [])
        env.Replace(CCFLAGS = [])
        env.Replace(CXXFLAGS = [])

        # Link flags
        env.Replace(LIBPATH = [])
        env.Replace(LIBS = [])
        env.Replace(LINKFLAGS = [])

        return env

