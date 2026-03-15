import xbmcaddon
import xbmcgui

from resources.lib import log


def run():
    addon = xbmcaddon.Addon()
    addon_name = addon.getAddonInfo("name")
    addon_version = addon.getAddonInfo("version")

    log.info(f"Launching {addon_name} {addon_version}")
    xbmcgui.Dialog().ok(
        addon_name,
        "Backup and restore are not implemented yet.",
        "Baseline addon skeleton is in place.",
    )
