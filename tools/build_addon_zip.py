import argparse
import os
import xml.etree.ElementTree as ET
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_ROOT_ITEMS = ("addon.py", "addon.xml", "resources")


class PackageBuildError(RuntimeError):
    pass


def _read_addon_metadata():
    addon_xml_path = os.path.join(REPO_ROOT, "addon.xml")
    try:
        root = ET.parse(addon_xml_path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise PackageBuildError(f"Could not read addon metadata from {addon_xml_path} ({exc})")

    addon_id = (root.attrib.get("id") or "").strip()
    addon_version = (root.attrib.get("version") or "").strip()
    if not addon_id:
        raise PackageBuildError("addon.xml is missing addon id.")
    if not addon_version:
        raise PackageBuildError("addon.xml is missing addon version.")

    return {
        "id": addon_id,
        "version": addon_version,
    }


def _iter_package_files():
    for item_name in PACKAGE_ROOT_ITEMS:
        item_path = os.path.join(REPO_ROOT, item_name)
        if not os.path.exists(item_path):
            raise PackageBuildError(f"Required package path is missing: {item_path}")

        if os.path.isdir(item_path):
            for current_root, dirnames, filenames in os.walk(item_path):
                dirnames[:] = sorted(
                    dirname
                    for dirname in dirnames
                    if dirname != "__pycache__"
                )
                for filename in sorted(filenames):
                    if filename.endswith(".pyc"):
                        continue
                    source_path = os.path.join(current_root, filename)
                    archive_path = os.path.relpath(source_path, REPO_ROOT).replace(os.sep, "/")
                    yield source_path, archive_path
        else:
            yield item_path, item_name


def build_addon_zip(output_dir):
    metadata = _read_addon_metadata()
    output_dir = os.path.abspath(output_dir)

    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as exc:
        raise PackageBuildError(f"Could not create output directory: {output_dir} ({exc})")

    archive_name = f"{metadata['id']}-{metadata['version']}.zip"
    archive_path = os.path.join(output_dir, archive_name)

    try:
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            for source_path, archive_path_name in _iter_package_files():
                archive.write(source_path, archive_path_name)
    except OSError as exc:
        raise PackageBuildError(f"Could not build addon zip: {archive_path} ({exc})")
    except zipfile.BadZipFile as exc:
        raise PackageBuildError(f"Could not write addon zip: {archive_path} ({exc})")

    return archive_path


def main():
    parser = argparse.ArgumentParser(
        description="Build an installable Kodi addon zip for KodiMirror."
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(REPO_ROOT, "dist"),
        help="Directory where the built zip should be written.",
    )
    args = parser.parse_args()

    archive_path = build_addon_zip(args.output_dir)
    print(archive_path)


if __name__ == "__main__":
    main()
