__version__ = '2.0.29'
__description__ = 'UDI Polyglot v2 Interface'
__url__ = 'https://github.com/UniversalDevicesInc/polyglot-v2-python-interface'
__author__ = 'James Milne'
__authoremail__ = 'milne.james@gmail.com'
__license__ = 'MIT'
__features__ = {
    "noticeByKey": "on",
    "customParamsDoc": "on",
    "typedParams": "on"
}

from .polyinterface import Interface, Node, Controller, LOGGER, unload_interface

LOGGER.info('{} {} Starting...'.format(__description__, __version__))
