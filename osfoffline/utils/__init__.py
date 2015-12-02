"""
General utilities used by the application
"""
import logging
import logging.config
import logging.handlers


def start_app_logging(config=None):
    """
    Start logging for the application
    :param config:
    :return:
    """
    # Avoids circular import
    from osfoffline import settings
    logging.config.dictConfig(config or settings.LOGGING_CONFIG)
