import re
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


INIT_FILE = 'sqlalchemy_aio/__init__.py'
init_data = open(INIT_FILE).read()

metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", init_data))

AUTHOR_EMAIL = metadata['author']
VERSION = metadata['version']
LICENSE = metadata['license']
DESCRIPTION = metadata['description']

AUTHOR, EMAIL = re.match(r'(.*) <(.*)>', AUTHOR_EMAIL).groups()

requires = [
    'represent>=1.4',
    'sqlalchemy',
    'outcome',
]

extras_require = dict()

extras_require['test-noextras'] = [
    'pytest >= 5.4',
    'pytest-asyncio >= 0.14',
]

extras_require['test'] = extras_require['test-noextras'] + [
    'pytest-trio >= 0.6',
]

extras_require['trio'] = [
    'trio >= 0.15',
]


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='sqlalchemy_aio',
    version=VERSION,
    description=DESCRIPTION,
    long_description=open('README.rst').read(),
    author=AUTHOR,
    author_email=EMAIL,
    url='https://github.com/RazerM/sqlalchemy_aio',
    packages=find_packages(exclude=['tests']),
    cmdclass={'test': PyTest},
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    license=LICENSE,
    install_requires=requires,
    extras_require=extras_require,
    python_requires='>=3.6',
)
