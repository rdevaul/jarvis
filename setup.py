#!/usr/bin/env python
"""Minimal setup.py for backwards compatibility.

This project uses pyproject.toml for configuration (PEP 517/518).
This setup.py shim enables installation with older pip versions
or tools that don't fully support pyproject.toml.

To install:
    pip install -e .           # Editable/development install
    pip install .              # Regular install
    pip install .[dev]         # With dev dependencies
"""

from setuptools import setup

if __name__ == "__main__":
    setup()
