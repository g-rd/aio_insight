from setuptools import setup, find_packages

# Load the README file for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aio-insight",  # The package name
    version="0.1.4",  # Initial version number
    author="Gerd Kukemilk",
    author_email="",
    description="A Python library for asynchronous querying of Jira Insight API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/g-rd/aio_insight",
    packages=find_packages(),  # Automatically discover all packages
    install_requires=[  # List of dependencies
        "aiofiles==24.1.0",
        "anyio==4.4.0",
        "certifi==2024.7.4",
        "h11==0.14.0",
        "httpcore==1.0.5",
        "httpx==0.27.0",
        "idna==3.7",
        "oauthlib==3.2.2",
        "six==1.16.0",
        "sniffio==1.3.1",
    ],
    classifiers=[  # Metadata for the package
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',  # Specify minimum Python version
    license='Apache License 2.0',
)
