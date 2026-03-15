import os
import zipfile

from resources.lib.constants import ARCHIVE_MANIFEST_NAME


class RestoreArchiveError(RuntimeError):
    pass


def validate_restore_archive(archive_path):
    archive_path = (archive_path or "").strip()
    if not archive_path:
        raise RestoreArchiveError("No backup archive was selected.")

    if not os.path.isfile(archive_path):
        raise RestoreArchiveError(f"Backup archive does not exist: {archive_path}")

    if not os.access(archive_path, os.R_OK):
        raise RestoreArchiveError(f"Backup archive is not readable: {archive_path}")

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.getinfo(ARCHIVE_MANIFEST_NAME)
            invalid_member = archive.testzip()
            entry_count = len(archive.infolist())
    except FileNotFoundError:
        raise RestoreArchiveError(f"Backup archive does not exist: {archive_path}")
    except PermissionError:
        raise RestoreArchiveError(f"Backup archive is not readable: {archive_path}")
    except zipfile.BadZipFile as exc:
        raise RestoreArchiveError(f"Backup archive is not a valid ZIP file: {archive_path} ({exc})")
    except zipfile.LargeZipFile as exc:
        raise RestoreArchiveError(f"Backup archive could not be opened: {archive_path} ({exc})")
    except KeyError:
        raise RestoreArchiveError(
            f"Backup archive is missing {ARCHIVE_MANIFEST_NAME}: {archive_path}"
        )
    except OSError as exc:
        raise RestoreArchiveError(f"Backup archive could not be read: {archive_path} ({exc})")

    if invalid_member:
        raise RestoreArchiveError(
            f"Backup archive contains a corrupt entry: {invalid_member}"
        )

    return {
        "path": archive_path,
        "entry_count": entry_count,
        "manifest_name": ARCHIVE_MANIFEST_NAME,
    }
