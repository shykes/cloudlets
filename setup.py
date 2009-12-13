from distutils.core import setup

from distribute_setup import use_setuptools
use_setuptools()

setup(name='clapp',
      version='0.0.1',
      author='Solomon Hykes',
      install_requires=['simplejson >= 2.0.9'],
      package_dir = {'clapp' : '.'},
      packages=['clapp'],
      scripts=['clapp.py']
)
