from setuptools import setup
from botlib import __doc__, __version__

with open('README.md') as fp:
    longdesc = fp.read()

setup(
    name='botlib',
    version=__version__,
    description=__doc__.strip(),
    long_description=longdesc,
    long_description_content_type="text/markdown",
    author='relikd',
    url='https://github.com/relikd/botlib',
    license='MIT',
    packages=['botlib'],
    entry_points={
        'console_scripts': [
            'html2list = botlib.html2list:_cli',
        ]
    },
    python_requires='>=3.5',
    keywords=[
        'conversion',
        'converter',
        'data-processing',
        'html',
        'xml',
        'rss',
        'telegram',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Text Processing :: General',
        'Topic :: Text Processing :: Markup',
        'Topic :: Utilities',
    ],
)
