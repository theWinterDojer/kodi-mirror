import os
import sys
import xml.etree.ElementTree as ET


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resources.lib.constants import (
    CLEANUP_WINDOW_XML,
    MAIN_WINDOW_RESOLUTION,
    MAIN_WINDOW_SKIN,
    MAIN_WINDOW_XML,
    RESTORE_CONFIRM_WINDOW_XML,
)


def _resolve_xml_path(xml_name):
    return os.path.join(
        REPO_ROOT,
        "resources",
        "skins",
        MAIN_WINDOW_SKIN,
        MAIN_WINDOW_RESOLUTION,
        xml_name,
    )


def _parse_xml(xml_path):
    assert os.path.exists(xml_path), xml_path
    tree = ET.parse(xml_path)
    return tree.getroot()


def _find_control_by_id(root, control_id):
    for control in root.findall(".//control"):
        if control.get("id") == str(control_id):
            return control
    raise AssertionError(f"expected control id {control_id}")


def main():
    main_xml_path = _resolve_xml_path(MAIN_WINDOW_XML)
    cleanup_xml_path = _resolve_xml_path(CLEANUP_WINDOW_XML)
    restore_confirm_xml_path = _resolve_xml_path(RESTORE_CONFIRM_WINDOW_XML)
    media_path = os.path.join(
        REPO_ROOT,
        "resources",
        "skins",
        MAIN_WINDOW_SKIN,
        "media",
        "solid-white.png",
    )
    assert os.path.exists(media_path), media_path
    root = _parse_xml(main_xml_path)

    image_controls = root.findall(".//control[@type='image']")
    assert image_controls, "expected image controls for backdrop and panels"

    fullscreen_backdrop = None
    modal_panel = None
    for control in image_controls:
        left = control.findtext("left")
        top = control.findtext("top")
        width = control.findtext("width")
        height = control.findtext("height")
        if left == "0" and top == "0" and width == "1920" and height == "1080":
            fullscreen_backdrop = control
        if left == "160" and top == "90" and width == "1600" and height == "900":
            modal_panel = control

    assert fullscreen_backdrop is not None, "expected fullscreen backdrop image control"
    assert modal_panel is not None, "expected centered modal panel image control"

    with open(main_xml_path, "r", encoding="utf-8") as xml_file:
        xml_text = xml_file.read()
    assert ">white.png<" not in xml_text
    assert "Backup Destination" not in xml_text
    assert "Restore stages" not in xml_text
    assert ">Flow<" not in xml_text
    assert "applies after restart" not in xml_text
    assert "Warnings are shown for platform or Kodi version differences." in xml_text
    assert "Archive Path" not in xml_text

    cleanup_root = _parse_xml(cleanup_xml_path)
    cleanup_image_controls = cleanup_root.findall(".//control[@type='image']")
    assert cleanup_image_controls, "expected cleanup window backdrop and panel images"

    cleanup_panel = None
    for control in cleanup_image_controls:
        left = control.findtext("left")
        top = control.findtext("top")
        width = control.findtext("width")
        height = control.findtext("height")
        if left == "300" and top == "140" and width == "1320" and height == "800":
            cleanup_panel = control

    assert cleanup_panel is not None, "expected centered cleanup modal panel image control"

    with open(cleanup_xml_path, "r", encoding="utf-8") as xml_file:
        cleanup_xml_text = xml_file.read()
    assert "Select all" in cleanup_xml_text
    assert ">Apply<" in cleanup_xml_text
    assert "Clear all" not in cleanup_xml_text
    assert "Apply cleanup selection" not in cleanup_xml_text

    restore_confirm_root = _parse_xml(restore_confirm_xml_path)
    restore_confirm_image_controls = restore_confirm_root.findall(".//control[@type='image']")
    assert restore_confirm_image_controls, "expected restore confirm backdrop and panel images"

    restore_confirm_panel = None
    for control in restore_confirm_image_controls:
        left = control.findtext("left")
        top = control.findtext("top")
        width = control.findtext("width")
        height = control.findtext("height")
        if left == "360" and top == "220" and width == "1200" and height == "520":
            restore_confirm_panel = control

    assert restore_confirm_panel is not None, "expected centered restore confirm modal panel image control"

    with open(restore_confirm_xml_path, "r", encoding="utf-8") as xml_file:
        restore_confirm_xml_text = xml_file.read()
    assert "The restore process can take a few minutes." in restore_confirm_xml_text
    assert "Please be patient." in restore_confirm_xml_text
    assert restore_confirm_xml_text.count(">Start restore<") == 2
    assert ">Cancel<" in restore_confirm_xml_text

    start_button = _find_control_by_id(restore_confirm_root, 1301)
    cancel_button = _find_control_by_id(restore_confirm_root, 1302)
    assert start_button.findtext("onup") == "1301"
    assert start_button.findtext("ondown") == "1301"
    assert start_button.findtext("onright") == "1302"
    assert cancel_button.findtext("onup") == "1302"
    assert cancel_button.findtext("ondown") == "1302"
    assert cancel_button.findtext("onleft") == "1301"
    print("ui asset ok")


if __name__ == "__main__":
    main()
