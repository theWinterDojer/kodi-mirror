import xbmcgui

from resources.lib.constants import (
    CONTROL_ID_RESTORE_CONFIRM_CANCEL,
    CONTROL_ID_RESTORE_CONFIRM_START,
    MAIN_WINDOW_RESOLUTION,
    MAIN_WINDOW_SKIN,
    RESTORE_CONFIRM_WINDOW_XML,
)


class RestoreConfirmWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self._confirmed = False

    def onInit(self):
        self.setFocusId(CONTROL_ID_RESTORE_CONFIRM_START)

    def onClick(self, control_id):
        if control_id == CONTROL_ID_RESTORE_CONFIRM_START:
            self._confirmed = True
            self.close()
            return

        if control_id == CONTROL_ID_RESTORE_CONFIRM_CANCEL:
            self.close()
            return

    def onAction(self, action):
        if action.getId() in (
            xbmcgui.ACTION_NAV_BACK,
            xbmcgui.ACTION_PREVIOUS_MENU,
        ):
            self.close()
            return

        super().onAction(action)

    def is_confirmed(self):
        return self._confirmed


def open_restore_confirm_window(addon_path):
    window = RestoreConfirmWindow(
        RESTORE_CONFIRM_WINDOW_XML,
        addon_path,
        MAIN_WINDOW_SKIN,
        MAIN_WINDOW_RESOLUTION,
    )
    window.doModal()
    confirmed = window.is_confirmed()
    del window
    return confirmed
