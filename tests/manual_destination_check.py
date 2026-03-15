import os
import shutil
import stat
import sys
import tempfile
import importlib


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class XbmcStub:
    def __init__(self, platform_family):
        self._platform_family = platform_family

    def getCondVisibility(self, condition):
        return condition == f"system.platform.{self._platform_family}"


def load_destination_module(platform_family):
    sys.modules["xbmc"] = XbmcStub(platform_family)
    module_name = "resources.lib.destination"
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def assert_default_paths():
    temp_home = tempfile.mkdtemp(prefix="kodimirror-home-")
    try:
        windows_destination = load_destination_module("windows")
        assert windows_destination.resolve_default_backup_destination(
            {"USERPROFILE": temp_home}
        ) == os.path.normpath(os.path.join(temp_home, "Backup"))

        linux_destination = load_destination_module("linux")
        assert linux_destination.resolve_default_backup_destination(
            {"HOME": temp_home}
        ) == os.path.normpath(os.path.join(temp_home, "Backup"))

        macos_destination = load_destination_module("osx")
        assert macos_destination.resolve_default_backup_destination(
            {"HOME": temp_home}
        ) == os.path.normpath(os.path.join(temp_home, "Backup"))

        android_destination = load_destination_module("android")
        assert (
            android_destination.resolve_default_backup_destination()
            == "/storage/emulated/0/Backup"
        )
    finally:
        shutil.rmtree(temp_home)


def assert_validation_behaviour():
    destination_module = load_destination_module("linux")
    temp_root = tempfile.mkdtemp(prefix="kodimirror-destination-")
    ready_destination = os.path.join(temp_root, "Backup")
    unwritable_destination = os.path.join(temp_root, "NoWrite")

    try:
        validated_path = destination_module.validate_backup_destination(ready_destination)
        assert validated_path == os.path.normpath(ready_destination)
        assert os.path.isdir(validated_path)

        os.makedirs(unwritable_destination, exist_ok=True)
        os.chmod(unwritable_destination, stat.S_IREAD | stat.S_IEXEC)

        try:
            destination_module.validate_backup_destination(unwritable_destination)
            raise AssertionError("Expected unwritable destination to fail validation.")
        except destination_module.DestinationError as exc:
            assert "not writable" in str(exc)
    finally:
        os.chmod(unwritable_destination, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        shutil.rmtree(temp_root)


def main():
    assert_default_paths()
    assert_validation_behaviour()
    print("destination checks ok")


if __name__ == "__main__":
    main()
