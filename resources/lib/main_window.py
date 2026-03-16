import xbmcgui

from resources.lib import log
from resources.lib.backup_engine import (
    BackupArchiveError,
    collect_backup_entries,
    create_backup_archive,
)
from resources.lib.backup_manifest import (
    BackupManifestError,
    build_backup_manifest,
)
from resources.lib.backup_progress import BackupProgress
from resources.lib.backup_preflight import BackupPreflightError, run_backup_preflight
from resources.lib.cleanup import (
    CleanupError,
    build_cleanup_selections,
    format_cleanup_selections,
    run_cleanup,
)
from resources.lib.dialog import compose_dialog_text
from resources.lib.destination import (
    DestinationError,
    clear_saved_backup_destination,
    resolve_default_destination_state,
    save_selected_backup_destination,
)
from resources.lib.restore_archive import RestoreArchiveError, validate_restore_archive
from resources.lib.restore_live import RestoreLiveError, apply_live_restore
from resources.lib.restore_preflight import RestorePreflightError, run_restore_preflight
from resources.lib.restore_warning import RestoreWarningError, build_restore_warnings
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
        self.getControl(CONTROL_ID_BACKUP_DESTINATION_STATUS).setText(status_label)

    def _refresh_cleanup_display(self):
        cleanup_lines = format_cleanup_selections(self._cleanup_selections)
        selected_count = sum(
            1 for selection in self._cleanup_selections if selection["selected"]
        )
        self.getControl(CONTROL_ID_CLEANUP_SELECTIONS).setText("[CR]".join(cleanup_lines))
        if selected_count == 0:
            status_label = "No cleanup targets selected."
        elif selected_count == 1:
            status_label = "1 cleanup target selected."
        else:
            status_label = f"{selected_count} cleanup targets selected."
        self.getControl(CONTROL_ID_CLEANUP_STATUS).setText(status_label)

    def _set_cleanup_selection_state(self, selected_ids):
        selected_ids = set(selected_ids)
        for selection in self._cleanup_selections:
            selection["selected"] = selection["id"] in selected_ids
        self._refresh_cleanup_display()

    def _edit_cleanup_targets(self):
        while True:
            options = [
                *format_cleanup_selections(self._cleanup_selections),
                "Select all",
                "Clear all",
                "Apply cleanup selection",
            ]
            selection_index = xbmcgui.Dialog().select(
                "Cleanup before backup",
                options,
            )
            if selection_index == -1:
                return

            if selection_index == len(self._cleanup_selections) + 2:
                self._refresh_cleanup_display()
                return

            if selection_index == len(self._cleanup_selections):
                self._set_cleanup_selection_state(
                    selection["id"] for selection in self._cleanup_selections
                )
                continue

            if selection_index == len(self._cleanup_selections) + 1:
                self._set_cleanup_selection_state(set())
                continue

            selected_item = self._cleanup_selections[selection_index]
            selected_item["selected"] = not selected_item["selected"]
            self._refresh_cleanup_display()

    def _open_backup_review(self):
        selected_count = sum(
            1 for selection in self._cleanup_selections if selection["selected"]
        )
        destination_path = self._destination_state["path"] or "No backup destination selected."
        while True:
            cleanup_label = f"Edit cleanup ({selected_count} selected)"
            selection_index = xbmcgui.Dialog().select(
                "Backup",
                [
                    "Start backup",
                    cleanup_label,
                    "Cancel",
                ],
            )
            if selection_index in (-1, 2):
                return False

            if selection_index == 0:
                return True

            if selection_index == 1:
                self._edit_cleanup_targets()
                selected_count = sum(
                    1 for selection in self._cleanup_selections if selection["selected"]
                )
                continue

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
                compose_dialog_text(
                    "Destination not saved.",
                    str(exc),
                ),
            )
            return

        self._refresh_destination_display()
        xbmcgui.Dialog().ok(
            self._addon_name,
            compose_dialog_text(
                "Backup destination saved.",
                self._destination_state["path"],
            ),
        )

    def _open_settings(self):
        selection = xbmcgui.Dialog().select(
            "Settings",
            [
                "Change backup destination",
                "Use platform default destination",
            ],
        )
        if selection == -1:
            return

        if selection == 0:
            self._browse_destination()
            return

        clear_saved_backup_destination(self._addon)
        self._destination_state = resolve_default_destination_state()
        self._refresh_destination_display()
        if self._destination_state["is_ready"]:
            xbmcgui.Dialog().ok(
                self._addon_name,
                compose_dialog_text(
                    "Default destination active.",
                    self._destination_state["path"],
                ),
            )
            return

        xbmcgui.Dialog().ok(
            self._addon_name,
            compose_dialog_text(
                "Default destination not ready.",
                self._destination_state["error"],
                "Choose Backup Destination to save another path.",
            ),
        )

    def _browse_restore_archive(self):
        start_path = self._destination_state["path"] or ""
        selected_path = xbmcgui.Dialog().browseSingle(
            1,
            "Select backup archive",
            "files",
            ".zip",
            False,
            False,
            start_path,
        )
        if not selected_path:
            log.info("Restore archive browse canceled")
            return

        log.info(f"Restore archive selected: {selected_path}")

        try:
            archive_details = validate_restore_archive(selected_path)
        except RestoreArchiveError as exc:
            log.error(f"Restore archive validation failed: {exc}")
            xbmcgui.Dialog().ok(
                self._addon_name,
                compose_dialog_text(
                    "Restore cannot start.",
                    str(exc),
                    "Choose a valid KodiMirror backup zip.",
                ),
            )
            return
        log.info(
            "Restore archive validated successfully: "
            f"{archive_details['entry_count']} entries"
        )

        try:
            preflight = run_restore_preflight(self._runtime_paths, archive_details)
        except RestorePreflightError as exc:
            log.error(f"Restore preflight failed: {exc}")
            xbmcgui.Dialog().ok(
                self._addon_name,
                compose_dialog_text(
                    "Restore cannot start.",
                    str(exc),
                    "Fix the reported issue and try again.",
                ),
            )
            return
        log.info(
            "Restore preflight passed: "
            f"archive_bytes={preflight['archive_bytes']} "
            f"entry_count={preflight['entry_count']} "
            f"userdata_target={preflight['target_root_paths']['userdata']} "
            f"addons_target={preflight['target_root_paths']['addons']}"
        )

        try:
            warning_result = build_restore_warnings(preflight["manifest"])
        except RestoreWarningError as exc:
            log.error(f"Restore warning evaluation failed: {exc}")
            xbmcgui.Dialog().ok(
                self._addon_name,
                compose_dialog_text(
                    "Restore cannot start.",
                    str(exc),
                    "Fix the reported issue and try again.",
                ),
            )
            return
        if warning_result["warnings"]:
            log.info(
                "Restore warnings generated: "
                + " | ".join(warning_result["warnings"])
            )
        else:
            log.info("Restore warnings generated: none")

        if warning_result["warnings"]:
            dialog_lines = [
                "Live restore runs now.",
                "Files Kodi is using may stay unchanged.",
            ]
            dialog_lines.extend(warning_result["warnings"])
            dialog_lines.append("Restore can continue.")
            dialog_lines.append(f"Archive entries: {archive_details['entry_count']}")
            dialog_lines.append(archive_details["path"])
            xbmcgui.Dialog().ok(
                self._addon_name,
                compose_dialog_text(
                    "Restore warnings.",
                    *dialog_lines,
                ),
            )

        progress = BackupProgress(xbmcgui.DialogProgress())
        progress.start("Restore")
        log.info("Restore progress dialog opened")
        last_percent = {"value": 15}

        def update_restore_progress(current_entry, total_entries, _archive_name):
            if total_entries <= 0:
                return
            percent = 15 + int((current_entry * 80) / total_entries)
            if percent <= last_percent["value"]:
                return
            last_percent["value"] = percent
            progress.update(percent, "Applying live restore.")

        try:
            progress.update(15, "Applying live restore.")
            restore_result = apply_live_restore(
                self._runtime_paths,
                preflight,
                progress_callback=update_restore_progress,
            )
        except RestoreLiveError as exc:
            progress.close()
            log.error(f"Live restore failed: {exc}")
            xbmcgui.Dialog().ok(
                self._addon_name,
                compose_dialog_text(
                    "Restore failed.",
                    str(exc),
                ),
            )
            return

        progress.update(100, "Restore complete.")
        progress.close()
        log.info(
            "Live restore finished: "
            f"restored_file_count={restore_result['restored_file_count']} "
            f"skipped_file_count={restore_result['skipped_file_count']}"
        )
        for skipped_entry in restore_result["skipped_entries"]:
            log.info(
                "Live restore skipped: "
                f"{skipped_entry['archive_path']} ({skipped_entry['reason']})"
            )
        if restore_result["skipped_file_count"] > 0:
            result_lines = [
                f"Restore completed with {restore_result['skipped_file_count']} skipped files.",
                f"Files restored: {restore_result['restored_file_count']}",
                f"Files skipped: {restore_result['skipped_file_count']}",
            ]
        else:
            result_lines = [
                "Restore completed successfully.",
                f"Files restored: {restore_result['restored_file_count']}",
                "Files skipped: 0",
            ]
        if restore_result["skipped_file_count"] > 0:
            result_lines.append("Some files stayed unchanged while Kodi was running.")
            for skipped_entry in restore_result["skipped_entries"][:3]:
                result_lines.append(skipped_entry["archive_path"])
            result_lines.append("See kodi.log for skipped details.")
        xbmcgui.Dialog().ok(
            self._addon_name,
            compose_dialog_text(*result_lines),
        )

    def onClick(self, control_id):
        if control_id == CONTROL_ID_CLOSE:
            self.close()
            return

        if control_id == CONTROL_ID_BROWSE_DESTINATION:
            self._browse_destination()
            return

        if control_id == CONTROL_ID_BACKUP:
            if not self._open_backup_review():
                log.info("Backup review canceled")
                return
            log.info("Backup flow confirmed by user")
            progress = BackupProgress(xbmcgui.DialogProgress())
            progress.start("Backup")
            log.info("Backup progress dialog opened")
            try:
                progress.update(10, "Checking backup paths.")
                preflight = run_backup_preflight(
                    self._runtime_paths,
                    self._destination_state,
                )
            except BackupPreflightError as exc:
                progress.close()
                log.error(f"Backup preflight failed: {exc}")
                xbmcgui.Dialog().ok(
                    self._addon_name,
                    compose_dialog_text(
                        "Backup cannot start.",
                        str(exc),
                        "Fix the reported issue and try again.",
                    ),
                )
                return
            log.info(
                "Backup preflight passed: "
                f"destination_path={preflight['destination_path']} "
                f"source_bytes={preflight['source_bytes']} "
                f"required_bytes={preflight['required_bytes']} "
                f"free_bytes={preflight['free_bytes']}"
            )

            try:
                progress.update(30, "Cleaning selected cache folders.")
                cleanup_results = run_cleanup(self._cleanup_selections)
            except CleanupError as exc:
                progress.close()
                log.error(f"Cleanup failed before backup: {exc}")
                xbmcgui.Dialog().ok(
                    self._addon_name,
                    compose_dialog_text(
                        "Cleanup failed.",
                        str(exc),
                        "Backup did not start.",
                    ),
                )
                return
            cleaned_count = sum(
                1 for result in cleanup_results if result["status"] == "cleaned"
            )
            skipped_count = sum(
                1 for result in cleanup_results if result["status"] == "missing"
            )
            log.info(
                "Cleanup completed before backup: "
                f"cleaned={cleaned_count} skipped={skipped_count} "
                f"selected={sum(1 for selection in self._cleanup_selections if selection['selected'])}"
            )

            try:
                progress.update(55, "Collecting files for backup.")
                collected_entries = collect_backup_entries(self._runtime_paths)
                log.info(
                    "Backup entries collected: "
                    f"file_count={collected_entries['file_count']} "
                    f"source_bytes={collected_entries['source_bytes']}"
                )
                progress.update(70, "Building backup manifest.")
                manifest = build_backup_manifest(
                    addon_version=self._addon.getAddonInfo("version"),
                    runtime_paths=self._runtime_paths,
                    backup_stats=collected_entries,
                    cleanup_selections=self._cleanup_selections,
                    cleanup_results=cleanup_results,
                )
                log.info(
                    "Backup manifest built: "
                    f"file_count={manifest['file_count']} "
                    f"uncompressed_byte_size={manifest['uncompressed_byte_size']}"
                )
                progress.update(85, "Writing backup archive.")
                archive_path = create_backup_archive(
                    preflight["destination_path"],
                    collected_entries,
                    manifest,
                )
            except (BackupArchiveError, BackupManifestError) as exc:
                progress.close()
                log.error(f"Backup execution failed: {exc}")
                xbmcgui.Dialog().ok(
                    self._addon_name,
                    compose_dialog_text(
                        "Backup failed.",
                        str(exc),
                    ),
                )
                return

            progress.update(100, "Backup complete.")
            log.info(f"Backup archive created successfully: {archive_path}")
            log.info("Closing backup progress dialog")
            progress.close()
            log.info("Backup progress dialog closed")
            log.info("Opening backup complete dialog")
            xbmcgui.Dialog().ok(
                self._addon_name,
                compose_dialog_text(
                    "Backup complete.",
                    archive_path,
                    f"Files backed up: {manifest['file_count']}",
                ),
            )
            log.info("Backup complete dialog closed")
            return
        if control_id == CONTROL_ID_RESTORE:
            self._browse_restore_archive()
            return

        if control_id == CONTROL_ID_SETTINGS:
            self._open_settings()
            return

        return

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
