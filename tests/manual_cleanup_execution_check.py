import os
import shutil
import sys
import tempfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resources.lib.cleanup import CleanupError, run_cleanup


def ensure_directory(path, filename):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, filename), "w", encoding="utf-8") as handle:
        handle.write("x")


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-cleanup-")
    try:
        remove_path = os.path.join(temp_root, "remove-me")
        skipped_path = os.path.join(temp_root, "missing")
        file_path = os.path.join(temp_root, "not-a-dir")

        ensure_directory(remove_path, "cache.bin")
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write("x")

        results = run_cleanup(
            [
                {
                    "id": "remove",
                    "label": "Remove target",
                    "path": remove_path,
                    "selected": True,
                },
                {
                    "id": "skip",
                    "label": "Skip target",
                    "path": skipped_path,
                    "selected": True,
                },
                {
                    "id": "not-selected",
                    "label": "Not selected",
                    "path": os.path.join(temp_root, "keep-me"),
                    "selected": False,
                },
            ]
        )

        assert results == [
            {
                "id": "remove",
                "label": "Remove target",
                "path": remove_path,
                "status": "removed",
            },
            {
                "id": "skip",
                "label": "Skip target",
                "path": skipped_path,
                "status": "skipped",
            },
        ]
        assert not os.path.exists(remove_path)

        try:
            run_cleanup(
                [
                    {
                        "id": "file-target",
                        "label": "File target",
                        "path": file_path,
                        "selected": True,
                    }
                ]
            )
            raise AssertionError("Expected non-directory cleanup target to fail.")
        except CleanupError as exc:
            assert "Could not remove cleanup target" in str(exc)
    finally:
        shutil.rmtree(temp_root)

    print("cleanup execution ok")


if __name__ == "__main__":
    main()
