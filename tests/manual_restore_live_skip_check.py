import os
import shutil
import sys
import tempfile
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import resources.lib.restore_live as restore_live
from resources.lib.restore_archive import validate_restore_archive
from resources.lib.restore_preflight import run_restore_preflight


def write_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-restore-live-skip-")
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

        runtime_paths = {
            "userdata": os.path.join(temp_root, "live-userdata"),
            "addons": os.path.join(temp_root, "live-addons"),
        }
        preflight = run_restore_preflight(runtime_paths, validate_restore_archive(archive_path))

        original_copy = restore_live._copy_archive_member
        copy_targets = []

        def failing_copy(source_handle, destination_path):
            copy_targets.append(destination_path)
            if destination_path.endswith(os.path.join("plugin.video.example", "addon.xml")):
                raise PermissionError("forced locked file")
            return original_copy(source_handle, destination_path)

        restore_live._copy_archive_member = failing_copy
        try:
            result = restore_live.apply_live_restore(runtime_paths, preflight)
        finally:
            restore_live._copy_archive_member = original_copy

        assert len(copy_targets) == 2
        assert result["restored_file_count"] == 1
        assert result["skipped_file_count"] == 1
        assert len(result["skipped_entries"]) == 1
        skipped_entry = result["skipped_entries"][0]
        assert skipped_entry["archive_path"] == "addons/plugin.video.example/addon.xml"
        assert "forced locked file" in skipped_entry["reason"]
        assert os.path.isfile(os.path.join(runtime_paths["userdata"], "guisettings.xml"))
        assert not os.path.exists(os.path.join(runtime_paths["addons"], "plugin.video.example", "addon.xml"))

        corrupt_targets = []

        def corrupt_copy(source_handle, destination_path):
            corrupt_targets.append(destination_path)
            if destination_path.endswith(os.path.join("plugin.video.example", "addon.xml")):
                raise zipfile.BadZipFile("forced bad member")
            return original_copy(source_handle, destination_path)

        restore_live._copy_archive_member = corrupt_copy
        try:
            corrupt_result = restore_live.apply_live_restore(runtime_paths, preflight)
        finally:
            restore_live._copy_archive_member = original_copy

        assert len(corrupt_targets) == 2
        assert corrupt_result["restored_file_count"] == 1
        assert corrupt_result["skipped_file_count"] == 1
        corrupt_skipped_entry = corrupt_result["skipped_entries"][0]
        assert corrupt_skipped_entry["archive_path"] == "addons/plugin.video.example/addon.xml"
        assert "forced bad member" in corrupt_skipped_entry["reason"]

        def runtime_failure_copy(source_handle, destination_path):
            if destination_path.endswith(os.path.join("plugin.video.example", "addon.xml")):
                raise RuntimeError("forced runtime failure")
            return original_copy(source_handle, destination_path)

        restore_live._copy_archive_member = runtime_failure_copy
        try:
            try:
                restore_live.apply_live_restore(runtime_paths, preflight)
            except RuntimeError as exc:
                assert "forced runtime failure" in str(exc)
            else:
                raise AssertionError("Expected runtime restore bug to propagate.")
        finally:
            restore_live._copy_archive_member = original_copy
    finally:
        shutil.rmtree(temp_root)

    print("restore live skip ok")


if __name__ == "__main__":
    main()
