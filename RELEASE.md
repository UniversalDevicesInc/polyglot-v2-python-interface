# UDI Polyglot v2 Interface Module Releases

We will now be doing official releases of this interface.

## Version Numbering

We will be using [Semantic Versioning](https://semver.org/) Which is MAJOR.MINOR.PATCH
- MAJOR - Will follow major Polyglot releases, current 2
- MINOR - Any release that adds functionality
- PATCH - Only fixes problems, no functional changes

## Release Information

We will be following methods defined [Managing releases in a repository
](https://help.github.com/en/github/administering-a-repository/managing-releases-in-a-repository)

https://pypi.org
https://test.pypi.org

Created github user udi-pg-dev to email pg-dev@universal-devices.com
Created pypi and test pypi users udi-pg-dev

Documentation
https://realpython.com/documenting-python-code/
Use NumPy/SciPy Docstrings

## Generating a Release

The releases are handled by Github actions
- Go to [polyglot-v2-pyhton-interface Releases](https://github.com/UniversalDevicesInc/polyglot-v2-python-interface/releases)
- Click 'Draft a new release'
- Set Tag version to the relese with a v prefix, e.g. v2.1.0
- Target: should always be master
- Set Release title: Version 2.1.0
- Describe the release.  Currently copy the info added to RELEASE.md
- This is a pre-release is not yet tested.
