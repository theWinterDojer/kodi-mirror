import json
import os
import posixpath
import shutil
import zipfile

from resources.lib.constants import (
    ARCHIVE_MANIFEST_NAME,
    PENDING_RESTORE_PLAN_NAME,
    PENDING_RESTORE_PLAN_SCHEMA_VERSION,
    RESTORE_PAYLOAD_DIRECTORY_NAME,
)


REQUIRED_ARCHIVE_ROOTS = ("userdata", "addons")


class RestoreStageError(RuntimeError):
    pass


def _clear_staging_directory(staging_path):
    try:
        entries = os.listdir(staging_path)
    except OSError as exc:
        raise RestoreStageError(
            f"Could not read restore staging directory: {staging_path} ({exc})"
        )

    for entry_name in entries:
        entry_path = os.path.join(staging_path, entry_name)
        try:
            if os.path.isdir(entry_path) and not os.path.islink(entry_path):
                shutil.rmtree(entry_path)
            else:
                os.remove(entry_path)
        except OSError as exc:
            raise RestoreStageError(
                f"Could not clear restore staging path: {entry_path} ({exc})"
            )


def _normalize_archive_member(name):
    normalized = (name or "").replace("\\", "/")
    if not normalized:
        raise RestoreStageError("Backup archive contains an empty entry name.")

    if normalized.startswith("/"):
        raise RestoreStageError(f"Backup archive entry is not safe to extract: {name}")

    for segment in normalized.split("/"):
        if segment in (".", ".."):
            raise RestoreStageError(f"Backup archive entry is not safe to extract: {name}")

    first_segment = normalized.split("/", 1)[0]
    if ":" in first_segment:
        raise RestoreStageError(f"Backup archive entry is not safe to extract: {name}")

    normalized = posixpath.normpath(normalized)
    if normalized in (".", ""):
        return ""

    if normalized == ".." or normalized.startswith("../") or "/../" in normalized:
        raise RestoreStageError(f"Backup archive entry is not safe to extract: {name}")

    return normalized


def _copy_archive_member(source_handle, destination_path):
    total_bytes = 0
    with open(destination_path, "wb") as destination_handle:
        while True:
            chunk = source_handle.read(1024 * 1024)
            if not chunk:
                break
            destination_handle.write(chunk)
            total_bytes += len(chunk)
    return total_bytes


def _extract_restore_payload(archive_path, payload_path):
    file_count = 0
    extracted_bytes = 0

    os.makedirs(os.path.join(payload_path, "userdata"), exist_ok=True)
    os.makedirs(os.path.join(payload_path, "addons"), exist_ok=True)

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            for archive_info in archive.infolist():
                normalized_name = _normalize_archive_member(archive_info.filename)
                if not normalized_name:
                    continue
                if normalized_name == ARCHIVE_MANIFEST_NAME:
                    continue

                top_level_root = normalized_name.split("/", 1)[0]
                if top_level_root not in REQUIRED_ARCHIVE_ROOTS:
                    raise RestoreStageError(
                        f"Backup archive contains an unsupported entry: {normalized_name}"
                    )

                destination_path = os.path.normpath(
                    os.path.join(payload_path, *normalized_name.split("/"))
                )
                if os.path.commonpath([payload_path, destination_path]) != payload_path:
                    raise RestoreStageError(
                        f"Backup archive entry is not safe to extract: {normalized_name}"
                    )

                if archive_info.is_dir():
                    os.makedirs(destination_path, exist_ok=True)
                    continue

                parent_path = os.path.dirname(destination_path)
                if parent_path:
                    os.makedirs(parent_path, exist_ok=True)

                try:
                    with archive.open(archive_info, "r") as source_handle:
                        extracted_bytes += _copy_archive_member(source_handle, destination_path)
                except OSError as exc:
                    raise RestoreStageError(
                        f"Could not extract restore entry: {normalized_name} ({exc})"
                    )
                except zipfile.BadZipFile as exc:
                    raise RestoreStageError(
                        f"Backup archive could not be read during restore staging: {archive_path} ({exc})"
                    )

                file_count += 1
    except FileNotFoundError:
        raise RestoreStageError(f"Backup archive does not exist: {archive_path}")
    except PermissionError:
        raise RestoreStageError(f"Backup archive is not readable: {archive_path}")
    except zipfile.BadZipFile as exc:
        raise RestoreStageError(f"Backup archive is not a valid ZIP file: {archive_path} ({exc})")
    except OSError as exc:
        raise RestoreStageError(f"Backup archive could not be extracted: {archive_path} ({exc})")

    return {
        "extracted_byte_size": extracted_bytes,
        "extracted_file_count": file_count,
    }


def _write_pending_restore_plan(plan_path, plan):
    try:
        with open(plan_path, "w", encoding="utf-8") as handle:
            json.dump(plan, handle, indent=2, sort_keys=True)
    except OSError as exc:
        raise RestoreStageError(f"Could not write pending restore plan: {plan_path} ({exc})")


def stage_restore_payload(runtime_paths, preflight):
    staging_path = preflight["staging_path"]
    payload_path = os.path.join(staging_path, RESTORE_PAYLOAD_DIRECTORY_NAME)
    archive_path = preflight["archive_path"]
    manifest = preflight["manifest"]

    _clear_staging_directory(staging_path)
    os.makedirs(payload_path, exist_ok=True)

    extracted_stats = _extract_restore_payload(archive_path, payload_path)

    staged_root_paths = {
        root_name: os.path.join(payload_path, root_name) for root_name in REQUIRED_ARCHIVE_ROOTS
    }
    plan = {
        "archive_path": archive_path,
        "manifest": manifest,
        "pending_restore_plan_schema_version": PENDING_RESTORE_PLAN_SCHEMA_VERSION,
        "payload_path": payload_path,
        "staged_root_paths": staged_root_paths,
        "staging_path": staging_path,
        "target_root_paths": {
            "userdata": runtime_paths["userdata"],
            "addons": runtime_paths["addons"],
        },
        "extracted_file_count": extracted_stats["extracted_file_count"],
        "extracted_byte_size": extracted_stats["extracted_byte_size"],
    }
    plan_path = os.path.join(staging_path, PENDING_RESTORE_PLAN_NAME)
    _write_pending_restore_plan(plan_path, plan)

    return {
        "payload_path": payload_path,
        "plan": plan,
        "plan_path": plan_path,
        "staging_path": staging_path,
    }
