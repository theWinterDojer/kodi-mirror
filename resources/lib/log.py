import xbmc

from resources.lib.constants import ADDON_ID


def info(message):
    xbmc.log(f"{ADDON_ID}: {message}", xbmc.LOGINFO)


def error(message):
    xbmc.log(f"{ADDON_ID}: {message}", xbmc.LOGERROR)
