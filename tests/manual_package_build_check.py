import os
import shutil
import sys
import tempfile
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from tools.build_addon_zip import build_addon_zip


def main():
    output_dir = tempfile.mkdtemp(prefix="kodimirror-package-")
    try:
        archive_path = build_addon_zip(output_dir)
        assert os.path.basename(archive_path) == "script.kodi.mirror-0.1.0.zip"
        assert os.path.isfile(archive_path)

        with zipfile.ZipFile(archive_path, "r") as archive:
            names = set(archive.namelist())
            assert "addon.xml" in names
            assert "addon.py" in names
            assert "resources/lib/app.py" in names
            assert "resources/skins/default/1080i/script-kodi-mirror-main.xml" in names
            assert "docs/progress.md" not in names
            assert "tests/manual_package_build_check.py" not in names
            assert "addon_repo.xml" not in names

        print("package build ok")
    finally:
        shutil.rmtree(output_dir)


if __name__ == "__main__":
    main()
