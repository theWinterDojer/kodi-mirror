import os
import sys
import tempfile
import shutil


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class XbmcStub:
    def getCondVisibility(self, _condition):
        return False

    def getInfoLabel(self, _label):
        return "20.2 (20.2.0)"


sys.modules["xbmc"] = XbmcStub()

from resources.lib.backup_engine import collect_backup_entries
from resources.lib.backup_preflight import run_backup_preflight


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-backup-self-exclusion-")
    try:
        userdata_path = os.path.join(temp_root, "userdata")
        addons_path = os.path.join(temp_root, "addons")
        destination_path = os.path.join(temp_root, "Backup")

        write_file(os.path.join(userdata_path, "guisettings.xml"), "userdata")
        write_file(os.path.join(addons_path, "plugin.video.example", "addon.xml"), "addon")
        write_file(
            os.path.join(
                userdata_path,
                "addon_data",
                "script.kodi.mirror",
                "pending_restore",
                "payload",
                "userdata",
                "stale.txt",
            ),
            "stale",
        )

        runtime_paths = {
            "userdata": userdata_path,
            "addons": addons_path,
        }
        destination_state = {
            "path": destination_path,
            "is_ready": True,
            "error": "",
            "source": "saved",
        }

        preflight = run_backup_preflight(
            runtime_paths,
            destination_state,
            disk_usage=lambda _path: type("Usage", (), {"free": 10_000_000})(),
            safety_buffer_bytes=0,
        )
        assert preflight["file_count"] == 2
        assert preflight["source_bytes"] == len("userdata") + len("addon")

        collected = collect_backup_entries(runtime_paths)
        assert collected["file_count"] == 2
        archive_paths = sorted(entry["archive_path"] for entry in collected["entries"])
        assert archive_paths == [
            "addons/plugin.video.example/addon.xml",
            "userdata/guisettings.xml",
        ]
    finally:
        shutil.rmtree(temp_root)

    print("backup self exclusion ok")


if __name__ == "__main__":
    main()
