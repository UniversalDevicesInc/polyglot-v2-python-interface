
import os
import logging
from logging import handlers as log_handlers
import warnings

class PolyLogger:

    NAME = __name__.split(".")[0]
    LOGS_DIR= './logs'
    LOG_FILE = 'debug.log'
    LEVEL = logging.DEBUG
    ROTATION = 'midnight'
    WARN_LOGGER_NAME = 'py.warnings'
    BACKUP_COUNT = 30
    FMT_STRING = '%(asctime)s %(threadName)-10s %(name)-18s %(levelname)-8s %(module)s:%(funcName)s: %(message)s'
    IS_ROOT = True

    def __init__(self):
        if not os.path.exists(PolyLogger.LOGS_DIR):
            os.makedirs(PolyLogger.LOGS_DIR)
        self.handler = log_handlers.TimedRotatingFileHandler(
            os.path.join(PolyLogger.LOGS_DIR, PolyLogger.LOG_FILE),
            when=PolyLogger.ROTATION,
            backupCount=PolyLogger.BACKUP_COUNT
        )
        logging.captureWarnings(True)
        self.set_log_format(PolyLogger.FMT_STRING)
        # Get our logger for everyone to use.
        self.logger = logging.getLogger(PolyLogger.NAME)
        # Set the root logger name to our name
        self.logger.propagate = False # Duplicates when basicConfig is used
        self.logger.addHandler(self.handler)
        self.logger.setLevel(PolyLogger.LEVEL)
        # By default we only show warnings for others.
        self.set_basic_config(True,logging.WARNING)
        self.warnlog = logging.getLogger(PolyLogger.WARN_LOGGER_NAME)
        warnings.formatwarning = self.warning_on_one_line
        self.warnlog.addHandler(self.handler)

    def set_log_format(self, fmt_string):
        # Format each log message like this
        formatter = logging.Formatter(fmt_string)
        # Attach the formatter to the handler
        self.handler.setFormatter(formatter)

    def set_basic_config(self, enable=True, level=None):
        self.logger.info('set_basic_config: enable={} level={}'.format(enable,level))
        if level is None:
            level = self.logger.getEffectiveLevel()
            self.logger.info('set_basic_config: level={}'.format(level))
        # Remove all handlers associated with the root logger object.
        # Once everyone is on Python 3.8 we could use basicConfig force
        # option instead
        # https://stackoverflow.com/questions/12158048/changing-loggings-basicconfig-which-is-already-set#12158233
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        # Attach the handler to the logger
        if enable:
            logging.basicConfig(
                handlers=[self.handler],
                level=level,
                )

    @staticmethod
    def warning_on_one_line(message, category, filename, lineno, file=None, line=None):
        return '{}:{}: {}: {}'.format(filename, lineno, category.__name__, message)

LOG_HANDLER = PolyLogger()
LOGGER = LOG_HANDLER.logger
