#!/usr/bin/env python
"""
Python Interface for UDI Polyglot v2 NodeServers
by Einstein.42 (James Milne) milne.james@gmail.com
"""

from copy import deepcopy
from dotenv import load_dotenv
import json
import ssl
import logging
import logging.handlers
import __main__ as main
import markdown2
import os
from os.path import join, expanduser
import paho.mqtt.client as mqtt
try:
    import queue
except ImportError:
    import Queue as queue
import re
import sys
import select
from threading import Thread
import warnings

from polyinterface import __features__


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
    # path = os.path.dirname(sys.argv[0])
    if not os.path.exists('./logs'):
        os.makedirs('./logs')
    log_filename = "./logs/debug.log"
    log_level = logging.DEBUG  # Could be e.g. "DEBUG" or "WARNING"

    # ### Logging Section ################################################################################
    logging.captureWarnings(True)
    logger = logging.getLogger(__name__)
    logger.propagate = False
    warnlog = logging.getLogger('py.warnings')
    warnings.formatwarning = warning_on_one_line
    logger.setLevel(log_level)
    # Set the log level to LOG_LEVEL
    # Make a handler that writes to a file,
    # making a new file at midnight and keeping 3 backups
    handler = logging.handlers.TimedRotatingFileHandler(log_filename, when="midnight", backupCount=30)
    # Format each log message like this
    formatter = logging.Formatter('%(asctime)s [%(threadName)-10s] [%(levelname)-5s] %(message)s')
    # Attach the formatter to the handler
    handler.setFormatter(formatter)
    # Attach the handler to the logger
    logger.addHandler(handler)
    warnlog.addHandler(handler)
    return logger

LOGGER = setup_log()


def init_interface():
    sys.stdout = LoggerWriter(LOGGER.debug)
    sys.stderr = LoggerWriter(LOGGER.error)

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
            # e = sys.exc_info()[0]
            LOGGER.error('Invalid formatted input. Skipping. %s', err, exc_info=True)


def unload_interface():
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    LOGGER.handlers = []


class Interface(object):

    CUSTOM_CONFIG_DOCS_FILE_NAME = 'POLYGLOT_CONFIG.md'

    """
    Polyglot Interface Class

    :param envVar: The Name of the variable from ~/.polyglot/.env that has this NodeServer's profile number
    """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=unused-argument

    __exists = False

    def __init__(self, envVar=None):
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
        self._threads = {}
        self._threads['socket'] = Thread(target = self._startMqtt, name = 'Interface')
        self._mqttc = mqtt.Client(envVar, True)
        # self._mqttc.will_set(self.topicSelfConnection, json.dumps({'node': self.profileNum, 'connected': False}), retain=True)
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
            if 'MQTT_CERTPATH' in os.environ:
                self._mqttc.tls_set(
                    ca_certs=os.environ['MQTT_CERTPATH'] + '/polyglot.crt',
                    certfile=os.environ['MQTT_CERTPATH'] + '/client.crt',
                    keyfile=os.environ['MQTT_CERTPATH'] + '/client_private.key',
                    tls_version=ssl.PROTOCOL_TLSv1_2)
            else:
                self._mqttc.tls_set(
                    ca_certs=join(expanduser("~") + '/.polyglot/ssl/polyglot.crt'),
                    certfile=join(expanduser("~") + '/.polyglot/ssl/client.crt'),
                    keyfile=join(expanduser("~") + '/.polyglot/ssl/client_private.key'),
                    tls_version=ssl.PROTOCOL_TLSv1_2
                    )
        # self._mqttc.tls_insecure_set(True)
        # self._mqttc.enable_logger(logger=LOGGER)
        self.config = None
        # self.loop = asyncio.new_event_loop()
        self.loop = None
        self.inQueue = queue.Queue()
        # self.thread = Thread(target=self.start_loop)
        self.isyVersion = None
        self._server = os.environ.get("MQTT_HOST") or 'localhost'
        self._port = os.environ.get("MQTT_PORT") or '1883'
        self.polyglotConnected = False
        self.__configObservers = []
        self.__stopObservers = []
        Interface.__exists = True
        self.custom_params_docs_file_sent = False
        self.custom_params_pending_docs = ''

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
            self._mqttc.publish(self.topicSelfConnection, json.dumps(
                {
                    'connected': True,
                    'node': self.profileNum,
                    'features': __features__
                }), retain=True)
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
                if parsed_msg['node'] != 'polyglot':
                    return
                del parsed_msg['node']
                for key in parsed_msg:
                    # LOGGER.debug('MQTT Received Message: {}: {}'.format(msg.topic, parsed_msg))
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
        # LOGGER.info('MQTT Log - {}: {}'.format(str(level), str(string)))
        pass

    def _subscribe(self, mqttc, userdata, mid, granted_qos):
        """ Callback for Subscribe message. Unused currently. """
        # LOGGER.info("MQTT Subscribed Succesfully for Message ID: {} - QoS: {}".format(str(mid), str(granted_qos)))
        pass

    def _publish(self, mqttc, userdata, mid):
        """ Callback for publish message. Unused currently. """
        # LOGGER.info("MQTT Published message ID: {}".format(str(mid)))
        pass

    def start(self):
        for _, thread in self._threads.items():
            thread.start()

    def _startMqtt(self):
        """
        The client start method. Starts the thread for the MQTT Client
        and publishes the connected message.
        """
        LOGGER.info('Connecting to MQTT... {}:{}'.format(self._server, self._port))
        try:
            # self._mqttc.connect_async(str(self._server), int(self._port), 10)
            self._mqttc.connect_async('{}'.format(self._server), int(self._port), 10)
            self._mqttc.loop_forever()
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
        # self.loop.call_soon_threadsafe(self.loop.stop)
        # self.loop.stop()
        # self._longPoll.cancel()
        # self._shortPoll.cancel()
        if self.connected:
            LOGGER.info('Disconnecting from MQTT... {}:{}'.format(self._server, self._port))
            self._mqttc.publish(self.topicSelfConnection, json.dumps({'node': self.profileNum, 'connected': False}), retain=True)
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
            self._mqttc.publish(self.topicInput, json.dumps(message), retain=False)
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
        except KeyError:
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

            self.send_custom_config_docs()

        except KeyError as e:
            LOGGER.error('KeyError in gotConfig: {}'.format(e), exc_info=True)

    def input(self, command):
        self.inQueue.put(command)

    def supports_feature(self, feature):
        if self.config is None:
            return False

        feature_support = self.config.get('features', {}).get(feature, 'off')
        if feature_support == 'deprecated':
            LOGGER.warning('Deprecated feature detected {}. Update interface and node server.'.format(feature))
            return True

        return feature_support == 'on'

    def get_md_file_data(self, fileName):
        data = ''
        if os.path.isfile(fileName):
            data = markdown2.markdown_path(fileName)

        return data

    def send_custom_config_docs(self):
        if not self.supports_feature('customParamsDoc'):
            return

        data = ''
        if not self.custom_params_docs_file_sent:
            data = self.get_md_file_data(Interface.CUSTOM_CONFIG_DOCS_FILE_NAME)
        else:
            data = self.config.get('customParamsDoc', '')

        # send if we're sending new file or there are updates
        if (not self.custom_params_docs_file_sent or
            len(self.custom_params_pending_docs) > 0):
            data += self.custom_params_pending_docs
            self.custom_params_docs_file_sent = True
            self.custom_params_pending_docs = ''

            self.config['customParamsDoc'] = data
            self.send({ 'customparamsdoc': data })

    def add_custom_config_docs(self, data, clearCurrentData=False):
        if clearCurrentData:
            self.custom_params_docs_file_sent = False

        self.custom_params_pending_docs += data
        self.send_custom_config_docs()

    def save_typed_params(self, data):
        """
        Send custom parameters descriptions to Polyglot to be used
        in front end UI configuration screen
        Accepts list of objects with the followin properties
            name - used as a key when data is sent from UI
            title - displayed in UI
            defaultValue - optionanl
            type - optional, can be 'NUMBER', 'STRING' or 'BOOLEAN'.
                Defaults to 'STRING'
            desc - optional, shown in tooltip in UI
            isRequired - optional, True/False, when set, will not validate UI
                input if it's empty
            isList - optional, True/False, if set this will be treated as list
                of values or objects by UI
            params - optional, can contain a list of objects. If present, then
                this (parent) is treated as object / list of objects by UI,
                otherwise, it's treated as a single / list of single values
        """
        LOGGER.info('Sending typed parameters to Polyglot.')
        if type(data) is not list:
            data = [ data ]
        message = { 'typedparams': data }
        self.send(message)


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

    def _convertDrivers(self, drivers):
        return deepcopy(drivers)
        """
        if isinstance(drivers, list):
            newFormat = {}
            for driver in drivers:
                newFormat[driver['driver']] = {}
                newFormat[driver['driver']]['value'] = driver['value']
                newFormat[driver['driver']]['uom'] = driver['uom']
            return newFormat
        else:    
            return deepcopy(drivers)
        """

    def setDriver(self, driver, value, report=True, force=False, uom=None):
        for d in self.drivers:
            if d['driver'] == driver:
                d['value'] = value
                if uom is not None:
                    d['uom'] = uom
                if report:
                    self.reportDriver(d, report, force)
                break

    def reportDriver(self, driver, report, force):
        for d in self._drivers:
            if (d['driver'] == driver['driver'] and
                (str(d['value']) != str(driver['value']) or
                    d['uom'] != driver['uom'] or
                    force)):
                LOGGER.info('Updating Driver {} - {}: {}, uom: {}'.format(self.address, driver['driver'], driver['value'], driver['uom']))
                d['value'] = deepcopy(driver['value'])
                if d['uom'] != driver['uom']:
                    d['uom'] = deepcopy(driver['uom'])
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
            self._threads = {}
            self._threads['input'] = Thread(target = self._parseInput, name = 'Controller')
            self._threads['ns']  = Thread(target = self.start, name = 'NodeServer')
            self.polyConfig = None
            self.isPrimary = None
            self.timeAdded = None
            self.enabled = None
            self.added = None
            self.started = False
            self.nodesAdding = []
            # self._threads = []
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
        if self.address not in self._nodes:
            self.addNode(self)
            LOGGER.info('Waiting on Controller node to be added.......')
        if not self.started:
            self.nodes[self.address] = self
            self.started = True
            # self.setDriver('ST', 1, True, True)
            self._threads['ns'].start()

    def _startThreads(self):
        self._threads['input'].daemon = True
        self._threads['ns'].daemon = True
        self._threads['input'].start()

    def _parseInput(self):
        while True:
            input = self.poly.inQueue.get()
            for key in input:
                if key == 'command':
                    if input[key]['address'] in self.nodes:
                        try:
                            self.nodes[input[key]['address']].runCmd(input[key])
                        except (Exception) as err:
                            LOGGER.error('_parseInput: failed {}.runCmd({}) {}'.format(input[key]['address'], input[key]['cmd'], err), exc_info=True)
                    else:
                        LOGGER.error('_parseInput: received command {} for a node that is not in memory: {}'.format(input[key]['cmd'], input[key]['address']))
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
        # LOGGER.debug(self.nodesAdding)
        try:
            if 'addnode' in result:
                if result['addnode']['success']:
                    if not result['addnode']['address'] == self.address:
                        self.nodes[result['addnode']['address']].start()
                    # self.nodes[result['addnode']['address']].reportDrivers()
                    if result['addnode']['address'] in self.nodesAdding:
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

    def _convertDrivers(self, drivers):
        return deepcopy(drivers)
        """
        if isinstance(drivers, list):
            newFormat = {}
            for driver in drivers:
                newFormat[driver['driver']] = {}
                newFormat[driver['driver']]['value'] = driver['value']
                newFormat[driver['driver']]['uom'] = driver['uom']
            return newFormat
        else:    
            return deepcopy(drivers)
        """

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
    def addNode(self, node, update=False):
        if node.address in self._nodes:
            node._drivers = self._nodes[node.address]['drivers']
            for driver in node.drivers:
                for existing in self._nodes[node.address]['drivers']:
                    if driver['driver'] == existing['driver']:
                        driver['value'] = existing['value']
                        # JIMBO SAYS NO
                        # driver['uom'] = existing['uom']
        self.nodes[node.address] = node
        # if node.address not in self._nodes or update:
        self.nodesAdding.append(node.address)
        self.poly.addNode(node)
        # else:
        #    self.nodes[node.address].start()
        return node

    """
    Forces a full overwrite of the node
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
        self._threads['input'].join()

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
            newData = self.poly.config['customParams']
            newData.update(data)
            self.poly.saveCustomParams(newData)

    def removeCustomParam(self, data):
        try:  # check whether python knows about 'basestring'
            basestring
        except NameError:  # no, it doesn't (it's Python3); use 'str' instead
            basestring = str
        if not isinstance(data, basestring):
            LOGGER.error('removeCustomParam: data isn\'t a string. Ignoring.')
        else:
            try:
                newData = deepcopy(self.poly.config['customParams'])
                newData.pop(data)
                self.poly.saveCustomParams(newData)
            except KeyError:
                LOGGER.error('{} not found in customParams. Ignoring...'.format(data), exc_info=True)

    def getCustomParam(self, data):
        params = deepcopy(self.poly.config['customParams'])
        return params.get(data)

    def addNotice(self, data, key=None):
        if not isinstance(data, dict):
            self.poly.addNotice({ 'key': key, 'value': data})
        else:
            if 'value' in data:
                self.poly.addNotice(data)
            else:
                for key, value in data.items():
                    self.poly.addNotice({ 'key': key, 'value': value })

    def removeNotice(self, key):
        if (self.poly.supports_feature('noticeByKey')):
            data = { 'key': str(key) }
        else:
            if not isinstance(key, int):
                LOGGER.error('removeNotice: key isn\'t a int. Ignoring.')
                return
            try:
                data = self.poly.config['notices'][key]
            except (IndexError) as err:
                LOGGER.error('Notices doesn\'t have an element at index {} ignoring. {}'.format(data, err), exc_info=True)
                return
        self.poly.removeNotice(data)

    def getNotices(self):
        return self.poly.config['notices']

    def removeNoticesAll(self):
        if type(self.poly.config['notices']) == dict:
            for key in self.poly.config['notices'].keys():
                self.removeNotice(key)
        else:
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

if hasattr(main, '__file__'):
    init_interface()
