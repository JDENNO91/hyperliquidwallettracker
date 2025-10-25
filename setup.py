#!/usr/bin/env python3
"""
Setup script for HyperLiquidWalletTracker
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="hyperliquidwallettracker",
    version="1.0.0",
    author="JDENNO91",
    author_email="jdenno91@example.com",
    description="Advanced real-time cryptocurrency wallet monitoring system for Hyperliquid protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JDENNO91/hyperliquidwallettracker",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "hyperliquidwallettracker=hyperliquidwallettracker.cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
