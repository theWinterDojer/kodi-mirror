import os
import shutil

from resources.lib.constants import ADDON_ID
from resources.lib.destination import DestinationError, validate_backup_destination


FREE_SPACE_BUFFER_BYTES = 64 * 1024 * 1024
EXCLUDED_BACKUP_PATHS = {
    "userdata": (os.path.join("addon_data", ADDON_ID),),
    "addons": (),
}


class BackupPreflightError(RuntimeError):
    pass


def _raise_walk_error(exc):
    raise BackupPreflightError(f"Could not read source path: {exc.filename} ({exc})")


def _require_readable_directory(path, label):
    if not os.path.isdir(path):
        raise BackupPreflightError(f"Required {label} path is missing: {path}")
    if not os.access(path, os.R_OK | os.X_OK):
        raise BackupPreflightError(f"Required {label} path is not readable: {path}")
    return path


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


def _collect_directory_stats(root_name, path):
    total_bytes = 0
    file_count = 0

    for current_root, dirnames, filenames in os.walk(path, onerror=_raise_walk_error):
        relative_root = os.path.relpath(current_root, path)
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
        for filename in filenames:
            relative_path = os.path.join(relative_root, filename) if relative_root else filename
            if _is_excluded_backup_path(root_name, relative_path):
                continue
            current_path = os.path.join(current_root, filename)
            try:
                total_bytes += os.path.getsize(current_path)
            except OSError as exc:
                raise BackupPreflightError(
                    f"Could not read source file: {current_path} ({exc})"
                )
            file_count += 1

    return total_bytes, file_count


def run_backup_preflight(
    runtime_paths,
    destination_state,
    disk_usage=shutil.disk_usage,
    safety_buffer_bytes=FREE_SPACE_BUFFER_BYTES,
):
    if not destination_state["is_ready"]:
        raise BackupPreflightError(destination_state["error"])

    try:
        destination_path = validate_backup_destination(destination_state["path"])
    except DestinationError as exc:
        raise BackupPreflightError(str(exc))

    userdata_path = _require_readable_directory(runtime_paths["userdata"], "userdata")
    addons_path = _require_readable_directory(runtime_paths["addons"], "addons")

    userdata_bytes, userdata_files = _collect_directory_stats("userdata", userdata_path)
    addons_bytes, addons_files = _collect_directory_stats("addons", addons_path)

    source_bytes = userdata_bytes + addons_bytes
    file_count = userdata_files + addons_files
    required_bytes = source_bytes + safety_buffer_bytes

    try:
        free_bytes = disk_usage(destination_path).free
    except OSError as exc:
        raise BackupPreflightError(
            f"Could not read destination free space: {destination_path} ({exc})"
        )

    if free_bytes < required_bytes:
        raise BackupPreflightError(
            f"Not enough free space at backup destination: {destination_path}"
        )

    return {
        "destination_path": destination_path,
        "file_count": file_count,
        "free_bytes": free_bytes,
        "required_bytes": required_bytes,
        "source_bytes": source_bytes,
    }
