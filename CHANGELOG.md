# __Changelog for Polyglot Python Interface v2__

### Version 2.1.0
- Add log handler set_basic_config method to control logging for referenced modules
- Setting "profile_version": null
  in server.json will force updating profile on all restarts, which should only
  be used while testing profiles changes during development.

### Version 2.0.41
- Remove call to basicConfig so referenced module logging will not show up which
  is the behavior prior to 2.0.35
- Will add an option to put it back when I have time.

### Version 2.0.38-2.0.40
- Version changes while getting pypi automated releases to work

### Version 2.0.37
- Fixed bug for nodeservers that do not pass in name to polyinterface.Interface call.
- Added PyLogger class as suggested by @firstone

### Version 2.0.36
- New logger format with name instead of module
- Nodesrevers can call polyinterface.set_log_format if they don't like the default which is:
  '%(asctime)s %(threadName)-10s %(name)-18s %(levelname)-8s %(module)s:%(funcName)s: %(message)s'

### Version 2.0.35
- Use logger basicConfig so settings are shared by other modules used by NodeServers
- Add module to logger, asked all devs for opinions but nobody responded.

### Version 2.0.34
* Proper SSLError fix fix https://github.com/UniversalDevicesInc/polyglot-v2/issues/13

### Version 2.0.33
* Added Added get_server_data and check_profile poly methods

### Version 2.0.32
* Added get_network_interface method

### Version 2.0.31
* Removed features
* Stack Overflow fix https://github.com/UniversalDevicesInc/polyglot-v2/issues/8
* SSLError fix fixed https://github.com/UniversalDevicesInc/polyglot-v2/issues/13

### Version 2.0.29
* TLS 1.3 bypass (for now)
* Better thread handling
* Nicer log format with Thread Name
* MainThread loop MQTT disconnect avoidance
* PGC init compatibility

### Version 2.0.28
* Log propagaion fix
* Typed parameters
* Config docs
* Notices by key
* Features

### Version 2.0.27
* Remove notice fixed https://github.com/UniversalDevicesInc/polyglot-v2/issues/19
* Interactive fixes https://github.com/UniversalDevicesInc/polyglot-v2-python-interface/pull/2

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
