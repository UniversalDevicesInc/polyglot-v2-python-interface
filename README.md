![Test And Publish](https://github.com/UniversalDevicesInc/polyglot-v2-python-interface/workflows/Publish%20PyPI%20and%20TestPyPI/badge.svg)

# UDI Polyglot v2 Interface Module

This is the Polyglot interface API module that is portable to be imported into your Python 3.4+ based NodeServers.

### Installation

Pip > 9 should be installed. This typically isn't the case, so you will have to upgrade Pip first.

```
# Check your pip version
pip -V
pip 9.0.1 from /home/e42/.local/lib/python2.7/site-packages (python 2.7)
pip3 -V
pip 9.0.1 from /usr/lib/python3/dist-packages (python 3.5)

# If Pip is < Version 9
sudo pip install -U pip
```

The module is updated in Pypi (Python's package interface Pip) on a regular basis. So simply install the module like you would any Python module:

```
# Install the Polyglot interface
pip install polyinterface --user
```


### Starting your NodeServer build

When you start building a NodeServer you are helping build the free and open Internet of Things. Thank you! If you run in to any issues please ask your questions on the [UDI Polyglot Forums](http://forum.universal-devices.com/forum/111-polyglot/).

To get started, [use the python2/3 template.](https://github.com/Einstein42/udi-poly-template-python)

From there just read the code itself, it is fully explained step by step.

### How to Enable your NodeServer in the Cloud
[Link to PGC Interface](https://github.com/UniversalDevicesInc/pgc-python-interface/blob/master/README.md)

### Controlling logging

By default when the Polyglot Python Interface is started up the logging is in DEBUG mode.  This is how it was setup from the very beginning.  If you want to change the level use:  
```
import polyinterface,logging
LOGGER = polyinterface.LOGGER
LOGGER.setLevel(logging.WARNING)
```

Beginning with version 2.1.0 it will also show all logging for modules you may referece, but only WARNING level by default.  If you want to configure the levels differently you can use:
```
polyinterface.LOG_HANDLER.set_basic_config(True,logging.DEBUG)
```
This will enable logging for everything that doesn't have a specific logger tied to it and sets the level to DEBUG

There are examples of this being used in the udi-poly-template-python mentioned above.
