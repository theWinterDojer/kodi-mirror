from datetime import datetime, timezone

import xbmc

from resources.lib.destination import detect_platform_family


ARCHIVE_MANIFEST_NAME = "backup_manifest.json"
ARCHIVE_ROOTS = ("userdata", "addons")
MANIFEST_SCHEMA_VERSION = 1


class BackupManifestError(RuntimeError):
    pass


def _current_timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_kodi_version(info_label=xbmc.getInfoLabel):
    kodi_version = info_label("System.BuildVersion").strip()
    if not kodi_version:
        raise BackupManifestError("Could not determine Kodi version for backup manifest.")
    return kodi_version


def _build_cleanup_manifest_entries(cleanup_selections, cleanup_results):
    cleanup_results = cleanup_results or []
    status_by_id = {result["id"]: result["status"] for result in cleanup_results}

    entries = []
    for selection in cleanup_selections:
        if not selection["selected"]:
            continue
        entries.append(
            {
                "id": selection["id"],
                "label": selection["label"],
                "status": status_by_id.get(selection["id"], "selected"),
            }
        )
    return entries


def build_backup_manifest(
    addon_version,
    runtime_paths,
    backup_stats,
    cleanup_selections,
    cleanup_results=None,
    created_timestamp=None,
    kodi_version=None,
    platform_family=None,
):
    addon_version = (addon_version or "").strip()
    if not addon_version:
        raise BackupManifestError("Could not determine addon version for backup manifest.")

    if created_timestamp is None:
        created_timestamp = _current_timestamp()
    if platform_family is None:
        platform_family = detect_platform_family()
    if kodi_version is None:
        kodi_version = resolve_kodi_version()

    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "addon_version": addon_version,
        "created_timestamp": created_timestamp,
        "device_platform_family": platform_family,
        "kodi_version": kodi_version,
        "source_root_paths": {
            "userdata": runtime_paths["userdata"],
            "addons": runtime_paths["addons"],
        },
        "cleanup_selections_applied": _build_cleanup_manifest_entries(
            cleanup_selections,
            cleanup_results,
        ),
        "included_top_level_roots": list(ARCHIVE_ROOTS),
        "file_count": backup_stats["file_count"],
        "uncompressed_byte_size": backup_stats["source_bytes"],
    }
