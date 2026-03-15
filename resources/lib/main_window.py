import xbmcgui

from resources.lib.constants import (
    CONTROL_ID_ADDONS_PATH,
    CONTROL_ID_BACKUP,
    CONTROL_ID_CLOSE,
    CONTROL_ID_RESTORE,
    CONTROL_ID_SETTINGS,
    CONTROL_ID_USERDATA_PATH,
    MAIN_WINDOW_RESOLUTION,
    MAIN_WINDOW_SKIN,
    MAIN_WINDOW_XML,
)


class MainWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self._addon_name = kwargs["addon_name"]
        self._runtime_paths = kwargs["runtime_paths"]

    def onInit(self):
        self.getControl(CONTROL_ID_USERDATA_PATH).setText(self._runtime_paths["userdata"])
        self.getControl(CONTROL_ID_ADDONS_PATH).setText(self._runtime_paths["addons"])
        self.setFocusId(CONTROL_ID_BACKUP)

    def onClick(self, control_id):
        if control_id == CONTROL_ID_CLOSE:
            self.close()
            return

        if control_id == CONTROL_ID_BACKUP:
            heading = "Backup"
        elif control_id == CONTROL_ID_RESTORE:
            heading = "Restore"
        elif control_id == CONTROL_ID_SETTINGS:
            heading = "Settings"
        else:
            return

        xbmcgui.Dialog().ok(self._addon_name, f"{heading} is not implemented yet.")

    def onAction(self, action):
        if action.getId() in (
            xbmcgui.ACTION_NAV_BACK,
            xbmcgui.ACTION_PREVIOUS_MENU,
        ):
            self.close()
            return

        super().onAction(action)


def open_main_window(addon_path, addon_name, runtime_paths):
    window = MainWindow(
        MAIN_WINDOW_XML,
        addon_path,
        MAIN_WINDOW_SKIN,
        MAIN_WINDOW_RESOLUTION,
        addon_name=addon_name,
        runtime_paths=runtime_paths,
    )
    window.doModal()
    del window
