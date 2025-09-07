#!/usr/bin/env python3
"""
Setup script for DShield MCP - Elastic SIEM Integration
"""


from setuptools import find_packages, setup


# Read the README file
def read_readme():
    with open("README.md", encoding="utf-8") as fh:
        return fh.read()


# Read requirements
def read_requirements():
    with open("requirements.txt", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]


setup(
    name="dshield-mcp",
    version="1.0.0",
    author="DShield MCP Team",
    author_email="security@example.com",
    description="MCP utility for Elastic SIEM integration with DShield threat intelligence",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/dshield-mcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Security",
        "Topic :: System :: Monitoring",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "dshield-mcp=mcp_server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json"],
    },
    keywords="security, siem, elasticsearch, threat-intelligence, mcp, chatgpt",
    project_urls={
        "Bug Reports": "https://github.com/your-org/dshield-mcp/issues",
        "Source": "https://github.com/your-org/dshield-mcp",
        "Documentation": "https://github.com/your-org/dshield-mcp/blob/main/README.md",
    },
)
