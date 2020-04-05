#!/usr/bin/env python

from setuptools import setup
from pathlib import Path


def get_requirements():
    return Path('requirements.txt').read_text().splitlines()


setup(
    name="mhist",
    version='0.0.1',
    install_requires=get_requirements(),
    package_dir={'mhist': 'src/mhist'},
    packages=['mhist'],
    include_package_data=True,
    package_data={'mhist': ['mhist.lua.j2']},
    entry_points={'console_scripts': ['mhist = mhist:main']},
)
