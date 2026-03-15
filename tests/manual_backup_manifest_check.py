import importlib
import os
import sys
import types


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


def main():
    manifest_module = load_manifest_module()
    manifest = manifest_module.build_backup_manifest(
        addon_version="0.1.0",
        runtime_paths={
            "userdata": "/kodi/home/userdata",
            "addons": "/kodi/home/addons",
        },
        backup_stats={
            "file_count": 42,
            "source_bytes": 1024,
        },
        cleanup_selections=[
            {"id": "thumbnails", "label": "Thumbnail cache", "selected": True},
            {"id": "packages", "label": "Cached addon packages", "selected": True},
            {"id": "off", "label": "Off", "selected": False},
        ],
        cleanup_results=[
            {"id": "thumbnails", "status": "removed"},
            {"id": "packages", "status": "skipped"},
        ],
        created_timestamp="2026-03-15T12:00:00Z",
    )

    assert manifest["manifest_schema_version"] == 1
    assert manifest["addon_version"] == "0.1.0"
    assert manifest["created_timestamp"] == "2026-03-15T12:00:00Z"
    assert manifest["device_platform_family"] == "linux"
    assert manifest["kodi_version"] == "20.2 (20.2.0)"
    assert manifest["source_root_paths"] == {
        "userdata": "/kodi/home/userdata",
        "addons": "/kodi/home/addons",
    }
    assert manifest["cleanup_selections_applied"] == [
        {"id": "thumbnails", "label": "Thumbnail cache", "status": "removed"},
        {"id": "packages", "label": "Cached addon packages", "status": "skipped"},
    ]
    assert manifest["included_top_level_roots"] == ["userdata", "addons"]
    assert manifest["file_count"] == 42
    assert manifest["uncompressed_byte_size"] == 1024

    print("backup manifest ok")


if __name__ == "__main__":
    main()
