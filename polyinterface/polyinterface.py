#!/bin/python3
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
import queue
import asyncio
from os.path import join, expanduser
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from threading import Thread, Timer
from copy import deepcopy

def warning_on_one_line(message, category, filename, lineno, file=None, line=None):
    return '{}:{}: {}: {}'.format(filename, lineno, category.__name__, message)

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

LOGGER.info('Polyglot v2 Interface Starting...')
"""
Grab the ~/.polyglot/.env file for variables
If you are running Polyglot v2 on this same machine
then it should already exist. If not create it.
"""
warnings.simplefilter('error', UserWarning)
try:
    load_dotenv(join(expanduser("~") + '/.polyglot/.env'))
except (UserWarning) as e:
    LOGGER.warning('File does not exist: {}.'.format(join(expanduser("~") + '/.polyglot/.env')))
    # sys.exit(1)
warnings.resetwarnings()

init = select.select([sys.stdin], [], [], 1)[0]
if init:
    line = sys.stdin.readline()
    try:
        line = json.loads(line)
        os.environ['PROFILE_NUM'] = line['profileNum']
        os.environ['MQTT_HOST'] = line['mqttHost']
        os.environ['MQTT_PORT'] = line['mqttPort']
        LOGGER.info('Received Config from STDIN.')
    except:
        e = sys.exc_info()[0]
        LOGGER.debug('Invalid formatted input. Skipping. {}'.format(e))

class Interface:
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
            self.profileNum = os.environ.get(envVar)
        if self.profileNum is None:
            LOGGER.error('Profile Number not found in STDIN or .env file. Exiting.')
            sys.exit(1)
        self.profileNum = str(self.profileNum)
        self.topicPolyglotConnection = 'udi/polyglot/connections/polyglot'
        self.topicInput = 'udi/polyglot/ns/{}'.format(self.profileNum)
        self.topicSelfConnection = 'udi/polyglot/connections/{}'.format(self.profileNum)
        self._mqttc = mqtt.Client(envVar, True)
        self._mqttc.will_set(self.topicSelfConnection, json.dumps({'node': self.profileNum, 'connected': False}), retain=True)
        self._mqttc.on_connect = self._connect
        self._mqttc.on_message = self._message
        self._mqttc.on_subscribe = self._subscribe
        self._mqttc.on_disconnect = self._disconnect
        self._mqttc.on_publish = self._publish
        self._mqttc.on_log = self._log
        self.config = None
        self.loop = asyncio.new_event_loop()
        self.inQueue = queue.Queue()
        #self.thread = Thread(target=self.start_loop)
        self._longPoll = None
        self._shortPoll = None
        self.isyVersion = None
        self._server = os.environ.get("MQTT_HOST") or '127.0.0.1'
        self._port = os.environ.get("MQTT_PORT") or '1883'
        self.polyglotConnected = False
        self.__configObservers = []
        Interface.__exists = True

    def bind_toConfig(self, callback):
        """
        Gives the ability to bind any methods to be run when the config is received.
        """
        self.__configObservers.append(callback)

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
            #LOGGER.debug(msg.payload.decode('utf-8'))
            parsed_msg = json.loads(msg.payload.decode('utf-8'))
            if parsed_msg['node'] == self.profileNum: return
            del parsed_msg['node']
            for key in parsed_msg:
                #LOGGER.debug('MQTT Received Message: {}: {}'.format(msg.topic, parsed_msg))
                if key == 'config':
                    self.inConfig(parsed_msg[key])
                elif key == 'status' or key == 'query' or key == 'command' or key == 'result':
                    self.input(parsed_msg)
                elif key == 'connected':
                    self.polyglotConnected = parsed_msg[key]
                else:
                    LOGGER.error('Invalid command received in message from Polyglot: {}'.format(key))

        except (ValueError, json.decoder.JSONDecodeError) as err:
            LOGGER.error('MQTT Received Payload Error: {}'.format(err))

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
        # LOGGER.info('MQTT Log - {}: {}'.format(str(level), str(string)))
        pass

    def _subscribe(self, mqttc, userdata, mid, granted_qos):
        """ Callback for Subscribe message. Unused currently. """
        # LOGGER.info("MQTT Subscribed Succesfully for Message ID: {} - QoS: {}".format(str(mid), str(granted_qos)))
        pass

    def _publish(self, mqttc, userdata, mid):
        """ Callback for publish message. Unused currently. """
        #LOGGER.info("MQTT Published message ID: {}".format(str(mid)))
        pass

    """
    def start(self):
        # Start the asyncio thread
        self.thread.daemon = True
        self.thread.start()
    """

    def start(self):
        """ Start the asyncio event loop """
        #self.loop.create_task(self._start())
        self.loop.run_until_complete(self._start())

    async def _start(self):
        """
        The client start method. Starts the thread for the MQTT Client
        and publishes the connected message.
        """
        LOGGER.info('Connecting to MQTT... {}:{}'.format(self._server, self._port))
        try:
            self._mqttc.connect_async(str(self._server), int(self._port), 10)
            self._mqttc.loop_start()
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            LOGGER.error("MQTT Connection error: {}".format(message))

    def stop(self):
        """
        The client stop method. If the client is currently connected
        stop the thread and disconnect. Publish the disconnected
        message if clean shutdown.
        """
        #self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop.stop()
        self._longPoll.cancel()
        self._shortPoll.cancel()
        if self.connected:
            LOGGER.info('Disconnecting from MQTT... {}:{}'.format(self._server, self._port))
            self._mqttc.publish(self.topicSelfConnection, json.dumps({'node': self.profileNum, 'connected': False}), retain = True)
            self._mqttc.loop_stop()
            self._mqttc.disconnect()

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
            # LOGGER.debug(message)
            self._mqttc.publish(self.topicInput, json.dumps(message), retain = False)
        except TypeError as err:
            LOGGER.error('MQTT Send Error: {}'.format(err))

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
                    'node_def_id': node.node_def_id,
                    'primary': node.primary,
                    'drivers': node.drivers
                }]
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
            LOGGER.error('Usually means we have not received the config yet.')
            return False

    def inConfig(self, config):
        """
        Save incoming config received from Polyglot to Interface.config and then do any functions
        that are waiting on the config to be received.
        """
        self.config = config
        try:
            for callback in self.__configObservers:
                callback(config)
        except KeyError as e:
            LOGGER.error('Could not find Nodes in Config')

    def input(self, command):
        self.inQueue.put(command)

class Node:
    """
    Node Class for individual devices.
    """
    def __init__(self, parent, primary, address, name):
        try:
            self.parent = parent
            self.primary = primary
            self.address = address
            self.name = name
            self.polyConfig = None
            self._drivers = deepcopy(self.drivers)
            self.isPrimary = None
            self.timeAdded = None
            self.enabled = None
            self.added = None
        except (KeyError) as err:
            LOGGER.error('Error Creating node: {}'.format(err))

    def setDriver(self, driver, value, report = True):
        for d in self.drivers:
            if d['driver'] == driver:
                d['value'] = value
                if report:
                    self.reportDriver(d, report)
                break

    def reportDriver(self, driver, report):
        for d in self._drivers:
            if d['driver'] == driver['driver'] and d['value'] != driver['value']:
                LOGGER.info('Updating Driver {} - {}: {}'.format(self.address, driver['driver'], driver['value']))
                d['value'] = deepcopy(driver['value'])
                message = {
                    'status': {
                        'address': self.address,
                        'driver': driver['driver'],
                        'value': driver['value'],
                        'uom': driver['uom']
                    }
                }
                self.parent.poly.send(message)
                break

    def reportDrivers(self):
        LOGGER.info('Updating All Drivers to ISY for {}({})'.format(self.name, self.address))
        for driver in self.drivers:
            message = {
                'status': {
                    'address': self.address,
                    'driver': driver['driver'],
                    'value': driver['value'],
                    'uom': driver['uom']
                }
            }
            self.parent.poly.send(message)

    def updateDrivers(self, drivers):
        self._drivers = deepcopy(drivers)

    def runCmd(self, command):
        if command['cmd'] in self._commands:
            fun = self._commands[command['cmd']]
            fun(self, command)

    def toJSON(self):
        LOGGER.debug(json.dumps(self.__dict__))

    def __rep__(self):
        return self.toJSON()

    _commands = {}
    node_def_id = ''
    _sends = {}
    _drivers = []

class Controller:
    """
    Controller Class for controller management.
    """
    def __init__(self, poly):
        try:
            self.poly = poly
            self.poly.bind_toConfig(self._gotConfig)
            self.name = None
            self.address = None
            self.nodes = {}
            self.polyNodes = None
            self.polyConfig = None
            self.nodesAdding = []
        except (KeyError) as err:
            LOGGER.error('Error Creating node: {}'.format(err))

    def addNode(self, node):
        if not self.poly.getNode(node.address):
            self.nodesAdding.append(node.address)
            self.poly.addNode(node)
        else:
            self.nodes[node.address].start()

    def _gotConfig(self, config):
        self.polyConfig = config
        self.poly.isyVersion = config['isyVersion']
        for node in config['nodes']:
            if node['address'] in self.nodes:
                n = self.nodes[node['address']]
                n.updateDrivers(node['drivers'])
                n.polyConfig = node
                n.isPrimary = node['isprimary']
                n.timeAdded = node['time_added']
                n.enabled = node['enabled']
                n.added = node['added']
        if not self.poly.getNode(self.address):
            self.addNode(self)
            LOGGER.info('Waiting on Primary node to be added.......')
        elif not self.started:
            self.started = True
            self.start()

    def parseInput(self, input):
        for key in input:
            if key == 'command':
                try:
                    self.nodes[input[key]['address']].runCmd(input[key])
                except KeyError as e:
                    LOGGER.error('parseInput: {}'.format(e))
            elif key == 'result':
                self._handleResult(input[key])

    def _handleResult(self, result):
        try:
            if 'addnode' in result:
                if result['addnode']['success'] == True:
                    if result['addnode']['address'] == self.address:
                        self.start()
                    else:
                        self.nodes[result['addnode']['address']].start()
                    self.nodesAdding.remove(result['addnode']['address'])
        except KeyError as e:
            LOGGER.error('handleResult: {}'.format(e))

    def start(self):
        pass

    def startPolls(self, long = 30, short = 10):
        Timer(long, self.longPoll, args = []).start()
        Timer(short, self.shortPoll, args = []).start()

    def longPoll(self, timer = 30):
        self.poly._longPoll = Timer(timer, self.longPoll, args = [timer]).start()

    def shortPoll(self, timer = 10):
        self.poly._shortPoll = Timer(timer, self.shortPoll, args = [timer]).start()

    def toJSON(self):
        LOGGER.debug(json.dumps(self.__dict__))

    def __rep__(self):
        return self.toJSON()
