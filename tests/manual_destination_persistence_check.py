import importlib
import os
import shutil
import sys
import tempfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class XbmcStub:
    def __init__(self, platform_family):
        self._platform_family = platform_family

    def getCondVisibility(self, condition):
        return condition == f"system.platform.{self._platform_family}"


class FakeAddon:
    def __init__(self, settings=None):
        self._settings = settings or {}

    def getSetting(self, setting_id):
        return self._settings.get(setting_id, "")

    def setSetting(self, setting_id, value):
        self._settings[setting_id] = value


def load_destination_module(platform_family):
    sys.modules["xbmc"] = XbmcStub(platform_family)
    module_name = "resources.lib.destination"
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-persist-")
    try:
        destination_module = load_destination_module("linux")
        default_home = os.path.join(temp_root, "home")
        os.makedirs(default_home, exist_ok=True)

        addon = FakeAddon()
        default_state = destination_module.resolve_active_destination_state(
            addon,
            {"HOME": default_home},
        )
        assert default_state["source"] == "default"
        assert default_state["is_ready"] is True

        selected_path = os.path.join(temp_root, "custom-backup")
        saved_state = destination_module.save_selected_backup_destination(addon, selected_path)
        assert saved_state["source"] == "saved"
        assert addon.getSetting("backup_destination") == os.path.normpath(selected_path)

        restored_state = destination_module.resolve_active_destination_state(
            addon,
            {"HOME": default_home},
        )
        assert restored_state["source"] == "saved"
        assert restored_state["path"] == os.path.normpath(selected_path)
        assert restored_state["is_ready"] is True

        broken_path = os.path.join(temp_root, "not-a-directory")
        with open(broken_path, "w", encoding="utf-8") as handle:
            handle.write("x")
        addon.setSetting("backup_destination", broken_path)
        invalid_state = destination_module.resolve_active_destination_state(
            addon,
            {"HOME": default_home},
        )
        assert invalid_state["source"] == "saved"
        assert invalid_state["is_ready"] is False
        assert invalid_state["path"] == os.path.normpath(broken_path)
    finally:
        shutil.rmtree(temp_root)

    print("destination persistence ok")


if __name__ == "__main__":
    main()
