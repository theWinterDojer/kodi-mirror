import re

from resources.lib.backup_manifest import BackupManifestError, resolve_kodi_version
from resources.lib.destination import DestinationError, detect_platform_family


class RestoreWarningError(RuntimeError):
    pass


def _require_manifest_value(manifest, key):
    value = manifest.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RestoreWarningError(f"Backup manifest is missing {key}.")
    return value.strip()


def _parse_kodi_major(version):
    match = re.match(r"(\d+)", version)
    if not match:
        raise RestoreWarningError(f"Could not determine Kodi major version from: {version}")
    return int(match.group(1))


def build_restore_warnings(
    manifest,
    current_platform_family=None,
    current_kodi_version=None,
):
    if not isinstance(manifest, dict):
        raise RestoreWarningError("Backup manifest must be a JSON object.")

    backup_platform_family = _require_manifest_value(manifest, "device_platform_family")
    backup_kodi_version = _require_manifest_value(manifest, "kodi_version")

    if current_platform_family is None:
        try:
            current_platform_family = detect_platform_family()
        except DestinationError as exc:
            raise RestoreWarningError(str(exc))

    if current_kodi_version is None:
        try:
            current_kodi_version = resolve_kodi_version()
        except BackupManifestError as exc:
            raise RestoreWarningError(str(exc))

    current_platform_family = (current_platform_family or "").strip()
    if not current_platform_family:
        raise RestoreWarningError("Could not determine the current Kodi platform.")

    current_kodi_version = (current_kodi_version or "").strip()
    if not current_kodi_version:
        raise RestoreWarningError("Could not determine the current Kodi version.")

    warnings = []
    if backup_platform_family != current_platform_family:
        warnings.append(
            f"Platform differs: backup {backup_platform_family}, current {current_platform_family}."
        )

    backup_kodi_major = _parse_kodi_major(backup_kodi_version)
    current_kodi_major = _parse_kodi_major(current_kodi_version)
    if backup_kodi_major != current_kodi_major:
        warnings.append(
            f"Kodi major differs: backup {backup_kodi_major}, current {current_kodi_major}."
        )

    return {
        "backup_kodi_version": backup_kodi_version,
        "backup_platform_family": backup_platform_family,
        "current_kodi_version": current_kodi_version,
        "current_platform_family": current_platform_family,
        "warnings": warnings,
    }
