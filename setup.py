#/usr/bin/env python3

from setuptools import setup, find_namespace_packages

metadata = {}
with open("mrbavii/fcman/_version.py") as handle:
    exec(handle.read(), metadata)

setup(
    name="mrbavii.fcman",
    version=metadata["__version__"],
    description=metadata["__doc__"],
    url='',
    author=metadata["__author__"],
    license='MIT',
    packages=find_namespace_packages(),
    entry_points={
        'console_scripts': [
            'mrbavii-fcman = mrbavii.fcman.main:main'
        ]
    }
)
