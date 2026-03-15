import os
import shutil
import sys
import tempfile
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


import resources.lib.restore_apply as restore_apply
from resources.lib.restore_archive import validate_restore_archive
from resources.lib.restore_preflight import run_restore_preflight
from resources.lib.restore_stage import stage_restore_payload


def write_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-restore-apply-fail-")
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
                "userdata/guisettings.xml": "<new-settings />",
                "addons/plugin.video.example/addon.xml": "<new-addon />",
            },
        )

        runtime_paths = {
            "userdata": os.path.join(temp_root, "live-userdata"),
            "addons": os.path.join(temp_root, "live-addons"),
            "restore_staging": os.path.join(temp_root, "pending_restore"),
        }
        os.makedirs(runtime_paths["restore_staging"], exist_ok=True)
        write_text(os.path.join(runtime_paths["userdata"], "old.txt"), "old")

        preflight = run_restore_preflight(
            runtime_paths,
            validate_restore_archive(archive_path),
            disk_usage=lambda _path: type("Usage", (), {"free": 10_000_000})(),
            safety_buffer_bytes=0,
        )
        stage_restore_payload(runtime_paths, preflight)

        original_copyfile = restore_apply.shutil.copyfile
        copy_calls = []

        def failing_copyfile(source_path, target_path):
            copy_calls.append(target_path)
            raise OSError("forced copy failure")

        restore_apply.shutil.copyfile = failing_copyfile
        try:
            try:
                restore_apply.apply_pending_restore(runtime_paths)
            except restore_apply.RestoreApplyError as exc:
                assert exc.stage == "copy_file"
                assert exc.path == copy_calls[0]
                assert "forced copy failure" in exc.message
            else:
                raise AssertionError("Expected restore apply failure.")
        finally:
            restore_apply.shutil.copyfile = original_copyfile

        assert len(copy_calls) == 1
        assert restore_apply.has_pending_restore(runtime_paths) is True
        assert os.path.isdir(os.path.join(runtime_paths["restore_staging"], "payload"))
        assert os.path.isfile(
            os.path.join(runtime_paths["restore_staging"], "pending_restore_plan.json")
        )
    finally:
        shutil.rmtree(temp_root)

    print("restore apply failure ok")


if __name__ == "__main__":
    main()
