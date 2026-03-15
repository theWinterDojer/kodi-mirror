import os
import sys
import xml.etree.ElementTree as ET


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resources.lib.constants import MAIN_WINDOW_XML, MAIN_WINDOW_RESOLUTION, MAIN_WINDOW_SKIN


def main():
    xml_path = os.path.join(
        REPO_ROOT,
        "resources",
        "skins",
        MAIN_WINDOW_SKIN,
        MAIN_WINDOW_RESOLUTION,
        MAIN_WINDOW_XML,
    )
    assert os.path.exists(xml_path), xml_path
    ET.parse(xml_path)
    print("ui asset ok")


if __name__ == "__main__":
    main()
