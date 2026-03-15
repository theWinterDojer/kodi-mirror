import os
import shutil
import sys
import tempfile
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from resources.lib.restore_apply import apply_pending_restore, has_pending_restore
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


def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-restore-apply-")
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
                "userdata/addon_data/plugin.example/settings.xml": "<plugin-settings />",
                "userdata/addon_data/script.kodi.mirror/restore-state.json": '{"staged": true}',
                "addons/plugin.video.example/addon.xml": "<new-addon />",
                "addons/script.kodi.mirror/addon.xml": "<staged-self-addon />",
            },
        )

        runtime_paths = {
            "userdata": os.path.join(temp_root, "live-userdata"),
            "addons": os.path.join(temp_root, "live-addons"),
            "restore_staging": os.path.join(temp_root, "pending_restore"),
        }
        os.makedirs(runtime_paths["restore_staging"], exist_ok=True)
        write_text(
            os.path.join(runtime_paths["userdata"], "guisettings.xml"),
            "<old-settings />",
        )
        write_text(
            os.path.join(runtime_paths["userdata"], "obsolete.txt"),
            "remove-me",
        )
        write_text(
            os.path.join(runtime_paths["addons"], "plugin.video.example", "addon.xml"),
            "<old-addon />",
        )
        write_text(
            os.path.join(runtime_paths["addons"], "plugin.video.old", "addon.xml"),
            "<obsolete-addon />",
        )
        write_text(
            os.path.join(runtime_paths["userdata"], "addon_data", "script.kodi.mirror", "live.json"),
            '{"live": true}',
        )
        write_text(
            os.path.join(runtime_paths["userdata"], "addon_data", "script.kodi.mirror", "keep.txt"),
            "keep-me",
        )
        write_text(
            os.path.join(runtime_paths["addons"], "script.kodi.mirror", "addon.xml"),
            "<live-self-addon />",
        )
        write_text(
            os.path.join(runtime_paths["addons"], "script.kodi.mirror", "keep.txt"),
            "keep-me",
        )

        preflight = run_restore_preflight(
            runtime_paths,
            validate_restore_archive(archive_path),
            disk_usage=lambda _path: type("Usage", (), {"free": 10_000_000})(),
            safety_buffer_bytes=0,
        )
        stage_restore_payload(runtime_paths, preflight)

        assert has_pending_restore(runtime_paths) is True

        result = apply_pending_restore(runtime_paths)

        assert result["archive_path"] == archive_path
        assert result["copied_file_count"] == 3
        assert result["removed_path_count"] >= 2
        assert read_text(os.path.join(runtime_paths["userdata"], "guisettings.xml")) == "<new-settings />"
        assert read_text(
            os.path.join(
                runtime_paths["userdata"],
                "addon_data",
                "plugin.example",
                "settings.xml",
            )
        ) == "<plugin-settings />"
        assert read_text(
            os.path.join(runtime_paths["addons"], "plugin.video.example", "addon.xml")
        ) == "<new-addon />"
        assert read_text(
            os.path.join(runtime_paths["userdata"], "addon_data", "script.kodi.mirror", "live.json")
        ) == '{"live": true}'
        assert read_text(
            os.path.join(runtime_paths["addons"], "script.kodi.mirror", "addon.xml")
        ) == "<live-self-addon />"
        assert read_text(
            os.path.join(runtime_paths["userdata"], "addon_data", "script.kodi.mirror", "keep.txt")
        ) == "keep-me"
        assert read_text(
            os.path.join(runtime_paths["addons"], "script.kodi.mirror", "keep.txt")
        ) == "keep-me"
        assert not os.path.exists(os.path.join(runtime_paths["userdata"], "obsolete.txt"))
        assert not os.path.exists(os.path.join(runtime_paths["addons"], "plugin.video.old"))
        assert has_pending_restore(runtime_paths) is False
        assert os.listdir(runtime_paths["restore_staging"]) == []
    finally:
        shutil.rmtree(temp_root)

    print("restore apply ok")


if __name__ == "__main__":
    main()
