from distutils.core import setup
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
  name='as3935_async',
  packages=['as3935_async'],
  version='0.0.1',
  license='gpl-3.0',
  description="An async Python3 module to control the lightning detector AS3935 chip",
  long_description=long_description,
  long_description_content_type="text/x-rst",
  author="mjkl-gh",
  author_email="9350991+mjkl-gh@users.noreply.github.com",
  url = 'https://github.com/mjkl-gh/as3935_async',
  download_url='https://github.com/mjkl-gh/as3935_async/archive/v0.0.1-alpha.tar.gz',
  keywords = ['python', 'raspberry', 'gpio', 'lightning', 'sensor'],
  install_requires=[
          'asyncpio @ git+https://github.com/mjkl-gh/asyncpio@master',
      ],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7'
  ],
)
