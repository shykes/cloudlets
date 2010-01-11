
from setuptools import setup

setup(name='cloudlets',
      version='0.0.1',
      author='Solomon Hykes',
      install_requires=['simplejson >= 2.0.9', 'jsonschema', 'ejs >= 0.0.1', 'argparse'],
      package_dir = {'cloudlets' : '.'},
      packages=['cloudlets'],
      scripts=['bin/cloudlets'],
      dependency_links=['http://dotcloud.org.s3.amazonaws.com/ejs-0.0.1.tar.gz', 'http://jsonschema.googlecode.com/files/jsonschema-0.2a.tar.gz']
)
