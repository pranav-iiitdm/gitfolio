from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="gitfolio",
    version="1.0.0",
    author="Pranav Parimi",
    description="Auto-generate ATS-friendly resume bullets from your GitHub commits",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pranav-iiitdm/gitfolio",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "click>=8.1.0",
        "PyGithub>=2.1.0",
        "anthropic>=0.25.0",
        "PyYAML>=6.0",
        "flask>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "gitfolio=gitfolio.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
)
