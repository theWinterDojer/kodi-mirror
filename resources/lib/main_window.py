import xbmcgui

from resources.lib.backup_manifest import (
    ARCHIVE_MANIFEST_NAME,
    BackupManifestError,
    build_backup_manifest,
)
from resources.lib.backup_preflight import BackupPreflightError, run_backup_preflight
from resources.lib.cleanup import (
    CleanupError,
    build_cleanup_selections,
    format_cleanup_selections,
    run_cleanup,
)
from resources.lib.destination import DestinationError, save_selected_backup_destination
from resources.lib.constants import (
    CONTROL_ID_ADDONS_PATH,
    CONTROL_ID_BACKUP_DESTINATION_PATH,
    CONTROL_ID_BACKUP_DESTINATION_STATUS,
    CONTROL_ID_BACKUP,
    CONTROL_ID_BROWSE_DESTINATION,
    CONTROL_ID_CLEANUP_SELECTIONS,
    CONTROL_ID_CLEANUP_STATUS,
    CONTROL_ID_CLOSE,
    CONTROL_ID_RESTORE,
    CONTROL_ID_SETTINGS,
    CONTROL_ID_USERDATA_PATH,
    MAIN_WINDOW_RESOLUTION,
    MAIN_WINDOW_SKIN,
    MAIN_WINDOW_XML,
)


class MainWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self._addon = kwargs["addon"]
        self._addon_name = kwargs["addon_name"]
        self._cleanup_selections = build_cleanup_selections(kwargs["runtime_paths"])
        self._destination_state = kwargs["destination_state"]
        self._runtime_paths = kwargs["runtime_paths"]

    def onInit(self):
        self._refresh_destination_display()
        self._refresh_cleanup_display()
        self.getControl(CONTROL_ID_USERDATA_PATH).setText(self._runtime_paths["userdata"])
        self.getControl(CONTROL_ID_ADDONS_PATH).setText(self._runtime_paths["addons"])
        self.setFocusId(CONTROL_ID_BACKUP)

    def _refresh_destination_display(self):
        if self._destination_state["path"]:
            path_label = self._destination_state["path"]
        else:
            path_label = "No backup destination selected."

        if self._destination_state["is_ready"]:
            status_label = f"{self._destination_state['source'].title()} destination ready."
        else:
            status_label = self._destination_state["error"]

        self.getControl(CONTROL_ID_BACKUP_DESTINATION_PATH).setText(path_label)
        self.getControl(CONTROL_ID_BACKUP_DESTINATION_STATUS).setLabel(status_label)

    def _refresh_cleanup_display(self):
        cleanup_lines = format_cleanup_selections(self._cleanup_selections)
        selected_count = sum(
            1 for selection in self._cleanup_selections if selection["selected"]
        )
        self.getControl(CONTROL_ID_CLEANUP_SELECTIONS).setText("[CR]".join(cleanup_lines))
        self.getControl(CONTROL_ID_CLEANUP_STATUS).setLabel(
            f"{selected_count} cleanup targets selected by default."
        )

    def _browse_destination(self):
        current_path = self._destination_state["path"]
        selected_path = xbmcgui.Dialog().browseSingle(
            0,
            "Select backup destination",
            "files",
            "",
            False,
            True,
            current_path,
        )
        if not selected_path:
            return

        try:
            self._destination_state = save_selected_backup_destination(self._addon, selected_path)
        except DestinationError as exc:
            xbmcgui.Dialog().ok(
                self._addon_name,
                "Destination not saved.",
                str(exc),
            )
            return

        self._refresh_destination_display()
        xbmcgui.Dialog().ok(
            self._addon_name,
            "Backup destination saved.",
            self._destination_state["path"],
        )

    def onClick(self, control_id):
        if control_id == CONTROL_ID_CLOSE:
            self.close()
            return

        if control_id == CONTROL_ID_BROWSE_DESTINATION:
            self._browse_destination()
            return

        if control_id == CONTROL_ID_BACKUP:
            try:
                preflight = run_backup_preflight(
                    self._runtime_paths,
                    self._destination_state,
                )
            except BackupPreflightError as exc:
                xbmcgui.Dialog().ok(
                    self._addon_name,
                    "Backup cannot start.",
                    str(exc),
                    "Fix the reported issue and try again.",
                )
                return

            try:
                cleanup_results = run_cleanup(self._cleanup_selections)
            except CleanupError as exc:
                xbmcgui.Dialog().ok(
                    self._addon_name,
                    "Cleanup failed.",
                    str(exc),
                    "Backup did not start.",
                )
                return

            removed_count = sum(1 for item in cleanup_results if item["status"] == "removed")
            skipped_count = sum(1 for item in cleanup_results if item["status"] == "skipped")

            try:
                manifest = build_backup_manifest(
                    addon_version=self._addon.getAddonInfo("version"),
                    runtime_paths=self._runtime_paths,
                    preflight=preflight,
                    cleanup_selections=self._cleanup_selections,
                    cleanup_results=cleanup_results,
                )
            except BackupManifestError as exc:
                xbmcgui.Dialog().ok(
                    self._addon_name,
                    "Backup cannot start.",
                    str(exc),
                )
                return

            xbmcgui.Dialog().ok(
                self._addon_name,
                "Backup is not implemented yet.",
                f"Destination: {preflight['destination_path']}",
                f"Manifest: {ARCHIVE_MANIFEST_NAME}",
                f"Files ready: {manifest['file_count']}",
                f"Cleanup removed: {removed_count}",
                f"Cleanup skipped: {skipped_count}",
            )
            return
        elif control_id == CONTROL_ID_RESTORE:
            heading = "Restore"
        elif control_id == CONTROL_ID_SETTINGS:
            heading = "Settings"
        else:
            return

        xbmcgui.Dialog().ok(self._addon_name, f"{heading} is not implemented yet.")

    def onAction(self, action):
        if action.getId() in (
            xbmcgui.ACTION_NAV_BACK,
            xbmcgui.ACTION_PREVIOUS_MENU,
        ):
            self.close()
            return

        super().onAction(action)


def open_main_window(addon, addon_path, addon_name, runtime_paths, destination_state):
    window = MainWindow(
        MAIN_WINDOW_XML,
        addon_path,
        MAIN_WINDOW_SKIN,
        MAIN_WINDOW_RESOLUTION,
        addon=addon,
        addon_name=addon_name,
        destination_state=destination_state,
        runtime_paths=runtime_paths,
    )
    window.doModal()
    del window
