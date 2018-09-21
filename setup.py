"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='pdfsurge',
    version='0.0.1',
    licence='MIT',
    description='Pure Python library to read, write, manipulate PDF documents with ease.',
    long_description=long_description,
    url='https://github.com/pdfshift/pdfsurge/',
    author='Cyril Nicodeme',
    author_email='cyril@pdfshift.io',

    # For a list of valid classifiers, see
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
        'Topic :: Software Development :: Pre-processors',
        'Topic :: Text Editors :: Text Processing',
        'Topic :: Text Editors :: Word Processors',
        'Topic :: Text Processing :: Markup',
        'Topic :: Utilities',

        'License :: OSI Approved :: MIT License',

        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],

    keywords='html pdf manipulate document merge watermark edit',

    project_urls={
        'Official Website': 'https://github.com/pdfshift/pdfsurge',
        'Documentation': 'https://github.com/pdfshift/pdfsurge',
        'Source': 'https://github.com/pdfshift/pdfsurge',
        'Company Website': 'https://pdfshift.io'
    },
)
