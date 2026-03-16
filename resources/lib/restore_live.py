import ntpath
import os
import posixpath
import shutil
import zipfile

from resources.lib.constants import ADDON_ID, ARCHIVE_MANIFEST_NAME


REQUIRED_ARCHIVE_ROOTS = ("userdata", "addons")
EXCLUDED_RESTORE_PATHS = {
    "addons": (ADDON_ID,),
    "userdata": (os.path.join("addon_data", ADDON_ID),),
}
SKIPPED_SAMPLE_LIMIT = 10


class RestoreLiveError(RuntimeError):
    pass


def _filesystem_path(path, platform_name=None):
    if platform_name is None:
        platform_name = os.name
    if platform_name != "nt":
        return os.path.normpath(path)

    absolute_path = ntpath.abspath(ntpath.normpath(path))
    if absolute_path.startswith("\\\\?\\"):
        return absolute_path
    if absolute_path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute_path[2:]
    return "\\\\?\\" + absolute_path


def _normalize_archive_member(name):
    normalized = (name or "").replace("\\", "/")
    if not normalized:
        raise RestoreLiveError("Backup archive contains an empty entry name.")

    if normalized.startswith("/"):
        raise RestoreLiveError(f"Backup archive entry is not safe to restore: {name}")

    for segment in normalized.split("/"):
        if segment in (".", ".."):
            raise RestoreLiveError(f"Backup archive entry is not safe to restore: {name}")

    first_segment = normalized.split("/", 1)[0]
    if ":" in first_segment:
        raise RestoreLiveError(f"Backup archive entry is not safe to restore: {name}")

    normalized = posixpath.normpath(normalized)
    if normalized in ("", "."):
        return ""

    if normalized == ".." or normalized.startswith("../") or "/../" in normalized:
        raise RestoreLiveError(f"Backup archive entry is not safe to restore: {name}")

    return normalized


def _is_excluded_restore_path(root_name, relative_path):
    normalized_path = os.path.normpath(relative_path or "")
    if normalized_path in ("", "."):
        return False

    for excluded_prefix in EXCLUDED_RESTORE_PATHS.get(root_name, ()):
        normalized_prefix = os.path.normpath(excluded_prefix)
        if normalized_path == normalized_prefix:
            return True
        if normalized_path.startswith(normalized_prefix + os.sep):
            return True
    return False


def _record_skip(summary, archive_path, target_path, reason):
    summary["skipped_file_count"] += 1
    if len(summary["skipped_entries"]) < SKIPPED_SAMPLE_LIMIT:
        summary["skipped_entries"].append(
            {
                "archive_path": archive_path,
                "target_path": target_path,
                "reason": str(reason),
            }
        )


def _ensure_directory(path):
    filesystem_path = _filesystem_path(path)
    if os.path.islink(filesystem_path):
        os.remove(filesystem_path)
    elif os.path.exists(filesystem_path) and not os.path.isdir(filesystem_path):
        os.remove(filesystem_path)
    os.makedirs(filesystem_path, exist_ok=True)


def _copy_archive_member(source_handle, destination_path):
    with open(_filesystem_path(destination_path), "wb") as destination_handle:
        while True:
            chunk = source_handle.read(1024 * 1024)
            if not chunk:
                break
            destination_handle.write(chunk)


def apply_live_restore(runtime_paths, preflight, progress_callback=None):
    archive_path = preflight["archive_path"]
    target_root_paths = preflight["target_root_paths"]
    summary = {
        "restored_file_count": 0,
        "skipped_file_count": 0,
        "skipped_entries": [],
    }

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive_infos = archive.infolist()
            total_entries = len(archive_infos)
            for entry_index, archive_info in enumerate(archive_infos, 1):
                if progress_callback is not None:
                    progress_callback(entry_index, total_entries, archive_info.filename)

                normalized_name = _normalize_archive_member(archive_info.filename)
                if not normalized_name or normalized_name == ARCHIVE_MANIFEST_NAME:
                    continue

                root_name, _, remainder = normalized_name.partition("/")
                if root_name not in REQUIRED_ARCHIVE_ROOTS:
                    raise RestoreLiveError(
                        f"Backup archive contains an unsupported entry: {normalized_name}"
                    )

                relative_path = os.path.normpath(remainder) if remainder else ""
                if _is_excluded_restore_path(root_name, relative_path):
                    continue

                target_root = target_root_paths[root_name]
                destination_path = os.path.normpath(
                    os.path.join(target_root, *normalized_name.split("/")[1:])
                )
                if os.path.commonpath([target_root, destination_path]) != target_root:
                    raise RestoreLiveError(
                        f"Backup archive entry is not safe to restore: {normalized_name}"
                    )

                if archive_info.is_dir():
                    if not relative_path:
                        continue
                    try:
                        _ensure_directory(destination_path)
                    except OSError as exc:
                        _record_skip(summary, normalized_name, destination_path, exc)
                    continue

                try:
                    parent_path = os.path.dirname(destination_path)
                    if parent_path:
                        _ensure_directory(parent_path)

                    filesystem_destination_path = _filesystem_path(destination_path)
                    if os.path.isdir(filesystem_destination_path) and not os.path.islink(
                        filesystem_destination_path
                    ):
                        shutil.rmtree(filesystem_destination_path)
                    elif os.path.islink(filesystem_destination_path):
                        os.remove(filesystem_destination_path)

                    with archive.open(archive_info, "r") as source_handle:
                        _copy_archive_member(source_handle, destination_path)
                except OSError as exc:
                    _record_skip(summary, normalized_name, destination_path, exc)
                    continue

                summary["restored_file_count"] += 1
    except FileNotFoundError:
        raise RestoreLiveError(f"Backup archive does not exist: {archive_path}")
    except PermissionError:
        raise RestoreLiveError(f"Backup archive is not readable: {archive_path}")
    except zipfile.BadZipFile as exc:
        raise RestoreLiveError(f"Backup archive is not a valid ZIP file: {archive_path} ({exc})")
    except OSError as exc:
        raise RestoreLiveError(f"Backup archive could not be restored: {archive_path} ({exc})")

    return summary
