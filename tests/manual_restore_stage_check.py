import json
import os
import shutil
import sys
import tempfile
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from resources.lib.restore_archive import validate_restore_archive
from resources.lib.restore_preflight import run_restore_preflight
from resources.lib.restore_stage import RestoreStageError, stage_restore_payload


def write_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-restore-stage-")
    try:
        archive_path = os.path.join(temp_root, "backup.zip")
        write_zip(
            archive_path,
            {
                "backup_manifest.json": (
                    '{"manifest_schema_version": 1, '
                    '"device_platform_family": "linux", '
                    '"kodi_version": "20.1 (20.1.0)", '
                    '"included_top_level_roots": ["userdata", "addons"]}'
                ),
                "userdata/guisettings.xml": "<settings />",
                "addons/plugin.video.example/addon.xml": "<addon />",
            },
        )

        runtime_paths = {
            "userdata": os.path.join(temp_root, "live-userdata"),
            "addons": os.path.join(temp_root, "live-addons"),
            "restore_staging": os.path.join(temp_root, "pending_restore"),
        }
        os.makedirs(runtime_paths["userdata"], exist_ok=True)
        os.makedirs(runtime_paths["addons"], exist_ok=True)
        os.makedirs(runtime_paths["restore_staging"], exist_ok=True)
        with open(
            os.path.join(runtime_paths["restore_staging"], "old-file.txt"),
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write("old")

        archive_details = validate_restore_archive(archive_path)
        preflight = run_restore_preflight(
            runtime_paths,
            archive_details,
            disk_usage=lambda _path: type("Usage", (), {"free": 10_000_000})(),
            safety_buffer_bytes=0,
        )
        staged = stage_restore_payload(runtime_paths, preflight)

        userdata_file = os.path.join(
            staged["payload_path"],
            "userdata",
            "guisettings.xml",
        )
        addon_file = os.path.join(
            staged["payload_path"],
            "addons",
            "plugin.video.example",
            "addon.xml",
        )
        assert os.path.isfile(userdata_file)
        assert os.path.isfile(addon_file)
        assert read_text(userdata_file) == "<settings />"
        assert read_text(addon_file) == "<addon />"
        assert not os.path.exists(os.path.join(runtime_paths["restore_staging"], "old-file.txt"))

        with open(staged["plan_path"], "r", encoding="utf-8") as handle:
            plan = json.load(handle)
        assert plan["archive_path"] == archive_path
        assert plan["target_root_paths"] == {
            "userdata": runtime_paths["userdata"],
            "addons": runtime_paths["addons"],
        }
        assert plan["extracted_file_count"] == 2
        assert plan["extracted_byte_size"] == len("<settings />") + len("<addon />")
        assert plan["manifest"]["device_platform_family"] == "linux"

        unsafe_archive_path = os.path.join(temp_root, "unsafe.zip")
        write_zip(
            unsafe_archive_path,
            {
                "backup_manifest.json": (
                    '{"manifest_schema_version": 1, '
                    '"device_platform_family": "linux", '
                    '"kodi_version": "20.1 (20.1.0)", '
                    '"included_top_level_roots": ["userdata", "addons"]}'
                ),
                "userdata/../../outside.txt": "bad",
            },
        )
        unsafe_preflight = run_restore_preflight(
            runtime_paths,
            validate_restore_archive(unsafe_archive_path),
            disk_usage=lambda _path: type("Usage", (), {"free": 10_000_000})(),
            safety_buffer_bytes=0,
        )
        try:
            stage_restore_payload(runtime_paths, unsafe_preflight)
        except RestoreStageError as exc:
            assert "not safe to extract" in str(exc)
        else:
            raise AssertionError("Expected unsafe archive entry to fail restore staging.")

        unsupported_archive_path = os.path.join(temp_root, "unsupported.zip")
        write_zip(
            unsupported_archive_path,
            {
                "backup_manifest.json": (
                    '{"manifest_schema_version": 1, '
                    '"device_platform_family": "linux", '
                    '"kodi_version": "20.1 (20.1.0)", '
                    '"included_top_level_roots": ["userdata", "addons"]}'
                ),
                "other/file.txt": "bad",
            },
        )
        unsupported_preflight = run_restore_preflight(
            runtime_paths,
            validate_restore_archive(unsupported_archive_path),
            disk_usage=lambda _path: type("Usage", (), {"free": 10_000_000})(),
            safety_buffer_bytes=0,
        )
        try:
            stage_restore_payload(runtime_paths, unsupported_preflight)
        except RestoreStageError as exc:
            assert "unsupported entry" in str(exc)
        else:
            raise AssertionError("Expected unsupported archive entry to fail restore staging.")
    finally:
        shutil.rmtree(temp_root)

    print("restore staging ok")


if __name__ == "__main__":
    main()
