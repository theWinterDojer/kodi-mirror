import os


CLEANUP_TARGETS = (
    {
        "id": "thumbnails",
        "label": "Thumbnail cache",
        "root_key": "userdata",
        "relative_path": "Thumbnails",
        "default_selected": True,
    },
    {
        "id": "tmdb_blur",
        "label": "TMDb Helper blur cache",
        "root_key": "userdata",
        "relative_path": "addon_data/plugin.video.themoviedb.helper/blur_v2",
        "default_selected": True,
    },
    {
        "id": "tmdb_crop",
        "label": "TMDb Helper crop cache",
        "root_key": "userdata",
        "relative_path": "addon_data/plugin.video.themoviedb.helper/crop_v2",
        "default_selected": True,
    },
    {
        "id": "addon_packages",
        "label": "Cached addon packages",
        "root_key": "addons",
        "relative_path": "packages",
        "default_selected": True,
    },
)


def build_cleanup_selections(runtime_paths):
    selections = []
    for target in CLEANUP_TARGETS:
        root_path = runtime_paths[target["root_key"]]
        selections.append(
            {
                "id": target["id"],
                "label": target["label"],
                "path": os.path.normpath(os.path.join(root_path, target["relative_path"])),
                "selected": target["default_selected"],
            }
        )
    return selections


def format_cleanup_selections(selections):
    return [
        f"[{'x' if selection['selected'] else ' '}] {selection['label']}"
        for selection in selections
    ]
