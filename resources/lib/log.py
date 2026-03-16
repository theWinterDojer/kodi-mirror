import traceback
import logging

try:
    import xbmc
except ModuleNotFoundError:  # Plain Python validation path outside Kodi.
    xbmc = None

from resources.lib.constants import ADDON_ID


def _log(message, level_name, kodi_level=None):
    formatted = f"{ADDON_ID}: {message}"
    if xbmc is not None:
        xbmc.log(formatted, kodi_level)
        return
    logging.getLogger(ADDON_ID).log(getattr(logging, level_name), formatted)


def info(message):
    _log(message, "INFO", xbmc.LOGINFO if xbmc is not None else None)


def error(message):
    _log(message, "ERROR", xbmc.LOGERROR if xbmc is not None else None)


def debug(message):
    _log(message, "DEBUG", xbmc.LOGDEBUG if xbmc is not None else None)


def exception(message):
    error(message)
    error(traceback.format_exc().rstrip())
