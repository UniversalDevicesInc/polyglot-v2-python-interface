# UDI Polyglot v2 Interface Module

This is the Polyglot interface API module that is portable to be imported into your Python 3.4+ based NodeServers.

### Installation

Pip > 9 should be installed. This typically isn't the case, so you will have to upgrade Pip first.

```
# Check your pip version
pip -V
pip 9.0.1 from /usr/local/lib/python3.4/dist-packages (python 3.4)

# If Pip is < Version 9
sudo pip install -U pip
```

The module is updated in Pypy (Python's package interface Pip) on a regular basis. So simply install the module like you would any Python module:

```
# Install the Polyglot interface
sudo pip install polyglotinterface
```

### NodeServer .env Addition

You should already have a `~/.polyglot/.env` file if you are on the same host that Polyglot is running on, so most of the settings should be pulled from that automatically. If you are not running co-resident with Polyglot, just copy over `~/.polyglot/.env` to the host this will be running on.

Add a single line to your `~/.polyglot/.env` file that contains the 'name' of the variable you will pass, and equals the profile number that this NodeServer will be in Polyglot. For example, if I am running a LiFX NodeServer as profile 8 I would add the following:
```
LIFX_NS = 8
```

Keep in mind that the Variable name 'LIFX_NS' is completely arbitrary, it can be anything you want, just make sure that it is unique in the .env file.

### Starting your NodeServer build

When you start building a NodeServer you are helping build the free and open Internet of Things. Thank you! If you run in to any issues please ask your questions on the [UDI Polyglot Forums](http://forum.universal-devices.com/forum/111-polyglot/).

First step in your new project is to get the Interface ready to go. A built in logger is included in the PolyInterface and will let you attach to it.

```
# Import the Polyglot Interface to your project
# You don't have to use the 'as polyglot' but it lead to a little better readability for me
import polyinterface
```
Instantiate the logger to allow you to log anything into ./log/debug.log
```
# Setup the LOGGER, I like to do this globally outside of the main function right under the imports.
LOGGER = polyglot.LOGGER
```

After you run this line you can then use the format
```
LOGGER.debug('This is going to be put in the log!')
```

LOGGER.debug can be changed to .info or .warning or .error depending on what type of item you are logging. Logging to the console is fine to test with, but don't be that guy on production apps.

Now that the logger is instantiated, lets start up our polyglot interface. In this example I am using the LiFX NodeServer.
```
if __name__ == "__main__":
    # Try/Catch for shutdown signals or keyboard interrupt so we can shut down cleanly.
    try:
        """
        Grab the "LIFX_NS" variable from the .polyglot/.env file. This is where
        we tell it what profile number this NodeServer is.
        """
        poly = polyinterface.Interface('LIFX_NS')
        poly.start()
        lifx = Control(poly)
        while True:
            input = poly.inQueue.get()
            lifx.parseInput(input)
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
```

So to expound on this example. On program start we create the interface with the `poly = polyglot.Interface('LIFX_NS')`. LIFX_NS is the variable in our .env file that tells the NodeServer what profile number it will be on Polyglot/ISY. Refer to the NodeServer .env addition for more information.

Secondly we start our polyglot connections with `poly.start()`. This will take all the settings from .env and create the threaded asynchronous event loop and connect to MQTT and Polyglot. In the `log/debug.log` file. You should see the following:
```
2017-07-01 16:13:23,030 INFO     Polyglot v2 Interface Starting...
2017-07-01 16:13:23,046 INFO     Connecting to MQTT... 10.0.0.17:1883
2017-07-01 16:13:23,046 INFO     Started LiFX Protocol
2017-07-01 16:13:23,050 INFO     MQTT Connected with result code 0 (Success)
2017-07-01 16:13:23,051 INFO     MQTT Subscribing to topic: udi/polyglot/ns/8 -  MID: 1 Result: 0
2017-07-01 16:13:23,051 INFO     MQTT Subscribing to topic: udi/polyglot/connections/polyglot -  MID: 2 Result: 0
2017-07-01 16:13:23,548 INFO     Sent Connected message to Polyglot
```

Now we are connected and ready to go. We check the inQueue and run the polyinterface.Control.parseInput method when we receive input.

##### polyinterface.Controller API

The next line `lifx = Control(poly)` is our NodeServer class. This is a child class of the polyinterface.Controller class that comes with polyinteface. The parent class handles some of the heavy lifting for you, like parsing and running incoming commands, checking the config received by Polyglot, handling the results of commands sent TO Polyglot, and the short and long polling interface.

Typically a "Control Node" is created and all sub-nodes (lights, etc) are nested under it. This is done to keep some semblance of cleanliness in the ISY. Consider this best practice.

Once the NodeServer sends the connected message to Polyglot, it receives back the running config for that NodeServer that resides in Polyglot's database.

```
class Control(polyinterface.Controller):

    def __init__(self, poly):
        super().__init__(poly)
        LOGGER.info('Started NodeServer')
```

Once the configuration is received by Polyglot and the control node is added to the ISY then the start method is automatically called.

```
def start(self):
    """
    In order to have polls you should run the parent method startPolls()
    you can pass in the timers in seconds. LongPoll first, then ShortPoll.
    If you don't need Polling then you don't have to start them.
    """
    self.startPolls(60, 10)
    <start your nodeserver code here>
```

Optional Loop overrides for Polling. ShortPoll is default 10 seconds, longPoll is 30 seconds.
This is done in the Control class. You must super if you override these or your poll will not work.

```
    def shortPoll(self, timer = 10):
        """
        Overridden shortPoll. It is imperative that you super this if you override it
        as the threading.Timer loop is in the parent method.
        """
        super().shortPoll(timer)
        <your code here>

    def longPoll(self, timer = 30):
      """
      Overridden longPoll. It is imperative that you super this if you override it
      as the threading.Timer loop is in the parent method.
      """
      super().longPoll(timer)
      <your code here>
```

Parent methods in the **polyinterface.Controller** class:
 - **addNode(Node)**: Node is a polyinterface.Node class instance. This method adds a node to the ISY and Polyglot database. Checks if the node already exists, if it does then run the polyinterface.Node.start() method for that node. If it does not exist, send the command to add it and wait for the response asynchronously. Once the response is received if the node was added successfully, then run its start() method.

 - **startPolls(long = 30, short = 10)**: Use this method to begin the polling timers. Typically called from your NodeServer's .start() method. See example above.

- **parseInput(input)**: this method takes the input from Polyglot and handles any commands or results that are sent to the NodeServer. See

- **toJSON()**: returns a json representation of the control class to LOGGER.debug, useful for testing.

Private methods that should not be overridden:

- **_handleResult(result)**: This is the listener method that waits for incoming results messages and handles anything that it requires. Used to listen for the addNode success or failure messages and run the nodes .start() method if successful.

- **_gotConfig(config)**: This method is executed once the polyinterface.Interface class receives the configuration from Polyglot. It executes the polyinterface.Controller.start() method once it finishes parsing the config.

Node Meta Model Profile data is at the end of every ISY added node to identify and represent the Node in the ISY device. [See Appendix 7.2 of UDI's NodeServer Development Guide](http://www.universal-devices.com/developers/wsdk/5.0.0/ISY-WS-SDK-Node-Server.pdf).

For a controller, simple is better. This says that it will use the **lifxcontrol** node definition in the profile.zip nodedefs.xml:
```
drivers = []
commands = {'DISCOVER': discover}
node_def_id = 'lifxcontrol'
```

##### polyinterface.Node API

The **polyinterface.Node** class is used as the Parent class of any nodes you add to Polyglot and the ISY. Example:

```
class MyNode(polyglotinterface.Node):
    def __init__(self, parent, primary, address):
        super().__init__(parent, primary, address, 'My Name in ISY here')

    def start(self):
        self.query()

    def query(self, command = None):
      <query something>
      self.value = <query response>
      self.setDriver('ST', self.value)      

    def setOn(self, command):
      <turn something on>

    def setOff(self, command):
      <turn something off>

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 25}]

    _commands = {
                    'DON': setOn, 'DOF': setOff, 'QUERY': query
                }

    node_def_id = 'mynode'
```

When you instantiate the polyinterface.Node class typically they are created from the Control node during some sort of discovery process. You need to pass in the Controller instance, the primary node's address, which is typically the controller, the address of the node itself, and the name as you want it to appear in the ISY.

ISY addresses must be equal to or less than 12 characters long, be unique, and not contain spaces or special characters.

For example:
```
myNode = polyinterface.Node(controller, controller.address, thisnode.address, 'Office Light')
controller.addNode(myNode)
```

Parent methods in the **polyinterface.Node** class:
 - **setDriver(driver, value, report = True)**: This will set the driver to the value in the running config. If report = True then we send the status change to Polyglot which updates the ISY value.

 - **reportDrivers()**: Sends an update to Polyglot and ISY of ALL the drivers and their current values.

 - **toJSON()**: Sends a JSON representation of the Node to the Logger as a DEBUG.
