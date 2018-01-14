# __Changelog for Polyglot Python Interface v2__

### Version 2.0.8
* Fixed Address received in query (Use Polyglot 2.0.34+)
* Fixed incoming node checks
* Added getDriver method
* Added saveCustomData to store data in Polyglot db for next run.
* Fixes various bugs

### Version 2.0.7
* Added restart method on Interface
* Added additional logging for the parse functions

### Version 2.0.5
* Removed ST updates from polyinterface, they are in Polyglot itself now
* Removed checks for primary and if already exists. Let polyglot update itself

### Version 2.0.4
* Added delete call and functions to allow for NodeServer cleanup upon Polyglot deletion
