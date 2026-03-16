import json
import os
import zipfile
from datetime import datetime

from resources.lib.constants import ADDON_ID
from resources.lib.backup_manifest import ARCHIVE_MANIFEST_NAME, ARCHIVE_ROOTS


ARCHIVE_COMPRESSION_LEVEL = 6
ARCHIVE_FILENAME_PREFIX = "KodiBackup"
EXCLUDED_BACKUP_PATHS = {
    "userdata": (os.path.join("addon_data", ADDON_ID),),
    "addons": (),
}


class BackupArchiveError(RuntimeError):
    pass


def _is_excluded_backup_path(root_name, relative_path):
    normalized_path = os.path.normpath(relative_path or "")
    if normalized_path in ("", "."):
        return False

    for excluded_prefix in EXCLUDED_BACKUP_PATHS.get(root_name, ()):
        normalized_prefix = os.path.normpath(excluded_prefix)
        if normalized_path == normalized_prefix:
            return True
        if normalized_path.startswith(normalized_prefix + os.sep):
            return True
    return False


def collect_backup_entries(runtime_paths):
    entries = []
    file_count = 0
    source_bytes = 0

    for root_name in ARCHIVE_ROOTS:
        source_root = runtime_paths[root_name]
        for current_root, dirnames, filenames in os.walk(source_root):
            relative_root = os.path.relpath(current_root, source_root)
            if relative_root == ".":
                relative_root = ""

            dirnames[:] = [
                dirname
                for dirname in dirnames
                if not _is_excluded_backup_path(
                    root_name,
                    os.path.join(relative_root, dirname) if relative_root else dirname,
                )
            ]
            filenames.sort()
            for filename in filenames:
                relative_path = os.path.join(relative_root, filename) if relative_root else filename
                if _is_excluded_backup_path(root_name, relative_path):
                    continue
                source_path = os.path.join(current_root, filename)
                archive_path = f"{root_name}/{relative_path.replace(os.sep, '/')}"
                try:
                    file_size = os.path.getsize(source_path)
                except OSError as exc:
                    raise BackupArchiveError(
                        f"Could not read source file for backup: {source_path} ({exc})"
                    )

                entries.append(
                    {
                        "archive_path": archive_path,
                        "size": file_size,
                        "source_path": source_path,
                    }
                )
                file_count += 1
                source_bytes += file_size

    return {
        "entries": entries,
        "file_count": file_count,
        "source_bytes": source_bytes,
    }


def _format_backup_filename(created_timestamp):
    normalized = created_timestamp.replace("Z", "+00:00")
    try:
        created_at = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise BackupArchiveError(f"Could not parse backup timestamp: {created_timestamp} ({exc})")

    return f"{ARCHIVE_FILENAME_PREFIX}-{created_at.strftime('%Y%m%d-%H%M%S')}.zip"


def create_backup_archive(destination_path, collected_entries, manifest):
    archive_name = _format_backup_filename(manifest["created_timestamp"])
    archive_path = os.path.join(destination_path, archive_name)

    try:
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=ARCHIVE_COMPRESSION_LEVEL,
        ) as archive:
            for entry in collected_entries["entries"]:
                archive.write(entry["source_path"], entry["archive_path"])
            archive.writestr(
                ARCHIVE_MANIFEST_NAME,
                json.dumps(manifest, indent=2, sort_keys=True),
            )
    except OSError as exc:
        raise BackupArchiveError(f"Could not create backup archive: {archive_path} ({exc})")
    except zipfile.BadZipFile as exc:
        raise BackupArchiveError(f"Could not write backup archive: {archive_path} ({exc})")

    return archive_path
