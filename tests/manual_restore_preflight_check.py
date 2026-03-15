import os
import shutil
import sys
import tempfile
import types
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from resources.lib.restore_archive import validate_restore_archive
from resources.lib.restore_preflight import RestorePreflightError, run_restore_preflight


def write_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-restore-preflight-")
    try:
        archive_path = os.path.join(temp_root, "backup.zip")
        write_zip(
            archive_path,
            {
                "backup_manifest.json": (
                    '{"manifest_schema_version": 1, '
                    '"included_top_level_roots": ["userdata", "addons"]}'
                ),
                "userdata/guisettings.xml": "<settings />",
                "addons/plugin.video.example/addon.xml": "<addon />",
            },
        )
        archive_details = validate_restore_archive(archive_path)
        runtime_paths = {
            "restore_staging": os.path.join(temp_root, "pending_restore"),
        }

        success = run_restore_preflight(
            runtime_paths,
            archive_details,
            disk_usage=lambda _path: types.SimpleNamespace(free=10_000_000),
            safety_buffer_bytes=0,
        )
        assert success["archive_path"] == archive_path
        assert success["manifest"]["manifest_schema_version"] == 1
        assert success["manifest"]["included_top_level_roots"] == ["userdata", "addons"]
        assert success["staging_path"] == os.path.normpath(runtime_paths["restore_staging"])
        assert os.path.isdir(success["staging_path"])
        assert success["archive_bytes"] == (
            len(
                '{"manifest_schema_version": 1, "included_top_level_roots": ["userdata", "addons"]}'
            )
            + len("<settings />")
            + len("<addon />")
        )

        invalid_manifest_archive = os.path.join(temp_root, "invalid-manifest.zip")
        write_zip(
            invalid_manifest_archive,
            {
                "backup_manifest.json": "not json",
                "userdata/guisettings.xml": "<settings />",
            },
        )
        try:
            run_restore_preflight(
                runtime_paths,
                validate_restore_archive(invalid_manifest_archive),
                disk_usage=lambda _path: types.SimpleNamespace(free=10_000_000),
                safety_buffer_bytes=0,
            )
        except RestorePreflightError as exc:
            assert "not valid JSON" in str(exc)
        else:
            raise AssertionError("Expected invalid manifest to fail preflight.")

        missing_roots_archive = os.path.join(temp_root, "missing-roots.zip")
        write_zip(
            missing_roots_archive,
            {
                "backup_manifest.json": (
                    '{"manifest_schema_version": 1, '
                    '"included_top_level_roots": ["userdata"]}'
                ),
                "userdata/guisettings.xml": "<settings />",
            },
        )
        try:
            run_restore_preflight(
                runtime_paths,
                validate_restore_archive(missing_roots_archive),
                disk_usage=lambda _path: types.SimpleNamespace(free=10_000_000),
                safety_buffer_bytes=0,
            )
        except RestorePreflightError as exc:
            assert "missing required restore roots" in str(exc)
        else:
            raise AssertionError("Expected missing restore roots to fail preflight.")

        try:
            run_restore_preflight(
                runtime_paths,
                archive_details,
                disk_usage=lambda _path: types.SimpleNamespace(free=1),
                safety_buffer_bytes=0,
            )
        except RestorePreflightError as exc:
            assert "Not enough free space" in str(exc)
        else:
            raise AssertionError("Expected low free space to fail preflight.")
    finally:
        shutil.rmtree(temp_root)

    print("restore preflight ok")


if __name__ == "__main__":
    main()
