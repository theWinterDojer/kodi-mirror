import xbmcvfs

from resources.lib.constants import (
    RESTORE_STAGING_PATH,
    SPECIAL_ADDONS_PATH,
    SPECIAL_HOME_PATH,
    SPECIAL_MASTERPROFILE_PATH,
    SPECIAL_USERDATA_PATH,
)


class PathResolutionError(RuntimeError):
    pass


def _translate_special_path(path):
    translated = xbmcvfs.translatePath(path)
    if not translated:
        raise PathResolutionError(f"Could not resolve path: {path}")
    return translated


def _require_directory(path, label):
    if not xbmcvfs.exists(path):
        raise PathResolutionError(f"Required {label} path is missing: {path}")
    return path


def resolve_runtime_paths():
    paths = {
        "home": _translate_special_path(SPECIAL_HOME_PATH),
        "masterprofile": _translate_special_path(SPECIAL_MASTERPROFILE_PATH),
        "userdata": _translate_special_path(SPECIAL_USERDATA_PATH),
        "addons": _translate_special_path(SPECIAL_ADDONS_PATH),
        "restore_staging": _translate_special_path(RESTORE_STAGING_PATH),
    }

    _require_directory(paths["home"], "home")
    _require_directory(paths["masterprofile"], "masterprofile")
    _require_directory(paths["userdata"], "userdata")
    _require_directory(paths["addons"], "addons")

    return paths


def format_runtime_paths(paths):
    return [
        f"userdata: {paths['userdata']}",
        f"addons: {paths['addons']}",
    ]
