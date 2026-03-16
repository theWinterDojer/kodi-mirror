import os
import sys
import types


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


SPECIAL_PATHS = {
    "special://home/": "/kodi/home",
    "special://masterprofile/": "/kodi/masterprofile",
    "special://home/userdata/": "/kodi/home/userdata",
    "special://home/addons/": "/kodi/home/addons",
}


xbmc_module = types.SimpleNamespace(getInfoLabel=lambda _: "")
xbmcvfs_module = types.SimpleNamespace(
    translatePath=lambda path: SPECIAL_PATHS.get(path, ""),
    exists=lambda path: path in SPECIAL_PATHS.values(),
)

sys.modules["xbmc"] = xbmc_module
sys.modules["xbmcvfs"] = xbmcvfs_module

from resources.lib.paths import resolve_runtime_paths


def main():
    paths = resolve_runtime_paths()
    assert paths["userdata"] == "/kodi/home/userdata"
    assert paths["addons"] == "/kodi/home/addons"
    print("path resolution ok")


if __name__ == "__main__":
    main()
