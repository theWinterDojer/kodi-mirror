import os
import uuid

import xbmc


ANDROID_BACKUP_ROOT = "/storage/emulated/0/Backup"
BACKUP_DIRECTORY_NAME = "Backup"


class DestinationError(RuntimeError):
    pass


def detect_platform_family():
    if xbmc.getCondVisibility("system.platform.android"):
        return "android"
    if xbmc.getCondVisibility("system.platform.windows"):
        return "windows"
    if xbmc.getCondVisibility("system.platform.osx"):
        return "macos"
    if xbmc.getCondVisibility("system.platform.linux"):
        return "linux"
    raise DestinationError("Could not determine the Kodi platform for backup destination selection.")


def resolve_default_backup_destination(environment=None):
    if environment is None:
        environment = os.environ
    platform_family = detect_platform_family()

    if platform_family == "android":
        return ANDROID_BACKUP_ROOT

    if platform_family == "windows":
        home_path = environment.get("USERPROFILE", "").strip()
        if not home_path:
            raise DestinationError("Backup destination default requires USERPROFILE on Windows.")
    else:
        home_path = environment.get("HOME", "").strip()
        if not home_path:
            raise DestinationError(f"Backup destination default requires HOME on {platform_family}.")

    return os.path.normpath(os.path.join(home_path, BACKUP_DIRECTORY_NAME))


def validate_backup_destination(path, create=True):
    normalized_path = os.path.normpath((path or "").strip())
    if not normalized_path or normalized_path == ".":
        raise DestinationError("Backup destination path is required.")

    if os.path.exists(normalized_path):
        if not os.path.isdir(normalized_path):
            raise DestinationError(f"Backup destination is not a directory: {normalized_path}")
    elif create:
        try:
            os.makedirs(normalized_path, exist_ok=True)
        except OSError as exc:
            raise DestinationError(
                f"Could not create backup destination: {normalized_path} ({exc})"
            )
    else:
        raise DestinationError(f"Backup destination does not exist: {normalized_path}")

    probe_name = f".kodimirror-write-test-{uuid.uuid4().hex}.tmp"
    probe_path = os.path.join(normalized_path, probe_name)
    try:
        with open(probe_path, "w", encoding="utf-8") as probe_file:
            probe_file.write("ok")
    except OSError as exc:
        raise DestinationError(
            f"Backup destination is not writable: {normalized_path} ({exc})"
        )
    finally:
        try:
            if os.path.exists(probe_path):
                os.remove(probe_path)
        except OSError:
            pass

    return normalized_path


def resolve_default_destination_state(environment=None):
    try:
        destination_path = resolve_default_backup_destination(environment)
    except DestinationError as exc:
        return {
            "path": "",
            "is_ready": False,
            "error": str(exc),
        }

    try:
        ready_path = validate_backup_destination(destination_path)
    except DestinationError as exc:
        return {
            "path": destination_path,
            "is_ready": False,
            "error": str(exc),
        }

    return {
        "path": ready_path,
        "is_ready": True,
        "error": "",
    }
