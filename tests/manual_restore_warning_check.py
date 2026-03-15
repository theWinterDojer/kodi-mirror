import importlib
import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class XbmcStub:
    def __init__(self, build_version, platform_condition):
        self._build_version = build_version
        self._platform_condition = platform_condition

    def getCondVisibility(self, condition):
        return condition == self._platform_condition

    def getInfoLabel(self, label):
        if label == "System.BuildVersion":
            return self._build_version
        return ""


def load_restore_warning_module(stub):
    sys.modules["xbmc"] = stub
    module_name = "resources.lib.restore_warning"
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def main():
    module = load_restore_warning_module(
        XbmcStub("20.2 (20.2.0)", "system.platform.linux")
    )

    no_warning = module.build_restore_warnings(
        {
            "device_platform_family": "linux",
            "kodi_version": "20.1 (20.1.0)",
        }
    )
    assert no_warning["warnings"] == []

    platform_warning = module.build_restore_warnings(
        {
            "device_platform_family": "android",
            "kodi_version": "20.1 (20.1.0)",
        }
    )
    assert platform_warning["warnings"] == [
        "Platform differs: backup android, current linux."
    ]

    version_warning = module.build_restore_warnings(
        {
            "device_platform_family": "linux",
            "kodi_version": "21.0 (21.0.0)",
        }
    )
    assert version_warning["warnings"] == [
        "Kodi major differs: backup 21, current 20."
    ]

    combined_warning = module.build_restore_warnings(
        {
            "device_platform_family": "android",
            "kodi_version": "21.0 (21.0.0)",
        }
    )
    assert combined_warning["warnings"] == [
        "Platform differs: backup android, current linux.",
        "Kodi major differs: backup 21, current 20.",
    ]

    try:
        module.build_restore_warnings({"kodi_version": "20.1 (20.1.0)"})
    except module.RestoreWarningError as exc:
        assert "device_platform_family" in str(exc)
    else:
        raise AssertionError("Expected missing platform family to fail.")

    try:
        module.build_restore_warnings({"device_platform_family": "linux"})
    except module.RestoreWarningError as exc:
        assert "kodi_version" in str(exc)
    else:
        raise AssertionError("Expected missing kodi version to fail.")

    print("restore warning ok")


if __name__ == "__main__":
    main()
