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

setup(
    name="ultron-risk-scorer",
    version="0.2.0",
    description="AI-Assisted Software Architecture Platform",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="MIT",
    python_requires=">=3.8",
    packages=find_packages(
        where=".",
        include=["ultron*"],
        exclude=[
            "ultron.tests*",
            "ultron.validation*",
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
    install_requires=[
        "radon",
    ],
    entry_points={
        "console_scripts": [
            "ultron = ultron.interfaces.ultron:main",
            "ultron-mcp = ultron.interfaces.mcp_server:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
    ],
)
