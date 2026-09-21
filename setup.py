#!/usr/bin/env python3
"""Standard setuptools packaging configuration for ultron-risk-scorer."""

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

readme = ""
readme_path = os.path.join(here, "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        readme = f.read()

version_dict = {}
with open(os.path.join(here, "ultron", "_version.py"), "r", encoding="utf-8") as f:
    exec(f.read(), version_dict)
version = version_dict["__version__"]

setup(
    name="ultron-risk-scorer",
    version=version,
    description="AI-Assisted Software Architecture Platform",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="MIT",
    python_requires=">=3.10",
    packages=find_packages(
        where=".",
        include=["ultron*"],
        exclude=[
            "ultron.tests*",
            "ultron.validation*",
            "ultron.scratch*",
            "umags*",
            "synapse_project*",
        ],
    ),
    include_package_data=True,
    package_data={
        "ultron.interfaces": [
            "web/*.html",
            "web/*.css",
            "web/*.js",
            "web/modules/*.js",
            "web/*.json",
        ],
        "ultron": [
            "resources/*.json",
        ],
        "ultron.core.rkm": [
            "migrations/*.sql",
            "rulepacks/**/*.json",
        ],
    },
    install_requires=[],
    extras_require={
        "tray": ["pystray>=0.19.0", "Pillow>=9.0.0"],
        "metrics": ["radon>=5.1.0"],
        "dev": ["radon>=5.1.0", "pystray>=0.19.0", "Pillow>=9.0.0"],
    },
    entry_points={
        "console_scripts": [
            "ultron = ultron.interfaces.ultron:main",
            "ultron-server = ultron.interfaces.server:main",
            "ultron-mcp = ultron.interfaces.mcp_server:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
    ],
)
