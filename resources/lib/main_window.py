import xbmcgui

from resources.lib.constants import (
    CONTROL_ID_ADDONS_PATH,
    CONTROL_ID_BACKUP_DESTINATION_PATH,
    CONTROL_ID_BACKUP_DESTINATION_STATUS,
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
        self._destination_state = kwargs["destination_state"]
        self._runtime_paths = kwargs["runtime_paths"]

    def onInit(self):
        self.getControl(CONTROL_ID_USERDATA_PATH).setText(self._runtime_paths["userdata"])
        self.getControl(CONTROL_ID_ADDONS_PATH).setText(self._runtime_paths["addons"])
        self.getControl(CONTROL_ID_BACKUP_DESTINATION_PATH).setText(
            self._destination_state["path"] or "No default destination available."
        )
        destination_status = "Ready"
        if not self._destination_state["is_ready"]:
            destination_status = self._destination_state["error"]
        self.getControl(CONTROL_ID_BACKUP_DESTINATION_STATUS).setLabel(destination_status)
        self.setFocusId(CONTROL_ID_BACKUP)

    def onClick(self, control_id):
        if control_id == CONTROL_ID_CLOSE:
            self.close()
            return

        if control_id == CONTROL_ID_BACKUP:
            if not self._destination_state["is_ready"]:
                xbmcgui.Dialog().ok(
                    self._addon_name,
                    "Backup cannot start.",
                    self._destination_state["error"],
                )
                return

            xbmcgui.Dialog().ok(
                self._addon_name,
                "Backup is not implemented yet.",
                f"Default destination: {self._destination_state['path']}",
            )
            return
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


def open_main_window(addon_path, addon_name, runtime_paths, destination_state):
    window = MainWindow(
        MAIN_WINDOW_XML,
        addon_path,
        MAIN_WINDOW_SKIN,
        MAIN_WINDOW_RESOLUTION,
        addon_name=addon_name,
        destination_state=destination_state,
        runtime_paths=runtime_paths,
    )
    window.doModal()
    del window
