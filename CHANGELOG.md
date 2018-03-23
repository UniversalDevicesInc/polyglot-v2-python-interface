# __Changelog for Polyglot Python Interface v2__

### Version 2.0.26
* Will not work properly with polyglot version 2.1.1 or prior.
* polyinterface version is printed to nodeserver log on startup
* addNode automatically adds/removes drivers for existing nodes, no need for update=True anymore
* addNode and updateNode can change the node_def_id

### Version 2.0.23
* setDriver has optional uom argument now

### Version 2.0.22
* Added reportCmd
* Fixed MQTT Timeout Issue

### Version 2.0.18
* ST connection set from polyinterface

### Version 2.0.9
* setDriver testing fix to prevent un-needed updates
* receive config on every successful driver change
* controller.\_nodes and node.\_drivers are real-time updated
* added node.config with real-time polyglot config for that node

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
