import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resources.lib.dialog import compose_dialog_text


def main():
    assert compose_dialog_text("Backup complete.") == "Backup complete."
    assert compose_dialog_text("Backup complete.", "", None, "Files backed up: 10") == (
        "Backup complete.[CR]Files backed up: 10"
    )
    assert compose_dialog_text("Line 1", "Line 2", "Line 3") == "Line 1[CR]Line 2[CR]Line 3"

    print("dialog text ok")


if __name__ == "__main__":
    main()
