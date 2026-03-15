import json
import os
import shutil
import tempfile
import zipfile

from resources.lib.constants import ARCHIVE_MANIFEST_NAME


FREE_SPACE_BUFFER_BYTES = 64 * 1024 * 1024
REQUIRED_ARCHIVE_ROOTS = ("userdata", "addons")


class RestorePreflightError(RuntimeError):
    pass


def _read_restore_manifest(archive_path):
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            manifest_bytes = archive.read(ARCHIVE_MANIFEST_NAME)
            archive_infos = archive.infolist()
    except FileNotFoundError:
        raise RestorePreflightError(f"Backup archive does not exist: {archive_path}")
    except PermissionError:
        raise RestorePreflightError(f"Backup archive is not readable: {archive_path}")
    except zipfile.BadZipFile as exc:
        raise RestorePreflightError(f"Backup archive is not a valid ZIP file: {archive_path} ({exc})")
    except KeyError:
        raise RestorePreflightError(
            f"Backup archive is missing {ARCHIVE_MANIFEST_NAME}: {archive_path}"
        )
    except OSError as exc:
        raise RestorePreflightError(f"Backup archive could not be read: {archive_path} ({exc})")

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise RestorePreflightError(
            f"Backup manifest is not valid UTF-8 JSON: {archive_path} ({exc})"
        )
    except json.JSONDecodeError as exc:
        raise RestorePreflightError(
            f"Backup manifest is not valid JSON: {archive_path} ({exc})"
        )

    if not isinstance(manifest, dict):
        raise RestorePreflightError("Backup manifest must be a JSON object.")

    if "manifest_schema_version" not in manifest:
        raise RestorePreflightError("Backup manifest is missing manifest_schema_version.")

    included_roots = manifest.get("included_top_level_roots")
    if not isinstance(included_roots, list):
        raise RestorePreflightError("Backup manifest is missing included_top_level_roots.")

    missing_roots = [root for root in REQUIRED_ARCHIVE_ROOTS if root not in included_roots]
    if missing_roots:
        raise RestorePreflightError(
            "Backup manifest is missing required restore roots: "
            + ", ".join(missing_roots)
        )

    return manifest, archive_infos


def _ensure_staging_directory(staging_path):
    staging_path = os.path.normpath(staging_path)
    try:
        os.makedirs(staging_path, exist_ok=True)
    except OSError as exc:
        raise RestorePreflightError(
            f"Restore staging directory could not be created: {staging_path} ({exc})"
        )

    if not os.path.isdir(staging_path):
        raise RestorePreflightError(
            f"Restore staging path is not a directory: {staging_path}"
        )

    if not os.access(staging_path, os.W_OK | os.X_OK):
        raise RestorePreflightError(
            f"Restore staging directory is not writable: {staging_path}"
        )

    try:
        with tempfile.NamedTemporaryFile(dir=staging_path, delete=True) as handle:
            handle.write(b"ok")
            handle.flush()
    except OSError as exc:
        raise RestorePreflightError(
            f"Restore staging directory is not writable: {staging_path} ({exc})"
        )

    return staging_path


def run_restore_preflight(
    runtime_paths,
    archive_details,
    disk_usage=shutil.disk_usage,
    safety_buffer_bytes=FREE_SPACE_BUFFER_BYTES,
):
    archive_path = archive_details["path"]
    manifest, archive_infos = _read_restore_manifest(archive_path)
    staging_path = _ensure_staging_directory(runtime_paths["restore_staging"])

    archive_bytes = sum(info.file_size for info in archive_infos)
    required_bytes = archive_bytes + safety_buffer_bytes

    try:
        free_bytes = disk_usage(staging_path).free
    except OSError as exc:
        raise RestorePreflightError(
            f"Could not read restore staging free space: {staging_path} ({exc})"
        )

    if free_bytes < required_bytes:
        raise RestorePreflightError(
            f"Not enough free space at restore staging path: {staging_path}"
        )

    return {
        "archive_path": archive_path,
        "manifest": manifest,
        "archive_bytes": archive_bytes,
        "free_bytes": free_bytes,
        "required_bytes": required_bytes,
        "staging_path": staging_path,
    }
