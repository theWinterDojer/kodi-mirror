import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resources.lib.restore_live import _filesystem_path


def main():
    normal_path = os.path.join("tmp", "restore", "target")
    assert _filesystem_path(normal_path, platform_name="posix") == os.path.normpath(normal_path)

    windows_path = r"C:\Kodi\addons\plugin.video.example\addon.dll"
    assert _filesystem_path(windows_path, platform_name="nt") == (
        r"\\?\C:\Kodi\addons\plugin.video.example\addon.dll"
    )

    print("restore live windows path ok")


if __name__ == "__main__":
    main()
