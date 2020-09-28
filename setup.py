#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read().replace(".. :changelog:", "")

requirements = [
    # TODO: put package requirements here
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name="ts_scheduler",
    version="0.1.0",
    description="LSST Scheduler",
    long_description=readme + "\n\n" + history,
    author="Francisco Delgado",
    author_email="fdelgado@lsst.org",
    url="https://github.com/ /ts_scheduler",
    packages=["ts_scheduler"],
    package_dir={"ts_scheduler": "ts_scheduler"},
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=False,
    keywords="ts_scheduler",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
    ],
    test_suite="tests",
    tests_require=test_requirements,
)
