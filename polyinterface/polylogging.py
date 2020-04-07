
import logging,os,warnings
import logging.handlers


def warning_on_one_line(message, category, filename, lineno, file=None, line=None):
    return '{}:{}: {}: {}'.format(filename, lineno, category.__name__, message)

# Make a handler that writes to a file,
# Log Location
# path = os.path.dirname(sys.argv[0])
if not os.path.exists('./logs'):
    os.makedirs('./logs')
# making a new file at midnight and keeping 3 backups
# this is global because we add it to basicConfig, so when set_log_format
# is called we just want to modify our handler, not recreate it each time.
_handler = logging.handlers.TimedRotatingFileHandler("./logs/debug.log", when="midnight", backupCount=30)
def set_log_format(fmt_string='%(asctime)s %(threadName)-10s %(name)-18s %(levelname)-8s %(module)s:%(funcName)s: %(message)s'):
    # Format each log message like this
    formatter = logging.Formatter(fmt_string)
    # Attach the formatter to the handler
    _handler.setFormatter(formatter)

def setup_log(logger):
    # Don't need to do it again...
    if logger.hasHandlers():
        return
    # ### Logging Section ################################################################################
    logging.captureWarnings(True)
    set_log_format()
    # Attach the handler to the logger
    logging.basicConfig(
        handlers=[_handler],
        level=logging.DEBUG
    )
    logger.propagate = False # If True we get duplicates?
    warnlog = logging.getLogger('py.warnings')
    warnings.formatwarning = warning_on_one_line
    logger.addHandler(_handler)
    warnlog.addHandler(_handler)
