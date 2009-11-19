from distutils.core import setup

setup(name='clapp',
      version='0.0.1',
      author='Solomon Hykes',
      package_dir = {
          'clapp' : '.',
        },
      packages=[
          'clapp',
    ]
)
