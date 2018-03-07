#!/usr/bin/env python
"""
Python Interface for UDI Polyglot v2 NodeServers
by Einstein.42 (James Milne) milne.james@gmail.com
"""

import logging
import logging.handlers
import warnings
import time
import json
import sys
import select
import os
import ssl
import re

try:
    import queue
except (ImportError):
    import Queue as queue
#import asyncio
from os.path import join, expanduser
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from threading import Thread
from copy import deepcopy

def warning_on_one_line(message, category, filename, lineno, file=None, line=None):
    return '{}:{}: {}: {}'.format(filename, lineno, category.__name__, message)

class LoggerWriter(object):
    def __init__(self, level):
        self.level = level

    def write(self, message):
        if not re.match(r'^\s*$', message):
            self.level(message.strip())

    def flush(self):
        pass

def setup_log():
   # Log Location
   #path = os.path.dirname(sys.argv[0])
   if not os.path.exists('./logs'):
       os.makedirs('./logs')
   log_filename = "./logs/debug.log"
   log_level = logging.DEBUG  # Could be e.g. "DEBUG" or "WARNING"

   #### Logging Section ################################################################################
   logging.captureWarnings(True)
   logger = logging.getLogger(__name__)
   warnlog = logging.getLogger('py.warnings')
   warnings.formatwarning = warning_on_one_line
   logger.setLevel(log_level)
   # Set the log level to LOG_LEVEL
   # Make a handler that writes to a file,
   # making a new file at midnight and keeping 3 backups
   handler = logging.handlers.TimedRotatingFileHandler(log_filename, when="midnight", backupCount=30)
   # Format each log message like this
   formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
   # Attach the formatter to the handler
   handler.setFormatter(formatter)
   # Attach the handler to the logger
   logger.addHandler(handler)
   warnlog.addHandler(handler)
   return logger

LOGGER = setup_log()
sys.stdout = LoggerWriter(LOGGER.debug)
sys.stderr = LoggerWriter(LOGGER.error)

LOGGER.info('Polyglot v2 Interface Starting...')
"""
Grab the ~/.polyglot/.env file for variables
If you are running Polyglot v2 on this same machine
then it should already exist. If not create it.
"""
warnings.simplefilter('error', UserWarning)
try:
    load_dotenv(join(expanduser("~") + '/.polyglot/.env'))
except (UserWarning) as err:
    LOGGER.warning('File does not exist: {}.'.format(join(expanduser("~") + '/.polyglot/.env')), exc_info=True)
    # sys.exit(1)
warnings.resetwarnings()

"""
If this NodeServer is co-resident with Polyglot it will receive a STDIN config on startup
that looks like:
{"token":"2cb40e507253fc8f4cbbe247089b28db79d859cbed700ec151",
"mqttHost":"localhost","mqttPort":"1883","profileNum":"10"}
"""

init = select.select([sys.stdin], [], [], 1)[0]
if init:
    line = sys.stdin.readline()
    try:
        line = json.loads(line)
        os.environ['PROFILE_NUM'] = line['profileNum']
        os.environ['MQTT_HOST'] = line['mqttHost']
        os.environ['MQTT_PORT'] = line['mqttPort']
        os.environ['TOKEN'] = line['token']
        LOGGER.info('Received Config from STDIN.')
    except (Exception) as err:
        #e = sys.exc_info()[0]
        LOGGER.error('Invalid formatted input. Skipping. {}'.format(err), exc_info=True)

class Interface(object):
    """
    Polyglot Interface Class

    :param envVar: The Name of the variable from ~/.polyglot/.env that has this NodeServer's profile number
    """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=unused-argument

    __exists = False

    def __init__(self, envVar = None):
        if self.__exists:
            warnings.warn('Only one Interface is allowed.')
            return
        self.connected = False
        self.profileNum = os.environ.get("PROFILE_NUM")
        if self.profileNum is None:
            if envVar is not None:
                self.profileNum = os.environ.get(envVar)
        if self.profileNum is None:
            LOGGER.error('Profile Number not found in STDIN or .env file. Exiting.')
            sys.exit(1)
        self.profileNum = str(self.profileNum)
        self.topicPolyglotConnection = 'udi/polyglot/connections/polyglot'
        self.topicInput = 'udi/polyglot/ns/{}'.format(self.profileNum)
        self.topicSelfConnection = 'udi/polyglot/connections/{}'.format(self.profileNum)
        self._mqttc = mqtt.Client(envVar, False)
        #self._mqttc.will_set(self.topicSelfConnection, json.dumps({'node': self.profileNum, 'connected': False}), retain=True)
        self._mqttc.on_connect = self._connect
        self._mqttc.on_message = self._message
        self._mqttc.on_subscribe = self._subscribe
        self._mqttc.on_disconnect = self._disconnect
        self._mqttc.on_publish = self._publish
        self._mqttc.on_log = self._log
        self.useSecure = True
        if 'USE_HTTPS' in os.environ:
            self.useSecure = os.environ['USE_HTTPS']
        if self.useSecure is True:
            self._mqttc.tls_set(join(expanduser("~") + '/.polyglot/ssl/polyglot.crt'),
                join(expanduser("~") + '/.polyglot/ssl/client.crt'),
                join(expanduser("~") + '/.polyglot/ssl/client_private.key'))
        #self._mqttc.tls_insecure_set(True)
        self.config = None
        #self.loop = asyncio.new_event_loop()
        self.loop = None
        self.inQueue = queue.Queue()
        #self.thread = Thread(target=self.start_loop)
        self.isyVersion = None
        self._server = os.environ.get("MQTT_HOST") or 'localhost'
        self._port = os.environ.get("MQTT_PORT") or '1883'
        self.polyglotConnected = False
        self.__configObservers = []
        self.__stopObservers = []
        Interface.__exists = True

    def onConfig(self, callback):
        """
        Gives the ability to bind any methods to be run when the config is received.
        """
        self.__configObservers.append(callback)

    def onStop(self, callback):
        """
        Gives the ability to bind any methods to be run when the stop command is received.
        """
        self.__stopObservers.append(callback)

    def _connect(self, mqttc, userdata, flags, rc):
        """
        The callback for when the client receives a CONNACK response from the server.
        Subscribing in on_connect() means that if we lose the connection and
        reconnect then subscriptions will be renewed.

        :param mqttc: The client instance for this callback
        :param userdata: The private userdata for the mqtt client. Not used in Polyglot
        :param flags: The flags set on the connection.
        :param rc: Result code of connection, 0 = Success, anything else is a failure
        """
        if rc == 0:
            self.connected = True
            results = []
            LOGGER.info("MQTT Connected with result code " + str(rc) + " (Success)")
            # result, mid = self._mqttc.subscribe(self.topicInput)
            results.append((self.topicInput, tuple(self._mqttc.subscribe(self.topicInput))))
            results.append((self.topicPolyglotConnection, tuple(self._mqttc.subscribe(self.topicPolyglotConnection))))
            for (topic, (result, mid)) in results:
                if result == 0:
                    LOGGER.info("MQTT Subscribing to topic: " + topic + " - " + " MID: " + str(mid) + " Result: " + str(result))
                else:
                    LOGGER.info("MQTT Subscription to " + topic + " failed. This is unusual. MID: " + str(mid) + " Result: " + str(result))
                    # If subscription fails, try to reconnect.
                    self._mqttc.reconnect()
            self._mqttc.publish(self.topicSelfConnection, json.dumps({'node': self.profileNum, 'connected': True}), retain = True)
            LOGGER.info('Sent Connected message to Polyglot')
        else:
            LOGGER.error("MQTT Failed to connect. Result code: " + str(rc))

    def _message(self, mqttc, userdata, msg):
        """
        The callback for when a PUBLISH message is received from the server.

        :param mqttc: The client instance for this callback
        :param userdata: The private userdata for the mqtt client. Not used in Polyglot
        :param flags: The flags set on the connection.
        :param msg: Dictionary of MQTT received message. Uses: msg.topic, msg.qos, msg.payload
        """
        try:
            inputCmds = ['query', 'command', 'result', 'status', 'shortPoll', 'longPoll', 'delete']
            parsed_msg = json.loads(msg.payload.decode('utf-8'))
            if 'node' in parsed_msg:
                if parsed_msg['node'] != 'polyglot': return
                del parsed_msg['node']
                for key in parsed_msg:
                    #LOGGER.debug('MQTT Received Message: {}: {}'.format(msg.topic, parsed_msg))
                    if key == 'config':
                        self.inConfig(parsed_msg[key])
                    elif key == 'connected':
                        self.polyglotConnected = parsed_msg[key]
                    elif key == 'stop':
                        LOGGER.debug('Received stop from Polyglot... Shutting Down.')
                        self.stop()
                    elif key in inputCmds:
                        self.input(parsed_msg)
                    else:
                        LOGGER.error('Invalid command received in message from Polyglot: {}'.format(key))

        except (ValueError) as err:
            LOGGER.error('MQTT Received Payload Error: {}'.format(err), exc_info=True)

    def _disconnect(self, mqttc, userdata, rc):
        """
        The callback for when a DISCONNECT occurs.

        :param mqttc: The client instance for this callback
        :param userdata: The private userdata for the mqtt client. Not used in Polyglot
        :param rc: Result code of connection, 0 = Graceful, anything else is unclean
        """
        self.connected = False
        if rc != 0:
            LOGGER.info("MQTT Unexpected disconnection. Trying reconnect.")
            try:
                self._mqttc.reconnect()
            except Exception as ex:
                template = "An exception of type {0} occured. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                LOGGER.error("MQTT Connection error: " + message)
        else:
            LOGGER.info("MQTT Graceful disconnection.")

    def _log(self, mqttc, userdata, level, string):
        """ Use for debugging MQTT Packets, disable for normal use, NOISY. """
        #LOGGER.info('MQTT Log - {}: {}'.format(str(level), str(string)))
        pass

    def _subscribe(self, mqttc, userdata, mid, granted_qos):
        """ Callback for Subscribe message. Unused currently. """
        # LOGGER.info("MQTT Subscribed Succesfully for Message ID: {} - QoS: {}".format(str(mid), str(granted_qos)))
        pass

    def _publish(self, mqttc, userdata, mid):
        """ Callback for publish message. Unused currently. """
        #LOGGER.info("MQTT Published message ID: {}".format(str(mid)))
        pass

    def start(self):
        """
        The client start method. Starts the thread for the MQTT Client
        and publishes the connected message.
        """
        LOGGER.info('Connecting to MQTT... {}:{}'.format(self._server, self._port))
        try:
            #self._mqttc.connect_async(str(self._server), int(self._port), 10)
            self._mqttc.connect('{}'.format(self._server), int(self._port))
            self._mqttc.loop_start()
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            LOGGER.error("MQTT Connection error: {}".format(message), exc_info=True)

    def stop(self):
        """
        The client stop method. If the client is currently connected
        stop the thread and disconnect. Publish the disconnected
        message if clean shutdown.
        """
        #self.loop.call_soon_threadsafe(self.loop.stop)
        #self.loop.stop()
        #self._longPoll.cancel()
        #self._shortPoll.cancel()
        if self.connected:
            LOGGER.info('Disconnecting from MQTT... {}:{}'.format(self._server, self._port))
            self._mqttc.publish(self.topicSelfConnection, json.dumps({'node': self.profileNum, 'connected': False}), retain = True)
            self._mqttc.loop_stop()
            self._mqttc.disconnect()
        try:
            for watcher in self.__stopObservers:
                watcher()
        except KeyError as e:
            LOGGER.exception('KeyError in gotConfig: {}'.format(e), exc_info=True)

    def send(self, message):
        """
        Formatted Message to send to Polyglot. Connection messages are sent automatically from this module
        so this method is used to send commands to/from Polyglot and formats it for consumption
        """
        if not isinstance(message, dict) and self.connected:
            warnings.warn('payload not a dictionary')
            return False
        try:
            message['node'] = self.profileNum
            self._mqttc.publish(self.topicInput, json.dumps(message), retain = False)
        except TypeError as err:
            LOGGER.error('MQTT Send Error: {}'.format(err), exc_info=True)

    def addNode(self, node):
        """
        Add a node to the NodeServer

        :param node: Dictionary of node settings. Keys: address, name, node_def_id, primary, and drivers are required.
        """
        LOGGER.info('Adding node {}({})'.format(node.name, node.address))
        message = {
            'addnode': {
                'nodes': [{
                    'address': node.address,
                    'name': node.name,
                    'node_def_id': node.id,
                    'primary': node.primary,
                    'drivers': node.drivers
                }]
            }
        }
        self.send(message)

    def saveCustomData(self, data):
        """
        Send custom dictionary to Polyglot to save and be retrieved on startup.

        :param data: Dictionary of key value pairs to store in Polyglot database.
        """
        LOGGER.info('Sending customData to Polyglot.')
        message = { 'customdata': data }
        self.send(message)

    def saveCustomParams(self, data):
        """
        Send custom dictionary to Polyglot to save and be retrieved on startup.

        :param data: Dictionary of key value pairs to store in Polyglot database.
        """
        LOGGER.info('Sending customParams to Polyglot.')
        message = { 'customparams': data }
        self.send(message)

    def addNotice(self, data):
        """
        Add custom notice to front-end for this NodeServers

        :param data: String of characters to add as a notification in the front-end.
        """
        LOGGER.info('Sending addnotice to Polyglot: {}'.format(data))
        message = { 'addnotice': data }
        self.send(message)

    def removeNotice(self, data):
        """
        Add custom notice to front-end for this NodeServers

        :param data: Index of notices list to remove.
        """
        LOGGER.info('Sending removenotice to Polyglot for index {}'.format(data))
        message = { 'removenotice': data }
        self.send(message)

    def restart(self):
        """
        Send a command to Polyglot to restart this NodeServer
        """
        LOGGER.info('Asking Polyglot to restart me.')
        message = {
            'restart': {}
        }
        self.send(message)

    def installprofile(self):
        LOGGER.info('Sending Install Profile command to Polyglot.')
        message = { 'installprofile': { 'reboot': False } }
        self.send(message)

    def delNode(self, address):
        """
        Delete a node from the NodeServer

        :param node: Dictionary of node settings. Keys: address, name, node_def_id, primary, and drivers are required.
        """
        LOGGER.info('Removing node {}'.format(address))
        message = {
            'removenode': {
                'address': address
            }
        }
        self.send(message)

    def getNode(self, address):
        """
        Get Node by Address of existing nodes.
        """
        try:
            for node in self.config['nodes']:
                if node['address'] == address:
                    return node
            return False
        except KeyError as e:
            LOGGER.error('Usually means we have not received the config yet.', exc_info=True)
            return False

    def inConfig(self, config):
        """
        Save incoming config received from Polyglot to Interface.config and then do any functions
        that are waiting on the config to be received.
        """
        self.config = config
        self.isyVersion = config['isyVersion']
        try:
            for watcher in self.__configObservers:
                watcher(config)
        except KeyError as e:
            LOGGER.error('KeyError in gotConfig: {}'.format(e), exc_info=True)

    def input(self, command):
        self.inQueue.put(command)

class Node(object):
    """
    Node Class for individual devices.
    """
    def __init__(self, controller, primary, address, name):
        try:
            self.controller = controller
            self.parent = self.controller
            self.primary = primary
            self.address = address
            self.name = name
            self.polyConfig = None
            self.drivers = deepcopy(self.drivers)
            self._drivers = deepcopy(self.drivers)
            self.isPrimary = None
            self.config = None
            self.timeAdded = None
            self.enabled = None
            self.added = None
        except (KeyError) as err:
            LOGGER.error('Error Creating node: {}'.format(err), exc_info=True)

    def setDriver(self, driver, value, report = True, force = False):
        for d in self.drivers:
            if d['driver'] == driver:
                d['value'] = value
                if report:
                    self.reportDriver(d, report, force)
                break

    def reportDriver(self, driver, report, force):
        for d in self._drivers:
            if d['driver'] == driver['driver'] and (d['value'] != str(driver['value']) or force):
                LOGGER.info('Updating Driver {} - {}: {}'.format(self.address, driver['driver'], driver['value']))
                d['value'] = deepcopy(driver['value'])
                message = {
                    'status': {
                        'address': self.address,
                        'driver': driver['driver'],
                        'value': str(driver['value']),
                        'uom': driver['uom']
                    }
                }
                self.controller.poly.send(message)
                break

    def reportCmd(self, command, value=None, uom=None):
        message = {
            'command': {
                'address': self.address,
                'command': command
            }
        }
        if value is not None and uom is not None:
            message['command']['value'] = str(value)
            message['command']['uom'] = uom
        self.controller.poly.send(message)

    def reportDrivers(self):
        LOGGER.info('Updating All Drivers to ISY for {}({})'.format(self.name, self.address))
        self.updateDrivers(self.drivers)
        for driver in self.drivers:
            message = {
                'status': {
                    'address': self.address,
                    'driver': driver['driver'],
                    'value': driver['value'],
                    'uom': driver['uom']
                }
            }
            self.controller.poly.send(message)

    def updateDrivers(self, drivers):
        self._drivers = deepcopy(drivers)

    def query(self):
        self.reportDrivers()

    def status(self):
        self.reportDrivers()

    def runCmd(self, command):
        if command['cmd'] in self.commands:
            fun = self.commands[command['cmd']]
            fun(self, command)

    def start(self):
        pass

    def getDriver(self, dv):
        for index, node in enumerate(self.controller.poly.config['nodes']):
            if node['address'] == self.address:
                for index, driver in enumerate(node['drivers']):
                    if driver['driver'] == dv:
                        return driver['value']
        return None

    def toJSON(self):
        LOGGER.debug(json.dumps(self.__dict__))

    def __rep__(self):
        return self.toJSON()

    id = ''
    commands = {}
    drivers = []
    sends = {}

class Controller(Node):
    """
    Controller Class for controller management. Superclass of Node
    """
    __exists = False

    def __init__(self, poly):
        if self.__exists:
            warnings.warn('Only one Controller is allowed.')
            return
        try:
            self.controller = self
            self.parent = self.controller
            self.poly = poly
            self.poly.onConfig(self._gotConfig)
            self.poly.onStop(self.stop)
            self.name = 'Controller'
            self.address = 'controller'
            self.primary = self.address
            self._drivers = deepcopy(self.drivers)
            self._nodes = {}
            self.config = None
            self.nodes = { self.address: self }
            self.polyConfig = None
            self.isPrimary = None
            self.timeAdded = None
            self.enabled = None
            self.added = None
            self.started = False
            self.nodesAdding = []
            self._threads = []
            self._startThreads()
        except (KeyError) as err:
            LOGGER.error('Error Creating node: {}'.format(err), exc_info=True)

    def _gotConfig(self, config):
        self.polyConfig = config
        for node in config['nodes']:
            self._nodes[node['address']] = node
            if node['address'] in self.nodes:
                n = self.nodes[node['address']]
                n.updateDrivers(node['drivers'])
                n.config = node
                n.isPrimary = node['isprimary']
                n.timeAdded = node['timeAdded']
                n.enabled = node['enabled']
                n.added = node['added']
        if not self.address in self._nodes:
            self.addNode(self)
            LOGGER.info('Waiting on Controller node to be added.......')
        if not self.started:
            self.nodes[self.address] = self
            self.started = True
            self.setDriver('ST', 1, True, True)
            self.start()

    def _startThreads(self):
        for i in range(1):
            t = Thread(target=self._parseInput)
            t.daemon = True
            t.start()
            self._threads.append(t)

    def _parseInput(self):
        while True:
            input = self.poly.inQueue.get()
            for key in input:
                if key == 'command':
                    try:
                        self.nodes[input[key]['address']].runCmd(input[key])
                    except KeyError as err:
                        LOGGER.error('_parseInput: {}, received command for the node that is not in memory: {}'.format(err, input[key]['address']))
                elif key == 'result':
                    self._handleResult(input[key])
                elif key == 'delete':
                    self._delete()
                elif key == 'shortPoll':
                    self.shortPoll()
                elif key == 'longPoll':
                    self.longPoll()
                elif key == 'query':
                    if input[key]['address'] in self.nodes:
                        self.nodes[input[key]['address']].query()
                    elif input[key]['address'] == 'all':
                        self.query()
                elif key == 'status':
                    if input[key]['address'] in self.nodes:
                        self.nodes[input[key]['address']].status()
                    elif input[key]['address'] == 'all':
                        self.status()
            self.poly.inQueue.task_done()

    def _handleResult(self, result):
        try:
            if 'addnode' in result:
                if result['addnode']['success'] == True:
                    if not result['addnode']['address'] == self.address:
                        self.nodes[result['addnode']['address']].start()
                    self.nodes[result['addnode']['address']].reportDrivers()
                    self.nodesAdding.remove(result['addnode']['address'])
                else:
                    del self.nodes[result['addnode']['address']]
        except (KeyError, ValueError) as err:
            LOGGER.error('handleResult: {}'.format(err), exc_info=True)

    def _delete(self):
        """
        Intermediate message that stops MQTT before sending to overrideable method for delete.
        """
        self.poly.stop()
        self.delete()

    def delete(self):
        """
        Incoming delete message from Polyglot. This NodeServer is being deleted.
        You have 5 seconds before the process is killed. Cleanup and disconnect.
        """
        pass

    """
    AddNode adds the class to self.nodes then sends the request to Polyglot
    If update is True, overwrite the node in Polyglot
    """
    def addNode(self, node, update = False):
        self.nodes[node.address] = node
        if node.address not in self._nodes or update:
            self.nodesAdding.append(node.address)
            self.poly.addNode(node)
        else:
            self.nodes[node.address].start()
        return node

    """
    Same as AddNode update = True
    """
    def updateNode(self, node):
        self.nodes[node.address] = node
        self.nodesAdding.append(node.address)
        self.poly.addNode(node)

    def delNode(self, address):
        """
        Just send it along if requested, should be able to delete the node even if it isn't
        in our config anywhere. Usually used for normalization.
        """
        if address in self.nodes:
            del self.nodes[address]
        self.poly.delNode(address)

    def longPoll(self):
        pass

    def shortPoll(self):
        pass

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def status(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def runForever(self):
        for thread in self._threads:
            thread.join()

    def start(self):
        pass

    def saveCustomData(self, data):
        if not isinstance(data, dict):
            LOGGER.error('saveCustomData: data isn\'t a dictionary. Ignoring.')
        else:
            self.poly.saveCustomData(data)

    def addCustomParam(self, data):
        if not isinstance(data, dict):
            LOGGER.error('addCustomParam: data isn\'t a dictionary. Ignoring.')
        else:
            newData = deepcopy(self.poly.config['customParams'])
            newData.update(data)
            self.poly.saveCustomParams(newData)

    def removeCustomParam(self, data):
        try: # check whether python knows about 'basestring'
           basestring
        except NameError: # no, it doesn't (it's Python3); use 'str' instead
           basestring=str
        if not isinstance(data, basestring):
            LOGGER.error('removeCustomParam: data isn\'t a string. Ignoring.')
        else:
            try:
                newData = deepcopy(self.poly.config['customParams'])
                newData.pop(data)
                self.poly.saveCustomParams(newData)
            except (KeyError) as err:
                LOGGER.error('{} not found in customParams. Ignoring...'.format(data), exc_info=True)

    def getCustomParam(self, data):
        params = deepcopy(self.poly.config['customParams'])
        return params.get(data)

    def addNotice(self, data):
        try: # check whether python knows about 'basestring'
           basestring
        except NameError: # no, it doesn't (it's Python3); use 'str' instead
           basestring=str
        if not isinstance(data, basestring):
            LOGGER.error('addNotice: data isn\'t a string. Ignoring.')
        else:
            self.poly.addNotice(data)

    def removeNotice(self, data):
        if not isinstance(data, int):
            LOGGER.error('removeNotice: data isn\'t a int. Ignoring.')
        else:
            try:
                self.poly.config['notices'][data]
                self.poly.removeNotice(data)
            except (IndexError) as err:
                LOGGER.error('Notices doesn\'t have an element at index {} ignoring. {}'.format(data, err), exc_info=True)

    def getNotices(self):
        return self.poly.config['notices']

    def removeNoticesAll(self):
        if len(self.poly.config['notices']):
            for i in range(len(self.poly.config['notices'])):
                self.removeNotice(i)

    def stop(self):
        """ Called on nodeserver stop """
        pass

    id = 'controller'
    commands = {}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]


if __name__ == "__main__":
    sys.exit(0)
