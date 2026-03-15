import os
import shutil

from resources.lib.destination import DestinationError, validate_backup_destination


FREE_SPACE_BUFFER_BYTES = 64 * 1024 * 1024


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


def _collect_directory_stats(path):
    total_bytes = 0
    file_count = 0

    for current_root, _, filenames in os.walk(path, onerror=_raise_walk_error):
        for filename in filenames:
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

    userdata_bytes, userdata_files = _collect_directory_stats(userdata_path)
    addons_bytes, addons_files = _collect_directory_stats(addons_path)

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
