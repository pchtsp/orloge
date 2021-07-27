#!/usr/bin/env python

from setuptools import setup

packages = ["orloge"]
requirementslist = ["requirements.txt"]

with open("README.md", "r") as fh:
    long_description = fh.read()

required = []
for r in requirementslist:
    with open(r, "r") as requirements:
        required.append(requirements.read().splitlines())


kwargs = {
    "name": "orloge",
    "version": 0.17,
    "packages": packages,
    "description": "OR log extractor",
    "long_description": long_description,
    "long_description_content_type": "text/markdown",
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
    ],
}

setup(**kwargs)

"""
reminder on how to deploy:
(from https://packaging.python.org/tutorials/packaging-projects/)

# installation:
python3.8 -m pip install --upgrade pip
python3.8 -m pip install --user --upgrade setuptools wheel --user
python3.8 -m pip install --user --upgrade twine --user

# bundelling
python3.8 setup.py sdist bdist_wheel

# test upload:
python3.8 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# real upload:
python3.8 -m twine upload dist/*
"""
