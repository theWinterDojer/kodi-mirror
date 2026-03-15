import os
import shutil
import sys
import tempfile
import types


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class XbmcStub:
    def getCondVisibility(self, _condition):
        return False


sys.modules["xbmc"] = XbmcStub()

from resources.lib.backup_preflight import BackupPreflightError, run_backup_preflight


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def build_runtime_paths(root_path):
    userdata_path = os.path.join(root_path, "userdata")
    addons_path = os.path.join(root_path, "addons")
    os.makedirs(userdata_path, exist_ok=True)
    os.makedirs(addons_path, exist_ok=True)

    write_file(os.path.join(userdata_path, "guisettings.xml"), "userdata")
    write_file(os.path.join(addons_path, "addon.txt"), "addons")

    return {
        "userdata": userdata_path,
        "addons": addons_path,
    }


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-preflight-")
    try:
        runtime_paths = build_runtime_paths(temp_root)
        destination_path = os.path.join(temp_root, "Backup")
        destination_state = {
            "path": destination_path,
            "is_ready": True,
            "error": "",
            "source": "saved",
        }

        success = run_backup_preflight(
            runtime_paths,
            destination_state,
            disk_usage=lambda _path: types.SimpleNamespace(free=10_000_000),
            safety_buffer_bytes=0,
        )
        assert success["destination_path"] == os.path.normpath(destination_path)
        assert success["file_count"] == 2
        assert success["source_bytes"] == len("userdata") + len("addons")

        try:
            run_backup_preflight(
                {
                    "userdata": os.path.join(temp_root, "missing-userdata"),
                    "addons": runtime_paths["addons"],
                },
                destination_state,
                disk_usage=lambda _path: types.SimpleNamespace(free=10_000_000),
                safety_buffer_bytes=0,
            )
            raise AssertionError("Expected missing userdata path to fail preflight.")
        except BackupPreflightError as exc:
            assert "userdata" in str(exc)

        try:
            run_backup_preflight(
                runtime_paths,
                {
                    "path": destination_path,
                    "is_ready": False,
                    "error": "Backup destination is not writable.",
                    "source": "saved",
                },
                disk_usage=lambda _path: types.SimpleNamespace(free=10_000_000),
                safety_buffer_bytes=0,
            )
            raise AssertionError("Expected invalid destination state to fail preflight.")
        except BackupPreflightError as exc:
            assert "not writable" in str(exc)

        try:
            run_backup_preflight(
                runtime_paths,
                destination_state,
                disk_usage=lambda _path: types.SimpleNamespace(free=1),
                safety_buffer_bytes=0,
            )
            raise AssertionError("Expected low free space to fail preflight.")
        except BackupPreflightError as exc:
            assert "Not enough free space" in str(exc)
    finally:
        shutil.rmtree(temp_root)

    print("backup preflight ok")


if __name__ == "__main__":
    main()
