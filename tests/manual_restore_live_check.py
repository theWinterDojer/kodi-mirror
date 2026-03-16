import os
import shutil
import sys
import tempfile
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resources.lib.restore_archive import validate_restore_archive
from resources.lib.restore_live import apply_live_restore
from resources.lib.restore_preflight import run_restore_preflight


def write_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-restore-live-")
    try:
        archive_path = os.path.join(temp_root, "backup.zip")
        write_zip(
            archive_path,
            {
                "backup_manifest.json": (
                    '{"manifest_schema_version": 1, '
                    '"device_platform_family": "windows", '
                    '"kodi_version": "21.0 (21.0.0)", '
                    '"included_top_level_roots": ["userdata", "addons"]}'
                ),
                "userdata/guisettings.xml": "<new-settings />",
                "addons/plugin.video.example/addon.xml": "<new-addon />",
                "addons/script.kodi.mirror/addon.xml": "<self-addon />",
                "userdata/addon_data/script.kodi.mirror/state.json": '{"self": true}',
            },
        )

        runtime_paths = {
            "userdata": os.path.join(temp_root, "live-userdata"),
            "addons": os.path.join(temp_root, "live-addons"),
        }
        os.makedirs(runtime_paths["userdata"], exist_ok=True)
        os.makedirs(runtime_paths["addons"], exist_ok=True)

        with open(os.path.join(runtime_paths["userdata"], "old.txt"), "w", encoding="utf-8") as handle:
            handle.write("keep-me")

        preflight = run_restore_preflight(runtime_paths, validate_restore_archive(archive_path))
        result = apply_live_restore(runtime_paths, preflight)

        assert result["restored_file_count"] == 2
        assert result["skipped_file_count"] == 0
        assert read_text(os.path.join(runtime_paths["userdata"], "guisettings.xml")) == "<new-settings />"
        assert (
            read_text(os.path.join(runtime_paths["addons"], "plugin.video.example", "addon.xml"))
            == "<new-addon />"
        )
        assert read_text(os.path.join(runtime_paths["userdata"], "old.txt")) == "keep-me"
        assert not os.path.exists(os.path.join(runtime_paths["addons"], "script.kodi.mirror"))
        assert not os.path.exists(
            os.path.join(runtime_paths["userdata"], "addon_data", "script.kodi.mirror")
        )
    finally:
        shutil.rmtree(temp_root)

    print("restore live ok")


if __name__ == "__main__":
    main()
