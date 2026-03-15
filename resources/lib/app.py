import xbmcaddon
import xbmcgui

from resources.lib import log
from resources.lib.paths import PathResolutionError, format_runtime_paths, resolve_runtime_paths


def run():
    addon = xbmcaddon.Addon()
    addon_name = addon.getAddonInfo("name")
    addon_version = addon.getAddonInfo("version")

    log.info(f"Launching {addon_name} {addon_version}")
    try:
        runtime_paths = resolve_runtime_paths()
    except PathResolutionError as exc:
        log.error(str(exc))
        xbmcgui.Dialog().ok(addon_name, "Startup failed.", str(exc))
        return

    xbmcgui.Dialog().ok(
        addon_name,
        "Runtime paths resolved.",
        *format_runtime_paths(runtime_paths),
    )
