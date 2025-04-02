#!/usr/bin/env python3

from setuptools import setup


with open("README.md") as fh:
    long_description = fh.read()


setup(
    name="django-paradedb",
    version="0.0.2",
    description="Django lookups and indexes for the ParadeDB PostgreSQL extension",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Marco Bonetti",
    author_email="mbonetti@gmail.com",
    package_dir={"": "src"},
    packages=["paradedb"],
    license="MIT",
    install_requires=["Django >= 4.2", "psycopg2-binary"],
    extras_require={"test": ("tox",)},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Framework :: Django :: 5.1",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
    ],
)
