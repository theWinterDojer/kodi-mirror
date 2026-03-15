import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resources.lib.backup_progress import BackupProgress


class FakeDialog:
    def __init__(self):
        self.events = []

    def create(self, heading, message):
        self.events.append(("create", heading, message))

    def update(self, percent, message):
        self.events.append(("update", percent, message))

    def close(self):
        self.events.append(("close",))


def main():
    dialog = FakeDialog()
    progress = BackupProgress(dialog)

    progress.start("Backup")
    progress.update(10, "Checking backup paths.")
    progress.update(50, "Collecting files for backup.")
    progress.close()

    assert dialog.events == [
        ("create", "Backup", "Starting backup."),
        ("update", 10, "Checking backup paths."),
        ("update", 50, "Collecting files for backup."),
        ("close",),
    ]

    print("backup progress ok")


if __name__ == "__main__":
    main()
