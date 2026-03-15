import importlib
import json
import os
import shutil
import sys
import tempfile
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class XbmcStub:
    def getCondVisibility(self, condition):
        return condition == "system.platform.linux"

    def getInfoLabel(self, label):
        if label == "System.BuildVersion":
            return "20.2 (20.2.0)"
        return ""


def load_manifest_module():
    sys.modules["xbmc"] = XbmcStub()
    module_name = "resources.lib.backup_manifest"
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def ensure_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-archive-")
    try:
        sys.modules["xbmc"] = XbmcStub()
        userdata_path = os.path.join(temp_root, "userdata")
        addons_path = os.path.join(temp_root, "addons")
        destination_path = os.path.join(temp_root, "Backup")
        os.makedirs(destination_path, exist_ok=True)

        ensure_file(os.path.join(userdata_path, "guisettings.xml"), "userdata")
        ensure_file(os.path.join(addons_path, "plugin.video.example", "addon.xml"), "addon")

        from resources.lib.backup_engine import collect_backup_entries, create_backup_archive

        manifest_module = load_manifest_module()
        collected = collect_backup_entries(
            {
                "userdata": userdata_path,
                "addons": addons_path,
            }
        )
        manifest = manifest_module.build_backup_manifest(
            addon_version="0.1.0",
            runtime_paths={
                "userdata": userdata_path,
                "addons": addons_path,
            },
            backup_stats=collected,
            cleanup_selections=[
                {"id": "thumbnails", "label": "Thumbnail cache", "selected": True}
            ],
            cleanup_results=[
                {"id": "thumbnails", "status": "removed"}
            ],
            created_timestamp="2026-03-15T12:00:00Z",
        )
        archive_path = create_backup_archive(destination_path, collected, manifest)

        assert os.path.basename(archive_path) == "KodiBackup-20260315-120000.zip"
        with zipfile.ZipFile(archive_path, "r") as archive:
            names = sorted(archive.namelist())
            assert names == [
                "addons/plugin.video.example/addon.xml",
                "backup_manifest.json",
                "userdata/guisettings.xml",
            ]
            manifest_data = json.loads(archive.read("backup_manifest.json").decode("utf-8"))
            assert manifest_data["file_count"] == 2
            assert manifest_data["uncompressed_byte_size"] == len("userdata") + len("addon")
            assert manifest_data["cleanup_selections_applied"] == [
                {"id": "thumbnails", "label": "Thumbnail cache", "status": "removed"}
            ]
    finally:
        shutil.rmtree(temp_root)

    print("backup archive ok")


if __name__ == "__main__":
    main()
