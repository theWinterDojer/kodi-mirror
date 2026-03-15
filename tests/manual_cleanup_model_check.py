import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resources.lib.cleanup import build_cleanup_selections, format_cleanup_selections


def main():
    runtime_paths = {
        "userdata": "/kodi/home/userdata",
        "addons": "/kodi/home/addons",
    }

    selections = build_cleanup_selections(runtime_paths)
    assert len(selections) == 4
    assert all(selection["selected"] is True for selection in selections)
    assert selections[0]["path"] == os.path.normpath("/kodi/home/userdata/Thumbnails")
    assert selections[1]["path"] == os.path.normpath(
        "/kodi/home/userdata/addon_data/plugin.video.themoviedb.helper/blur_v2"
    )
    assert selections[2]["path"] == os.path.normpath(
        "/kodi/home/userdata/addon_data/plugin.video.themoviedb.helper/crop_v2"
    )
    assert selections[3]["path"] == os.path.normpath("/kodi/home/addons/packages")

    formatted = format_cleanup_selections(selections)
    assert formatted == [
        "[x] Thumbnail cache",
        "[x] TMDb Helper blur cache",
        "[x] TMDb Helper crop cache",
        "[x] Cached addon packages",
    ]

    print("cleanup model ok")


if __name__ == "__main__":
    main()
