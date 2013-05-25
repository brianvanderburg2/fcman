from distutils.core import setup

setup(
    name='fcman',
    version='0.1',
    description='File Collection Manager',
    author='Brian Allen Vanderburg II',
    author_email='brianvanderburg@users.sourceforge.net',
    packages=['fcman'],
    package_dir={'': 'lib'},
    package_data={'fcman': ['resources/*.png']}
)
