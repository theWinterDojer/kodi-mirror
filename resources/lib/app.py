import xbmcaddon
import xbmcgui

from resources.lib import log
from resources.lib.destination import resolve_default_destination_state
from resources.lib.main_window import open_main_window
from resources.lib.paths import PathResolutionError, resolve_runtime_paths


def run():
    addon = xbmcaddon.Addon()
    addon_name = addon.getAddonInfo("name")
    addon_version = addon.getAddonInfo("version")
    addon_path = addon.getAddonInfo("path")

    log.info(f"Launching {addon_name} {addon_version}")
    try:
        runtime_paths = resolve_runtime_paths()
    except PathResolutionError as exc:
        log.error(str(exc))
        xbmcgui.Dialog().ok(addon_name, "Startup failed.", str(exc))
        return

    destination_state = resolve_default_destination_state()
    if destination_state["is_ready"]:
        log.info(f"Default backup destination ready: {destination_state['path']}")
    else:
        log.error(destination_state["error"])

    log.info("Opening main window")
    open_main_window(addon_path, addon_name, runtime_paths, destination_state)
