import os
from setuptools import setup, find_packages

# single source of truth for package version
version_ns = {}
with open(os.path.join("paropt_sdk", "version.py")) as f:
    exec(f.read(), version_ns)
version = version_ns['__version__']

setup(
    name='paropt_sdk',
    version=version,
    packages=find_packages(),
    description='Python interface and utilities for paropt',
    long_description=("paropt SDK contains a Python interface to the Paropt "
                      "Service."),
    install_requires=[
        "pandas", "requests", "jsonschema", "globus_sdk", "configobj", "pyyaml"
    ],
    python_requires=">=3.4",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering"
    ],
    keywords=[
        "paropt",
        "FaaS",
        "Function Serving"
    ],
    author='Ted Summer',
    author_email='ted.summer2@gmail.com',
    license="Apache License, Version 2.0",
    url="https://github.com/macintoshpie/paropt-service-sdk"
)
