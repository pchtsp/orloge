#!/usr/bin/env python

from setuptools import setup

packages = ['orloge']

requirementslist = ['requirements.txt']

required = []
for r in requirementslist:
    with open(r, 'r') as requirements:
        required.append(requirements.read().splitlines())


kwargs = {
    "name": "orloge",
    "version": 0.1,
    "packages": packages,
    "description": "OR log evaluator",
    "long_description": "Operations Research log extractor",
    "author": "Franco Peschiera",
    "maintainer": "Franco Peschiera",
    "author_email": "pchtsp@gmail.com",
    "maintainer_email": "pchtsp@gmail.com",
    "install_requires": required,
    "url": "https://github.com/pchtsp/orloge",
    "download_url": "https://github.com/pchtsp/orloge/archive/master.zip",
    "keywords": "Mathematical Optimization solver log parser",
    "classifiers": [
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
}

setup(**kwargs)