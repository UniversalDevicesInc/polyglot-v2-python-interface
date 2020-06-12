

from .polylogger import LOG_HANDLER,LOGGER
from .polyinterface import Interface, Node, Controller, unload_interface, get_network_interface

__version__ = '2.1.0'
__description__ = 'UDI Polyglot v2 Interface'
__url__ = 'https://github.com/UniversalDevicesInc/polyglot-v2-python-interface'
__author__ = 'James Milne'
__authoremail__ = 'milne.james@gmail.com'
__license__ = 'MIT'

LOGGER.info('{} {} Starting...'.format(__description__, __version__))
