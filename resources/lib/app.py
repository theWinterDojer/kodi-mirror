import xbmcaddon
import xbmcgui

from resources.lib import log
from resources.lib.destination import resolve_active_destination_state
from resources.lib.main_window import open_main_window
from resources.lib.paths import PathResolutionError, resolve_runtime_paths
from resources.lib.restore_apply import (
    RestoreApplyError,
    apply_pending_restore,
    has_pending_restore,
)


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

    if has_pending_restore(runtime_paths):
        log.info("Pending restore detected at startup")
        try:
            restore_result = apply_pending_restore(runtime_paths)
        except RestoreApplyError as exc:
            log.error(str(exc))
            xbmcgui.Dialog().ok(
                addon_name,
                "Restore apply failed.",
                str(exc),
            )
            return

        log.info("Pending restore applied successfully")
        xbmcgui.Dialog().ok(
            addon_name,
            "Restore complete.",
            f"Archive: {restore_result['archive_path']}",
            f"Files copied: {restore_result['copied_file_count']}",
            f"Paths removed: {restore_result['removed_path_count']}",
        )
        return

    destination_state = resolve_active_destination_state(addon)
    if destination_state["is_ready"]:
        log.info(
            f"Active backup destination ready ({destination_state['source']}): "
            f"{destination_state['path']}"
        )
    else:
        log.error(destination_state["error"])

    log.info("Opening main window")
    open_main_window(addon, addon_path, addon_name, runtime_paths, destination_state)
