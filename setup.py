#!/usr/bin/env python
from setuptools import setup, find_packages
import os

setup(name='federation',
      version='0.1',
      description='Federation Node Daemon',
      author='CommerceBlock',
      author_email='nikolaos@commerceblock.com',
      url='http://github.com/commerceblock/federation',
      packages=find_packages(),
      scripts=[],
      include_package_data=True,
      data_files=[],
)
