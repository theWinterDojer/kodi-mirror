import json
import os
import tempfile
import zipfile

from resources.lib.constants import ARCHIVE_MANIFEST_NAME


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


def _ensure_live_target_root(path, label):
    path = os.path.normpath(path)
    if os.path.exists(path) and not os.path.isdir(path):
        raise RestorePreflightError(f"Restore target {label} is not a directory: {path}")

    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:
        raise RestorePreflightError(
            f"Restore target {label} could not be created: {path} ({exc})"
        )

    if not os.access(path, os.W_OK | os.X_OK):
        raise RestorePreflightError(f"Restore target {label} is not writable: {path}")

    try:
        with tempfile.NamedTemporaryFile(dir=path, delete=True) as handle:
            handle.write(b"ok")
            handle.flush()
    except OSError as exc:
        raise RestorePreflightError(
            f"Restore target {label} is not writable: {path} ({exc})"
        )

    return path


def run_restore_preflight(runtime_paths, archive_details):
    archive_path = archive_details["path"]
    manifest, archive_infos = _read_restore_manifest(archive_path)
    target_root_paths = {
        root_name: _ensure_live_target_root(runtime_paths[root_name], root_name)
        for root_name in REQUIRED_ARCHIVE_ROOTS
    }
    archive_bytes = sum(info.file_size for info in archive_infos)

    return {
        "archive_path": archive_path,
        "manifest": manifest,
        "archive_bytes": archive_bytes,
        "entry_count": len(archive_infos),
        "target_root_paths": target_root_paths,
    }
