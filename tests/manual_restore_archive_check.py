import os
import shutil
import sys
import tempfile
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from resources.lib.restore_archive import RestoreArchiveError, validate_restore_archive


def write_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def main():
    temp_root = tempfile.mkdtemp(prefix="kodimirror-restore-")
    try:
        valid_archive = os.path.join(temp_root, "valid.zip")
        write_zip(
            valid_archive,
            {
                "backup_manifest.json": '{"manifest_schema_version": 1}',
                "userdata/guisettings.xml": "<settings />",
            },
        )
        validation = validate_restore_archive(valid_archive)
        assert validation["path"] == valid_archive
        assert validation["entry_count"] == 2
        assert validation["manifest_name"] == "backup_manifest.json"

        missing_manifest_archive = os.path.join(temp_root, "missing-manifest.zip")
        write_zip(missing_manifest_archive, {"userdata/guisettings.xml": "<settings />"})
        try:
            validate_restore_archive(missing_manifest_archive)
        except RestoreArchiveError as exc:
            assert "missing backup_manifest.json" in str(exc)
        else:
            raise AssertionError("Expected missing manifest validation failure")

        invalid_archive = os.path.join(temp_root, "invalid.zip")
        with open(invalid_archive, "w", encoding="utf-8") as handle:
            handle.write("not a zip")
        try:
            validate_restore_archive(invalid_archive)
        except RestoreArchiveError as exc:
            assert "not a valid ZIP file" in str(exc)
        else:
            raise AssertionError("Expected invalid zip validation failure")
    finally:
        shutil.rmtree(temp_root)

    print("restore archive validation ok")


if __name__ == "__main__":
    main()
