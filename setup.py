from distutils.core import setup

setup(name='clap',
      version='0.0.1',
      author='Solomon Hykes',
      package_dir = {
          'clap' : '.',
        },
      packages=[
          'dotcloud',
    ]
)
