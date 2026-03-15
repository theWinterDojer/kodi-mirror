import json
import os
import shutil

from resources.lib.constants import (
    ADDON_ID,
    PENDING_RESTORE_PLAN_NAME,
    PENDING_RESTORE_PLAN_SCHEMA_VERSION,
)


REQUIRED_RESTORE_ROOTS = ("userdata", "addons")
EXCLUDED_RESTORE_PATHS = {
    "addons": (ADDON_ID,),
    "userdata": (os.path.join("addon_data", ADDON_ID),),
}


class RestoreApplyError(RuntimeError):
    def __init__(self, stage, message, path=None):
        self.stage = stage
        self.message = message
        self.path = path

        if path:
            formatted = f"{message}: {path}"
        else:
            formatted = message
        super().__init__(formatted)


def format_restore_apply_stage(stage):
    return stage.replace("_", " ").strip().capitalize()


def has_pending_restore(runtime_paths):
    plan_path = os.path.join(runtime_paths["restore_staging"], PENDING_RESTORE_PLAN_NAME)
    return os.path.isfile(plan_path)


def _load_pending_restore_plan(runtime_paths):
    staging_path = os.path.normpath(runtime_paths["restore_staging"])
    plan_path = os.path.join(staging_path, PENDING_RESTORE_PLAN_NAME)
    if not os.path.isfile(plan_path):
        raise RestoreApplyError("load_plan", "Pending restore plan is missing", plan_path)

    try:
        with open(plan_path, "r", encoding="utf-8") as handle:
            plan = json.load(handle)
    except OSError as exc:
        raise RestoreApplyError("load_plan", f"Could not read pending restore plan ({exc})", plan_path)
    except json.JSONDecodeError as exc:
        raise RestoreApplyError(
            "load_plan",
            f"Pending restore plan is not valid JSON ({exc})",
            plan_path,
        )

    if not isinstance(plan, dict):
        raise RestoreApplyError("validate_plan", "Pending restore plan must be a JSON object.")

    if plan.get("pending_restore_plan_schema_version") != PENDING_RESTORE_PLAN_SCHEMA_VERSION:
        raise RestoreApplyError(
            "validate_plan",
            "Pending restore plan schema version is not supported.",
            plan_path,
        )

    plan_staging_path = os.path.normpath((plan.get("staging_path") or "").strip())
    if plan_staging_path != staging_path:
        raise RestoreApplyError(
            "validate_plan",
            "Pending restore plan staging path does not match runtime paths.",
            plan_path,
        )

    payload_path = os.path.normpath((plan.get("payload_path") or "").strip())
    if not payload_path:
        raise RestoreApplyError("validate_plan", "Pending restore plan is missing payload_path.", plan_path)
    if os.path.commonpath([staging_path, payload_path]) != staging_path:
        raise RestoreApplyError(
            "validate_plan",
            "Pending restore payload path is not inside the staging directory.",
            payload_path,
        )
    if not os.path.isdir(payload_path):
        raise RestoreApplyError("validate_plan", "Pending restore payload is missing", payload_path)

    staged_root_paths = plan.get("staged_root_paths")
    if not isinstance(staged_root_paths, dict):
        raise RestoreApplyError("validate_plan", "Pending restore plan is missing staged_root_paths.", plan_path)

    target_root_paths = plan.get("target_root_paths")
    if not isinstance(target_root_paths, dict):
        raise RestoreApplyError("validate_plan", "Pending restore plan is missing target_root_paths.", plan_path)

    validated_staged_root_paths = {}
    validated_target_root_paths = {}
    for root_name in REQUIRED_RESTORE_ROOTS:
        staged_root_path = os.path.normpath((staged_root_paths.get(root_name) or "").strip())
        if not staged_root_path:
            raise RestoreApplyError(
                "validate_plan",
                f"Pending restore plan is missing staged root: {root_name}",
                plan_path,
            )
        if os.path.commonpath([payload_path, staged_root_path]) != payload_path:
            raise RestoreApplyError(
                "validate_plan",
                "Pending restore staged root is outside the payload path",
                staged_root_path,
            )
        if not os.path.isdir(staged_root_path):
            raise RestoreApplyError(
                "validate_plan",
                "Pending restore staged root is missing",
                staged_root_path,
            )
        validated_staged_root_paths[root_name] = staged_root_path

        target_root_path = os.path.normpath((target_root_paths.get(root_name) or "").strip())
        if not target_root_path:
            raise RestoreApplyError(
                "validate_plan",
                f"Pending restore plan is missing target root: {root_name}",
                plan_path,
            )
        runtime_root_path = os.path.normpath(runtime_paths[root_name])
        if target_root_path != runtime_root_path:
            raise RestoreApplyError(
                "validate_plan",
                f"Pending restore target root does not match runtime path for {root_name}.",
                target_root_path,
            )
        validated_target_root_paths[root_name] = target_root_path

    return {
        "plan": plan,
        "plan_path": plan_path,
        "payload_path": payload_path,
        "staged_root_paths": validated_staged_root_paths,
        "staging_path": staging_path,
        "target_root_paths": validated_target_root_paths,
    }


def _collect_tree_paths(root_path):
    directory_paths = set()
    file_paths = set()

    for current_root, dirnames, filenames in os.walk(root_path):
        relative_root = os.path.relpath(current_root, root_path)
        if relative_root == ".":
            relative_root = ""
        else:
            directory_paths.add(relative_root)

        for dirname in dirnames:
            current_path = os.path.join(current_root, dirname)
            if os.path.islink(current_path):
                raise RestoreApplyError(
                    "scan_payload",
                    "Restore payload contains an unsupported symlink",
                    current_path,
                )
            relative_path = os.path.join(relative_root, dirname) if relative_root else dirname
            directory_paths.add(relative_path)

        for filename in filenames:
            current_path = os.path.join(current_root, filename)
            if os.path.islink(current_path):
                raise RestoreApplyError(
                    "scan_payload",
                    "Restore payload contains an unsupported symlink",
                    current_path,
                )
            relative_path = os.path.join(relative_root, filename) if relative_root else filename
            file_paths.add(relative_path)

    return {
        "directories": directory_paths,
        "files": file_paths,
    }


def _is_excluded_restore_path(root_name, relative_path):
    normalized_path = os.path.normpath(relative_path or "")
    if normalized_path in ("", "."):
        return False

    excluded_prefixes = EXCLUDED_RESTORE_PATHS.get(root_name, ())
    for excluded_prefix in excluded_prefixes:
        normalized_prefix = os.path.normpath(excluded_prefix)
        if normalized_path == normalized_prefix:
            return True
        if normalized_path.startswith(normalized_prefix + os.sep):
            return True
    return False


def _ensure_target_root(target_root):
    if os.path.islink(target_root):
        try:
            os.remove(target_root)
        except OSError as exc:
            raise RestoreApplyError(
                "prepare_target_root",
                f"Could not replace target root ({exc})",
                target_root,
            )

    if os.path.exists(target_root) and not os.path.isdir(target_root):
        try:
            os.remove(target_root)
        except OSError as exc:
            raise RestoreApplyError(
                "prepare_target_root",
                f"Could not replace target root ({exc})",
                target_root,
            )

    try:
        os.makedirs(target_root, exist_ok=True)
    except OSError as exc:
        raise RestoreApplyError(
            "prepare_target_root",
            f"Could not create restore target root ({exc})",
            target_root,
        )


def _remove_extra_target_paths(root_name, target_root, staged_paths):
    removed_count = 0

    for current_root, dirnames, filenames in os.walk(target_root, topdown=False):
        relative_root = os.path.relpath(current_root, target_root)
        if relative_root == ".":
            relative_root = ""

        for filename in filenames:
            current_path = os.path.join(current_root, filename)
            relative_path = os.path.join(relative_root, filename) if relative_root else filename
            if _is_excluded_restore_path(root_name, relative_path):
                continue
            if relative_path in staged_paths["files"]:
                continue
            try:
                os.remove(current_path)
            except OSError as exc:
                raise RestoreApplyError(
                    "remove_target_file",
                    f"Could not remove restore target file ({exc})",
                    current_path,
                )
            removed_count += 1

        for dirname in dirnames:
            current_path = os.path.join(current_root, dirname)
            relative_path = os.path.join(relative_root, dirname) if relative_root else dirname
            if _is_excluded_restore_path(root_name, relative_path):
                continue
            if relative_path in staged_paths["directories"]:
                continue

            try:
                if os.path.islink(current_path):
                    os.remove(current_path)
                else:
                    shutil.rmtree(current_path)
            except OSError as exc:
                raise RestoreApplyError(
                    "remove_target_directory",
                    f"Could not remove restore target directory ({exc})",
                    current_path,
                )
            removed_count += 1

    return removed_count


def _apply_staged_root(root_name, staged_root, target_root):
    staged_paths = _collect_tree_paths(staged_root)
    _ensure_target_root(target_root)
    removed_count = _remove_extra_target_paths(root_name, target_root, staged_paths)
    copied_count = 0

    for relative_directory in sorted(staged_paths["directories"]):
        if _is_excluded_restore_path(root_name, relative_directory):
            continue
        target_directory = os.path.join(target_root, relative_directory)
        if os.path.islink(target_directory):
            try:
                os.remove(target_directory)
            except OSError as exc:
                raise RestoreApplyError(
                    "prepare_target_directory",
                    f"Could not replace restore target path ({exc})",
                    target_directory,
                )
            removed_count += 1
        elif os.path.exists(target_directory) and not os.path.isdir(target_directory):
            try:
                os.remove(target_directory)
            except OSError as exc:
                raise RestoreApplyError(
                    "prepare_target_directory",
                    f"Could not replace restore target path ({exc})",
                    target_directory,
                )
            removed_count += 1
        try:
            os.makedirs(target_directory, exist_ok=True)
        except OSError as exc:
            raise RestoreApplyError(
                "prepare_target_directory",
                f"Could not create restore target directory ({exc})",
                target_directory,
            )

    for relative_file in sorted(staged_paths["files"]):
        if _is_excluded_restore_path(root_name, relative_file):
            continue
        source_path = os.path.join(staged_root, relative_file)
        target_path = os.path.join(target_root, relative_file)
        parent_path = os.path.dirname(target_path)
        if parent_path:
            try:
                os.makedirs(parent_path, exist_ok=True)
            except OSError as exc:
                raise RestoreApplyError(
                    "prepare_target_directory",
                    f"Could not create restore target directory ({exc})",
                    parent_path,
                )

        if os.path.isdir(target_path) and not os.path.islink(target_path):
            try:
                shutil.rmtree(target_path)
            except OSError as exc:
                raise RestoreApplyError(
                    "copy_file",
                    f"Could not replace restore target directory ({exc})",
                    target_path,
                )
            removed_count += 1
        elif os.path.islink(target_path):
            try:
                os.remove(target_path)
            except OSError as exc:
                raise RestoreApplyError(
                    "copy_file",
                    f"Could not replace restore target path ({exc})",
                    target_path,
                )
            removed_count += 1

        try:
            shutil.copyfile(source_path, target_path)
        except OSError as exc:
            raise RestoreApplyError(
                "copy_file",
                f"Could not copy restore file ({exc})",
                target_path,
            )
        copied_count += 1

    return {
        "copied_file_count": copied_count,
        "removed_path_count": removed_count,
    }


def _clear_staging_directory(staging_path):
    try:
        entries = os.listdir(staging_path)
    except OSError as exc:
        raise RestoreApplyError(
            "cleanup_staging",
            f"Could not read restore staging directory ({exc})",
            staging_path,
        )

    for entry_name in entries:
        entry_path = os.path.join(staging_path, entry_name)
        try:
            if os.path.isdir(entry_path) and not os.path.islink(entry_path):
                shutil.rmtree(entry_path)
            else:
                os.remove(entry_path)
        except OSError as exc:
            raise RestoreApplyError(
                "cleanup_staging",
                f"Could not clear restore staging path after apply ({exc})",
                entry_path,
            )


def apply_pending_restore(runtime_paths):
    pending_restore = _load_pending_restore_plan(runtime_paths)
    copied_file_count = 0
    removed_path_count = 0

    for root_name in REQUIRED_RESTORE_ROOTS:
        result = _apply_staged_root(
            root_name,
            pending_restore["staged_root_paths"][root_name],
            pending_restore["target_root_paths"][root_name],
        )
        copied_file_count += result["copied_file_count"]
        removed_path_count += result["removed_path_count"]

    _clear_staging_directory(pending_restore["staging_path"])

    return {
        "archive_path": pending_restore["plan"].get("archive_path", ""),
        "copied_file_count": copied_file_count,
        "removed_path_count": removed_path_count,
    }
