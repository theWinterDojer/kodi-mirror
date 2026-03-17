import xbmcgui

from resources.lib.constants import (
    CLEANUP_WINDOW_XML,
    CONTROL_ID_CLEANUP_APPLY,
    CONTROL_ID_CLEANUP_CANCEL,
    CONTROL_ID_CLEANUP_ITEM_1,
    CONTROL_ID_CLEANUP_ITEM_2,
    CONTROL_ID_CLEANUP_ITEM_3,
    CONTROL_ID_CLEANUP_ITEM_4,
    CONTROL_ID_CLEANUP_SELECT_ALL,
    CONTROL_ID_CLEANUP_STATE_1,
    CONTROL_ID_CLEANUP_STATE_2,
    CONTROL_ID_CLEANUP_STATE_3,
    CONTROL_ID_CLEANUP_STATE_4,
    MAIN_WINDOW_RESOLUTION,
    MAIN_WINDOW_SKIN,
)


ITEM_CONTROL_IDS = (
    CONTROL_ID_CLEANUP_ITEM_1,
    CONTROL_ID_CLEANUP_ITEM_2,
    CONTROL_ID_CLEANUP_ITEM_3,
    CONTROL_ID_CLEANUP_ITEM_4,
)

STATE_CONTROL_IDS = (
    CONTROL_ID_CLEANUP_STATE_1,
    CONTROL_ID_CLEANUP_STATE_2,
    CONTROL_ID_CLEANUP_STATE_3,
    CONTROL_ID_CLEANUP_STATE_4,
)


class CleanupWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self._working_selections = [
            {
                "id": selection["id"],
                "label": selection["label"],
                "selected": selection["selected"],
            }
            for selection in kwargs["cleanup_selections"]
        ]
        self._selected_ids = None

    def onInit(self):
        self._refresh_display()
        self.setFocusId(CONTROL_ID_CLEANUP_ITEM_1)

    def _refresh_display(self):
        for selection, item_control_id, state_control_id in zip(
            self._working_selections,
            ITEM_CONTROL_IDS,
            STATE_CONTROL_IDS,
        ):
            self.getControl(item_control_id).setLabel(selection["label"])
            self.getControl(state_control_id).setLabel(
                "Selected" if selection["selected"] else "Off"
            )

    def _toggle_selection(self, control_id):
        selection_index = ITEM_CONTROL_IDS.index(control_id)
        self._working_selections[selection_index]["selected"] = not self._working_selections[
            selection_index
        ]["selected"]
        self._refresh_display()

    def _select_all(self):
        for selection in self._working_selections:
            selection["selected"] = True
        self._refresh_display()

    def _apply(self):
        self._selected_ids = {
            selection["id"]
            for selection in self._working_selections
            if selection["selected"]
        }
        self.close()

    def onClick(self, control_id):
        if control_id in ITEM_CONTROL_IDS:
            self._toggle_selection(control_id)
            return

        if control_id == CONTROL_ID_CLEANUP_SELECT_ALL:
            self._select_all()
            return

        if control_id == CONTROL_ID_CLEANUP_APPLY:
            self._apply()
            return

        if control_id == CONTROL_ID_CLEANUP_CANCEL:
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

    def get_selected_ids(self):
        return self._selected_ids


def open_cleanup_window(addon_path, cleanup_selections):
    window = CleanupWindow(
        CLEANUP_WINDOW_XML,
        addon_path,
        MAIN_WINDOW_SKIN,
        MAIN_WINDOW_RESOLUTION,
        cleanup_selections=cleanup_selections,
    )
    window.doModal()
    selected_ids = window.get_selected_ids()
    del window
    return selected_ids
