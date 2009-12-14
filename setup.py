
from setuptools import setup

setup(name='clapp',
      version='0.0.1',
      author='Solomon Hykes',
      install_requires=['distribute', 'simplejson >= 2.0.9', 'jsonschema', 'ejs >= 0.0.1'],
      package_dir = {'clapp' : '.'},
      packages=['clapp'],
      scripts=['clapp.py'],
      dependency_links=['http://dotcloud.org.s3.amazonaws.com/ejs-0.0.1.tar.gz', 'http://jsonschema.googlecode.com/files/jsonschema-0.2a.tar.gz']
)
