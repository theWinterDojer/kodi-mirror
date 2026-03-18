# KodiMirror Progress

Last updated: 2026-03-18

## Project Summary

This project is a Kodi-native Python addon that provides a simple, remote-friendly backup and restore workflow for Kodi users.

The addon is intended to replace confusing backup solutions with a direct "clone-style" tool that backs up the active Kodi installation state by packaging the active `userdata/` and `addons/` directories, with optional cleanup of selected cache folders before compression. Restore now uses a best-effort live apply workflow that overwrites restorable files in `userdata/` and `addons/`, skips locked or unwritable files, and reports what could not be replaced while Kodi is running.

Primary product goals:

- Keep the workflow simple enough to use from a TV remote.
- Back up the active Kodi profile without asking users to locate Kodi internals manually.
- Restore backups across devices with clear warnings where platform differences may affect addon compatibility.
- Prefer explicit behavior and hard failure over silent fallback when required paths or permissions are unavailable.

## Core Use

User installs the addon from our GitHub repo inside Kodi, launches it, optionally cleans selected cache folders, chooses a backup destination, creates a compressed archive, and can later restore that archive on the same or another Kodi device.

Core v1 use cases:

- Back up an existing Kodi setup before migrating devices.
- Restore a known-good Kodi setup after reinstalling Kodi.
- Clone a preferred Kodi configuration across multiple devices with the understanding that some addons may not remain functional on a different platform.

## Product Scope

### In Scope for v1

- Kodi-native addon implementation
- Backup of active `userdata/` and `addons/`
- Optional cleanup before backup for these paths only:
  - `userdata/Thumbnails`
  - `userdata/addon_data/plugin.video.themoviedb.helper/blur_v2`
  - `userdata/addon_data/plugin.video.themoviedb.helper/crop_v2`
  - `addons/packages`
- User-selectable backup destination
- Sensible default backup destination by platform
- ZIP archive creation in Python with compression level 6
- Restore flow that warns on platform or Kodi-version differences but still allows restore
- Simple status and confirmation messaging
- Remote-friendly navigation and layout

### Explicitly Out of Scope for v1

- Cloud sync
- Incremental backups
- Scheduling
- Selective per-addon restore
- Backward-compatibility layers for legacy backup formats
- Silent fallback to alternate paths when required permissions or destinations fail

## Technical Direction

### Addon Shape

Build this as a Kodi-native `script.*` addon launched directly inside Kodi.

Reasoning:

- The nearby `kodi-backup` desktop prototype is useful only as logic reference.
- A desktop GUI stack such as `customtkinter` is not relevant for a Kodi TV workflow.
- Kodi special paths give us better cross-platform behavior than OS-specific path guessing.

Implementation defaults locked for v1:

- addon id: `script.kodi.mirror`
- initial addon version: `0.1.0`
- addon type: Kodi script addon
- minimum target: Kodi 20+
- packaging format: Kodi addon zip containing a top-level `script.kodi.mirror/` folder with `addon.xml` inside it
- restore mode: best-effort live restore while KodiMirror is running

### Source Path Strategy

Do not detect Kodi source folders primarily by operating system path patterns.

Use Kodi special paths first:

- `special://home/`
- `special://masterprofile/`

The active source roots for backup are:

- `special://home/userdata/`
- `special://home/addons/`

This avoids most platform-specific Kodi path differences on Android, Fire TV, Windows, and Linux.

### Backup Destination Strategy

Default destination should be explicit and platform-aware:

- Android / Fire TV default: `/storage/emulated/0/Backup`
- Windows default: `%USERPROFILE%\\Backup`
- Linux default: `$HOME/Backup`
- macOS default: `$HOME/Backup`

Rules:

- Create the default `Backup` directory if it does not exist.
- If the destination is unavailable or not writable, show a clear error and require the user to browse to a valid location.
- Always provide a browse option so the user can override the default path.
- Remember the last valid user-selected destination and use it on future backups.
- Do not force the user to browse on every backup unless no valid saved destination exists.

Note:

`/storage/emulated/0` is a strong Android default, not a universal path for all Kodi platforms.

## User Experience Direction

### UI Principles

- Remote-friendly first
- Large targets and clear actions
- Low text density
- Black, blue, and white theme
- Simple informative messages only
- Avoid free-text entry unless necessary
- Explain preflight failures plainly before backup or restore starts

### Proposed v1 Navigation

Main menu:

- `Backup`
- `Restore`
- `Settings`

Backup flow:

1. Open backup screen.
2. Show cleanup options with defaults preselected.
3. Show destination path and browse action.
4. Show summary and confirmation.
5. Run cleanup, then backup, with progress updates.
6. Show success or failure message with archive location.

Restore flow:

1. Open restore screen.
2. Browse for backup archive.
3. Read metadata and validate archive.
4. If needed, show warnings when platform family or Kodi major version differs.
5. Apply the restore directly while KodiMirror is running.
6. Show a completion summary with restored and skipped files.

Settings flow:

- View or change default backup location
- No cleanup-preference persistence in v1; default cleanup selections are applied each time

### UI Implementation Approach

Use a small custom Kodi UI rather than chaining many stock dialogs.

Current preferred approach:

- One primary XML-backed window for the main workflow
- Dialogs only for confirmations, file browsing, and final results
- Progress dialog during backup and live restore

## Backup Model

### Backup Preflight Checks

Before backup starts, the addon should verify:

- source roots exist and are readable
- destination directory exists or can be created
- destination directory is writable
- enough free space is available for the expected archive write

Behavior:

- fail before cleanup or archive creation if a required preflight check fails
- show a short, explicit message describing what failed and what path was involved
- do not continue with partial backup setup after a failed preflight

### What a Backup Represents

A backup is a file-level snapshot of the active Kodi state, not a complete device image.

What it will generally preserve:

- Kodi settings
- addon settings and addon data
- installed addons
- skins and configuration
- databases stored in Kodi profile locations

What it will not guarantee:

- platform-specific binary addon compatibility across devices
- validity of hardcoded filesystem paths inside restored configs
- transferability of every token, credential, or external integration

Restore intent:

- restore is replace-style, not merge-style
- target `userdata/` and `addons/` should match the backup after apply, except for explicit self-exclusions for this addon

### Cleanup Behavior

Cleanup is optional and user-driven.

Default selected cleanup items:

- Thumbnail cache
- TMDb Helper blur cache
- TMDb Helper crop cache
- Cached addon packages

If a selected cleanup path does not exist, that is not an error. Report it as skipped or not present.

### Archive Format

Archive type:

- ZIP

Compression:

- Python `zipfile`
- `ZIP_DEFLATED`
- compression level `6`

Archive contents:

- `userdata/`
- `addons/`
- `backup_manifest.json` at archive root

Suggested filename format:

- `KodiBackup-YYYYMMDD-HHMMSS.zip`

Optional later variant if user naming is added:

- `KodiBackup-<label>-YYYYMMDD-HHMMSS.zip`

### Backup Metadata

Each archive should include a `backup_manifest.json` with:

- manifest schema version
- addon version
- created timestamp
- device platform family
- Kodi version
- source root paths used
- cleanup selections applied
- included top-level roots
- file count
- uncompressed byte size

Purpose:

- restore validation
- user-facing warnings
- future format evolution without guessing

## Restore Model

### Restore Policy

Restore should allow cross-device and cross-platform restore with warnings, not hard blocks.

Warn when:

- platform family differs
- Kodi major version differs

Warning language should state:

- restore will continue
- some addons may not work on the target device
- some files may stay unchanged if Kodi is using them

### Restore Safety Requirements

- Validate that the selected file is a supported backup archive
- Validate the presence and format of `backup_manifest.json`
- Protect against path traversal in archive entries
- Refuse to copy entries outside the intended Kodi destination
- Exclude this backup addon from live restore so the running addon does not overwrite itself
- Skip locked or unwritable files and report them clearly
- Do not delete the live `userdata/` or `addons/` roots before restore while Kodi is running

### Restore Preflight Checks

Before live restore starts, the addon should verify:

- selected archive exists and is readable
- archive format is supported
- `backup_manifest.json` exists and parses successfully
- live target roots exist or can be created
- live target roots are writable at the root level

Behavior:

- fail before live restore if a required preflight check fails
- show a short, explicit message describing the failure

### Restore Behavior

Restore target roots:

- active `special://home/userdata/`
- active `special://home/addons/`

Behavior:

- restore is applied live from the selected backup zip while KodiMirror is running
- overwrite files and create directories where possible for `userdata/` and `addons/`
- do not delete files that are absent from the backup during live restore
- skip files or directories that cannot be replaced because they are locked, unwritable, or otherwise unavailable
- report restored and skipped results explicitly

Restore self-exclusions:

- this addon's folder under `addons/<addon_id>/`
- this addon's data folder under `userdata/addon_data/<addon_id>/`

Restore flow detail:

1. User selects a backup zip.
2. Addon validates the archive and reads `backup_manifest.json`.
3. Addon warns on platform or Kodi-version mismatch.
4. If warnings are shown, the user acknowledges them and restore continues.
5. Addon applies the restore directly into live `userdata/` and `addons/`, skipping this addon's own files.
6. Addon shows a summary with restored and skipped counts plus a short skipped-file sample.

Known limitation:

Live restore is best-effort while Kodi is running. Locked files such as active addon binaries may remain unchanged and are reported as skipped instead of causing a full restore stop.

## Permissions and Platform Notes

### Android / Fire TV

- `/storage/emulated/0/Backup` is the preferred default destination
- path writability must be verified before use
- Kodi Android permissions may vary by version and device
- browse flow must remain available when the default path is not writable

### Windows

- Kodi source data is still resolved through Kodi special paths
- default backup destination is `%USERPROFILE%\\Backup`

### Linux

- same source-path rule: use Kodi special paths
- default backup destination is `$HOME/Backup`

### macOS

- same source-path rule: use Kodi special paths
- default backup destination is `$HOME/Backup`

## Tech Stack

- Python 3 as supported by the target Kodi version
- Kodi addon packaging
- target Kodi baseline: Kodi 20+
- `addon.xml`
- Kodi APIs:
  - `xbmc`
  - `xbmcgui`
  - `xbmcaddon`
  - `xbmcvfs`
- Python standard library:
  - `os`
  - `json`
  - `zipfile`
  - `shutil`
  - `tempfile` if needed for restore staging
  - `datetime`

Expected repo contents:

- addon manifest and metadata
- addon entrypoint
- backup engine
- restore engine
- Kodi UI window/dialog code
- XML layout assets
- art assets for icon/fanart/theme
- minimal docs for installation and usage

## Important Context

- This repo is currently effectively empty aside from `AGENTS.md`.
- The nearby `/home/dojer/projects/kodi-backup` project is a reference only, not a base to extend.
- The goal is a fresh Kodi-native implementation.
- Simplicity is a hard constraint. Do not add speculative features or compatibility layers.
- The product is intended for TV use, so remote navigation quality matters more than desktop-style convenience.
- Full file-level backup of `userdata/` and `addons/` is the correct cloning model for v1.
- Cross-platform restore is allowed even though addon compatibility cannot be guaranteed.

## Risks and Assumptions

### Assumptions

- Kodi special paths are available and reliable on target platforms.
- Python ZIP compression level 6 is supported in the target Kodi Python runtime.
- Users can grant enough storage access on Android/Fire TV for the selected destination.

### Known Risks

- Some Android / Fire TV environments may restrict destination access more than expected.
- A live restore can skip files that Kodi keeps open while the application is running.
- Restoring platform-specific addons to another platform may produce broken addons after restore.
- Large backups may take long enough that progress reporting needs to be carefully designed to avoid the appearance of hanging.

## Validation Strategy

Validate the smallest effective surface for each phase.

Planned validation:

- local syntax and import validation for Python modules
- archive structure verification with a test backup
- restore validation against a controlled sample archive
- manual UI navigation test inside Kodi
- manual permission-path validation on at least one Android-class device and one desktop platform

Do not defer all validation to the end.

## Full Implementation Plan

### Phase 1: Addon Skeleton and Foundation

Goal:

Create a minimal installable Kodi addon that launches correctly and can resolve its runtime paths.

Deliverables:

- addon id, name, version, and manifest
- addon entrypoint
- basic icon/fanart placeholders
- minimal main menu window or initial dialog flow
- utility module for logging and path resolution

Definition of done:

- addon installs from a zip package
- addon launches inside Kodi without traceback
- source paths for active `userdata` and `addons` resolve correctly

### Phase 2: Destination and Settings Handling

Goal:

Implement destination selection and default-path logic cleanly.

Deliverables:

- platform-aware default destination resolution
- writability checks
- browse action
- persisted addon setting for preferred destination only
- destination preflight primitives usable by backup flow

Definition of done:

- addon can show default destination
- addon can create the destination folder when valid
- addon can reject invalid or unwritable destinations with a clear message
- addon reuses the last valid selected destination on the next backup

### Phase 3: Cleanup Engine

Goal:

Implement the pre-backup cleanup step for the four approved targets only.

Deliverables:

- cleanup target definitions
- selection state handling
- deletion logic
- user-facing cleanup summary

Definition of done:

- selected cache targets are removed when present
- missing targets are reported without failure
- cleanup results are included in backup metadata

### Phase 4: Backup Engine

Goal:

Create the archive correctly and efficiently.

Deliverables:

- backup preflight checks for source readability, destination readiness, and basic free-space validation
- recursive file collection for `userdata/` and `addons/`
- zip creation with compression level 6
- `backup_manifest.json`
- file counting and size tracking
- progress updates

Definition of done:

- backup fails early with a clear message if preflight fails
- a backup zip is produced successfully
- archive contains expected directory roots
- manifest reflects the actual backup

### Phase 5: Restore Engine

Goal:

Restore a supported archive back into the active Kodi environment safely.

Deliverables:

- archive validation
- manifest parsing
- warning logic for platform family and Kodi major mismatch
- restore preflight checks for archive readability, manifest validity, and live target-root readiness
- path-safe live restore apply direct from the selected zip
- self-exclusion for this addon during live restore
- skip tracking for locked or unwritable files
- failure reporting and clear live-restore completion messaging

Definition of done:

- restore fails early with a clear message if preflight fails
- a valid backup can be applied live into a test environment
- unsafe archive entries are rejected
- locked or unwritable files are skipped and reported clearly without stopping the entire restore

### Phase 6: UI Polish

Goal:

Make the addon genuinely pleasant to use on a TV.

Deliverables:

- black / blue / white visual treatment
- large readable controls
- simplified wording
- progress and completion messaging

Definition of done:

- navigation works well with a remote
- no screen requires dense text entry for the normal path
- messages are short, direct, and informative

### Phase 7: Packaging and Documentation

Goal:

Make the addon installable from the GitHub repo and document only what users need.

Deliverables:

- build/package process for addon zip
- install instructions
- concise README
- versioning approach

Definition of done:

- a user can install the addon from the packaged artifact
- repo docs accurately describe the current product

## Execution Task List

Priority order below should be followed unless a blocker forces reordering.

- [x] `CP-001` Define addon identity, packaging format, and Kodi version target.
- [x] `CP-002` Create addon skeleton with `addon.xml`, entrypoint, and base module layout.
- [x] `CP-003` Implement runtime path resolution using Kodi special paths for source roots.
- [x] `CP-004` Decide and implement main UI structure: primary XML window plus supporting dialogs.
- [x] `CP-005` Define destination path policy by platform and implement writability checks.
- [x] `CP-006` Implement browse/select destination flow and persistence of the last valid destination.
- [x] `CP-007` Implement backup preflight checks for source readability, destination readiness, and basic free-space validation.
- [x] `CP-008` Implement cleanup option model and defaults for the four approved paths.
- [x] `CP-009` Implement cleanup execution and cleanup-result reporting.
- [x] `CP-010` Define backup archive layout and `backup_manifest.json` schema.
- [x] `CP-011` Implement backup file walk, filtering, and zip creation with compression level 6.
- [x] `CP-012` Implement backup progress reporting and success/failure summaries.
- [x] `CP-013` Implement restore archive selection and archive validation.
- [x] `CP-014` Implement restore preflight checks for archive readability, manifest validity, and live target-root readiness.
- [x] `CP-015` Implement manifest parsing and restore warning logic for platform/Kodi mismatch.
- [x] `CP-016` Implement live restore archive iteration and direct file apply into `userdata/` and `addons/`.
- [x] `CP-017` Implement overwrite-only live restore behavior without destructive full-root delete.
- [x] `CP-018` Exclude this addon's own addon folder and addon_data folder from live restore.
- [x] `CP-019` Implement skip/report handling for locked or unwritable live-restore files.
- [x] `CP-020` Implement clear user messaging for live restore warnings and completion.
- [x] `CP-021` Apply black / blue / white Kodi UI styling and remote-friendly layout polish.
- [x] `CP-022` Package addon into an installable zip for GitHub distribution.
- [x] `CP-023` Write evergreen README with install and use instructions only.
- [x] `CP-024` Run targeted validation for backup flow on one desktop platform.
- [ ] `CP-025` Run targeted validation for destination and permission behavior on Android / Fire TV class hardware.
- [ ] `CP-026` Run targeted validation for live restore behavior and cross-platform warning messaging.
- [ ] `CP-027` Prepare first release candidate and record known limitations.

## Current Status

Current phase:

- Phase 7: Packaging and Documentation

Current decisions already made:

- Build from scratch as a Kodi-native addon
- Use addon id `script.kodi.mirror`
- Use initial addon version `0.1.0`
- Target Kodi 20+
- Package the addon as a Kodi zip containing a top-level `script.kodi.mirror/` folder with `addon.xml` inside it
- Back up active `userdata/` and `addons/`
- Allow full restore across platforms with warning
- Use `/storage/emulated/0/Backup` as the Android / Fire TV default destination
- Use `%USERPROFILE%\\Backup` as the Windows default destination
- Use `$HOME/Backup` as the Linux and macOS default destination
- Use explicit browse override plus persistence of the last valid destination
- Use ZIP compression level 6
- Use best-effort live restore with overwrite-only semantics while KodiMirror is running
- Skip and report locked or unwritable restore targets instead of failing the whole restore
- Exclude this addon from live restore to avoid self-overwrite during the running operation

Open items to resolve before implementation starts:

- None. The implementation plan is locked for v1.

## QA Ledger

### 2026-03-15

- `CP-001`: parsed `addon.xml` with `python3 -c "import xml.etree.ElementTree as ET; ET.parse('addon.xml')"`
- `CP-001`: verified packaging baseline files with `rg --files`
- `CP-002`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/constants.py resources/lib/log.py`
- `CP-002`: verified skeleton file layout with `rg --files`
- `CP-003`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/constants.py resources/lib/log.py resources/lib/paths.py`
- `CP-003`: exercised path resolution with a stubbed Kodi runtime via `python3 tests/manual_path_resolution_check.py`
- `CP-004`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/constants.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py tests/manual_path_resolution_check.py tests/manual_ui_asset_check.py`
- `CP-004`: verified main window XML asset with `python3 tests/manual_ui_asset_check.py`
- `CP-005`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py tests/manual_destination_check.py tests/manual_path_resolution_check.py tests/manual_ui_asset_check.py`
- `CP-005`: exercised default destination policy and writability checks with `python3 tests/manual_destination_check.py`
- `CP-005`: re-ran path and UI regression checks with `python3 tests/manual_path_resolution_check.py` and `python3 tests/manual_ui_asset_check.py`
- `CP-006`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_ui_asset_check.py`
- `CP-006`: exercised saved-destination persistence and invalid-saved-path handling with `python3 tests/manual_destination_persistence_check.py`
- `CP-006`: re-ran destination, path, and UI regression checks with `python3 tests/manual_destination_check.py`, `python3 tests/manual_path_resolution_check.py`, and `python3 tests/manual_ui_asset_check.py`
- `CP-007`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_preflight.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py tests/manual_backup_preflight_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_ui_asset_check.py`
- `CP-007`: exercised backup preflight success and failure cases with `python3 tests/manual_backup_preflight_check.py`
- `CP-007`: re-ran destination, persistence, path, and UI regression checks with `python3 tests/manual_destination_check.py`, `python3 tests/manual_destination_persistence_check.py`, `python3 tests/manual_path_resolution_check.py`, and `python3 tests/manual_ui_asset_check.py`
- `CP-008`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_preflight.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py tests/manual_backup_preflight_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_ui_asset_check.py`
- `CP-008`: exercised cleanup target defaults and resolved paths with `python3 tests/manual_cleanup_model_check.py`
- `CP-008`: re-ran preflight, destination, persistence, path, and UI regression checks with `python3 tests/manual_backup_preflight_check.py`, `python3 tests/manual_destination_check.py`, `python3 tests/manual_destination_persistence_check.py`, `python3 tests/manual_path_resolution_check.py`, and `python3 tests/manual_ui_asset_check.py`
- `CP-009`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_preflight.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py tests/manual_backup_preflight_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_ui_asset_check.py`
- `CP-009`: exercised cleanup execution, missing-path skip behavior, and delete-failure handling with `python3 tests/manual_cleanup_execution_check.py`
- `CP-009`: re-ran cleanup model, preflight, destination, persistence, path, and UI regression checks with `python3 tests/manual_cleanup_model_check.py`, `python3 tests/manual_backup_preflight_check.py`, `python3 tests/manual_destination_check.py`, `python3 tests/manual_destination_persistence_check.py`, `python3 tests/manual_path_resolution_check.py`, and `python3 tests/manual_ui_asset_check.py`
- `CP-010`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py tests/manual_backup_manifest_check.py tests/manual_backup_preflight_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_ui_asset_check.py`
- `CP-010`: exercised backup manifest field construction and schema shape with `python3 tests/manual_backup_manifest_check.py`
- `CP-010`: re-ran cleanup execution, cleanup model, preflight, destination, persistence, path, and UI regression checks with `python3 tests/manual_cleanup_execution_check.py`, `python3 tests/manual_cleanup_model_check.py`, `python3 tests/manual_backup_preflight_check.py`, `python3 tests/manual_destination_check.py`, `python3 tests/manual_destination_persistence_check.py`, `python3 tests/manual_path_resolution_check.py`, and `python3 tests/manual_ui_asset_check.py`
- `CP-011`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_engine.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py tests/manual_backup_archive_check.py tests/manual_backup_manifest_check.py tests/manual_backup_preflight_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_ui_asset_check.py`
- `CP-011`: exercised archive structure, manifest placement, and backup filename format with `python3 tests/manual_backup_archive_check.py`
- `CP-011`: re-ran manifest, cleanup execution, cleanup model, preflight, destination, persistence, path, and UI regression checks with `python3 tests/manual_backup_manifest_check.py`, `python3 tests/manual_cleanup_execution_check.py`, `python3 tests/manual_cleanup_model_check.py`, `python3 tests/manual_backup_preflight_check.py`, `python3 tests/manual_destination_check.py`, `python3 tests/manual_destination_persistence_check.py`, `python3 tests/manual_path_resolution_check.py`, and `python3 tests/manual_ui_asset_check.py`
- `CP-012`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_engine.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/backup_progress.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py tests/manual_backup_archive_check.py tests/manual_backup_manifest_check.py tests/manual_backup_preflight_check.py tests/manual_backup_progress_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_ui_asset_check.py`
- `CP-012`: exercised backup progress dialog helper behavior with `python3 tests/manual_backup_progress_check.py`
- `CP-012`: re-ran archive, manifest, cleanup execution, cleanup model, preflight, destination, persistence, path, and UI regression checks with `python3 tests/manual_backup_archive_check.py`, `python3 tests/manual_backup_manifest_check.py`, `python3 tests/manual_cleanup_execution_check.py`, `python3 tests/manual_cleanup_model_check.py`, `python3 tests/manual_backup_preflight_check.py`, `python3 tests/manual_destination_check.py`, `python3 tests/manual_destination_persistence_check.py`, `python3 tests/manual_path_resolution_check.py`, and `python3 tests/manual_ui_asset_check.py`
- `CP-013`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_engine.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/backup_progress.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py resources/lib/restore_archive.py tests/manual_backup_archive_check.py tests/manual_backup_manifest_check.py tests/manual_backup_preflight_check.py tests/manual_backup_progress_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_restore_archive_check.py tests/manual_ui_asset_check.py`
- `CP-013`: exercised restore archive validation success and unsupported-archive failures with `python3 tests/manual_restore_archive_check.py`
- `CP-013`: re-ran backup archive and manifest regression checks with `python3 tests/manual_backup_archive_check.py` and `python3 tests/manual_backup_manifest_check.py`
- `CP-014`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_engine.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/backup_progress.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py resources/lib/restore_archive.py resources/lib/restore_preflight.py tests/manual_backup_archive_check.py tests/manual_backup_manifest_check.py tests/manual_backup_preflight_check.py tests/manual_backup_progress_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_restore_archive_check.py tests/manual_restore_preflight_check.py tests/manual_ui_asset_check.py`
- `CP-014`: exercised restore preflight success, invalid-manifest failure, missing-root failure, and low-free-space failure with `python3 tests/manual_restore_preflight_check.py`
- `CP-014`: re-ran restore archive and backup archive-contract regression checks with `python3 tests/manual_restore_archive_check.py`, `python3 tests/manual_backup_archive_check.py`, and `python3 tests/manual_backup_manifest_check.py`
- `CP-015`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_engine.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/backup_progress.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py resources/lib/restore_archive.py resources/lib/restore_preflight.py resources/lib/restore_warning.py tests/manual_backup_archive_check.py tests/manual_backup_manifest_check.py tests/manual_backup_preflight_check.py tests/manual_backup_progress_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_restore_archive_check.py tests/manual_restore_preflight_check.py tests/manual_restore_warning_check.py tests/manual_ui_asset_check.py`
- `CP-015`: exercised no-warning, platform-mismatch warning, Kodi-major-mismatch warning, combined-warning, and missing-manifest-field failures with `python3 tests/manual_restore_warning_check.py`
- `CP-015`: re-ran restore preflight, restore archive, and backup manifest regressions with `python3 tests/manual_restore_preflight_check.py`, `python3 tests/manual_restore_archive_check.py`, and `python3 tests/manual_backup_manifest_check.py`
- `CP-016`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_engine.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/backup_progress.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py resources/lib/restore_archive.py resources/lib/restore_preflight.py resources/lib/restore_stage.py resources/lib/restore_warning.py tests/manual_backup_archive_check.py tests/manual_backup_manifest_check.py tests/manual_backup_preflight_check.py tests/manual_backup_progress_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_restore_archive_check.py tests/manual_restore_preflight_check.py tests/manual_restore_stage_check.py tests/manual_restore_warning_check.py tests/manual_ui_asset_check.py`
- `CP-016`: exercised staged extraction success, stale-staging cleanup, pending-plan creation, unsafe-entry failure, and unsupported-entry failure with `python3 tests/manual_restore_stage_check.py`
- `CP-016`: re-ran restore warning, restore preflight, restore archive, backup manifest, and backup archive regressions with `python3 tests/manual_restore_warning_check.py`, `python3 tests/manual_restore_preflight_check.py`, `python3 tests/manual_restore_archive_check.py`, `python3 tests/manual_backup_manifest_check.py`, and `python3 tests/manual_backup_archive_check.py`
- `CP-017`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_engine.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/backup_progress.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py resources/lib/restore_apply.py resources/lib/restore_archive.py resources/lib/restore_preflight.py resources/lib/restore_stage.py resources/lib/restore_warning.py tests/manual_backup_archive_check.py tests/manual_backup_manifest_check.py tests/manual_backup_preflight_check.py tests/manual_backup_progress_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_restore_apply_check.py tests/manual_restore_archive_check.py tests/manual_restore_preflight_check.py tests/manual_restore_stage_check.py tests/manual_restore_warning_check.py tests/manual_ui_asset_check.py`
- `CP-017`: exercised pending-plan detection, replace-style apply, target cleanup of paths absent from the backup, and staging cleanup after success with `python3 tests/manual_restore_apply_check.py`
- `CP-017`: re-ran restore staging, restore warning, restore preflight, restore archive, and backup manifest regressions with `python3 tests/manual_restore_stage_check.py`, `python3 tests/manual_restore_warning_check.py`, `python3 tests/manual_restore_preflight_check.py`, `python3 tests/manual_restore_archive_check.py`, and `python3 tests/manual_backup_manifest_check.py`
- `CP-018`: compiled Python modules with `python3 -m py_compile resources/lib/restore_apply.py tests/manual_restore_apply_check.py`
- `CP-018`: exercised self-exclusion of this addon's addon folder and addon_data folder while preserving normal replace-style apply for other paths with `python3 tests/manual_restore_apply_check.py`
- `CP-018`: re-ran restore staging, restore warning, restore preflight, restore archive, and backup manifest regressions with `python3 tests/manual_restore_stage_check.py`, `python3 tests/manual_restore_warning_check.py`, `python3 tests/manual_restore_preflight_check.py`, `python3 tests/manual_restore_archive_check.py`, and `python3 tests/manual_backup_manifest_check.py`
- `CP-019`: compiled Python modules with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_engine.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/backup_progress.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py resources/lib/restore_apply.py resources/lib/restore_archive.py resources/lib/restore_preflight.py resources/lib/restore_stage.py resources/lib/restore_warning.py tests/manual_backup_archive_check.py tests/manual_backup_manifest_check.py tests/manual_backup_preflight_check.py tests/manual_backup_progress_check.py tests/manual_cleanup_execution_check.py tests/manual_cleanup_model_check.py tests/manual_destination_check.py tests/manual_destination_persistence_check.py tests/manual_path_resolution_check.py tests/manual_restore_apply_check.py tests/manual_restore_apply_failure_check.py tests/manual_restore_archive_check.py tests/manual_restore_preflight_check.py tests/manual_restore_stage_check.py tests/manual_restore_warning_check.py tests/manual_ui_asset_check.py`
- `CP-019`: exercised fail-fast restore-apply failure reporting with stage/path context and verified pending staging remains after failure with `python3 tests/manual_restore_apply_failure_check.py`
- `CP-019`: re-ran restore apply success, restore staging, restore warning, restore preflight, restore archive, and backup manifest regressions with `python3 tests/manual_restore_apply_check.py`, `python3 tests/manual_restore_stage_check.py`, `python3 tests/manual_restore_warning_check.py`, `python3 tests/manual_restore_preflight_check.py`, `python3 tests/manual_restore_archive_check.py`, and `python3 tests/manual_backup_manifest_check.py`
- `CP-020`: compiled Python modules for restore message updates with `python3 -m py_compile resources/lib/main_window.py resources/lib/app.py`
- `CP-020`: re-ran restore apply failure, restore apply success, restore staging, restore warning, restore preflight, restore archive, and backup manifest regressions with `python3 tests/manual_restore_apply_failure_check.py`, `python3 tests/manual_restore_apply_check.py`, `python3 tests/manual_restore_stage_check.py`, `python3 tests/manual_restore_warning_check.py`, `python3 tests/manual_restore_preflight_check.py`, `python3 tests/manual_restore_archive_check.py`, and `python3 tests/manual_backup_manifest_check.py`
- `CP-021`: validated the main XML window asset after layout and color-hierarchy changes with `python3 tests/manual_ui_asset_check.py`
- `CP-022`: compiled the packaging script and package validation check with `python3 -m py_compile tools/build_addon_zip.py tests/manual_package_build_check.py`
- `CP-022`: built the installable addon zip with `python3 tools/build_addon_zip.py`
- `CP-022`: validated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `CP-022`: confirmed the corrected package layout after a real Kodi install failure against the root-file zip shape

### 2026-03-16

- `UI regression fix`: validated the main window XML structure and required backdrop/panel controls with `python3 tests/manual_ui_asset_check.py`
- `UI regression fix`: compiled the tightened UI asset check with `python3 -m py_compile tests/manual_ui_asset_check.py`
- `UI regression fix`: rebuilt the addon package with the opaque-background skin revision via `python3 tools/build_addon_zip.py`
- `UI regression fix`: revalidated package layout after adding skin media with `python3 tests/manual_package_build_check.py`
- `UI layout cleanup`: compiled the updated main window controller and UI asset check with `python3 -m py_compile resources/lib/main_window.py tests/manual_ui_asset_check.py`
- `UI layout cleanup`: validated the restructured XML layout and required backdrop/panel controls with `python3 tests/manual_ui_asset_check.py`
- `UI layout cleanup`: rebuilt the addon package after the layout simplification via `python3 tools/build_addon_zip.py`
- `UI layout cleanup`: revalidated package layout after the layout simplification with `python3 tests/manual_package_build_check.py`
- `UI flow fix`: compiled the updated main window controller, destination module, and targeted checks with `python3 -m py_compile resources/lib/main_window.py resources/lib/destination.py tests/manual_destination_persistence_check.py tests/manual_ui_asset_check.py`
- `UI flow fix`: validated saved-destination reset behavior for the new settings action with `python3 tests/manual_destination_persistence_check.py`
- `UI flow fix`: revalidated the main window XML asset with `python3 tests/manual_ui_asset_check.py`
- `UI flow fix`: rebuilt the addon package after wiring settings and backup confirmation via `python3 tools/build_addon_zip.py`
- `UI flow fix`: revalidated package layout after wiring settings and backup confirmation with `python3 tests/manual_package_build_check.py`
- `Backup interaction fix`: compiled the updated backup UI flow, cleanup model, and targeted checks with `python3 -m py_compile resources/lib/main_window.py resources/lib/cleanup.py tests/manual_cleanup_model_check.py tests/manual_cleanup_execution_check.py tests/manual_ui_asset_check.py`
- `Backup interaction fix`: validated cleanup defaults and formatting after switching cleanup to opt-in with `python3 tests/manual_cleanup_model_check.py`
- `Backup interaction fix`: revalidated cleanup execution semantics with `python3 tests/manual_cleanup_execution_check.py`
- `Backup interaction fix`: revalidated the main window XML asset with `python3 tests/manual_ui_asset_check.py`
- `Backup interaction fix`: rebuilt the addon package after simplifying the backup interaction via `python3 tools/build_addon_zip.py`
- `Backup interaction fix`: revalidated package layout after simplifying the backup interaction with `python3 tests/manual_package_build_check.py`
- `Backup interaction fix`: recompiled the main window controller after replacing the cleanup multiselect flow with a stepwise selector via `python3 -m py_compile resources/lib/main_window.py resources/lib/cleanup.py tests/manual_cleanup_model_check.py tests/manual_cleanup_execution_check.py tests/manual_ui_asset_check.py`
- `Backup interaction fix`: revalidated cleanup defaults and execution after replacing the cleanup multiselect flow with `python3 tests/manual_cleanup_model_check.py` and `python3 tests/manual_cleanup_execution_check.py`
- `Backup interaction fix`: rebuilt the addon package after replacing the cleanup multiselect flow via `python3 tools/build_addon_zip.py`
- `Backup interaction fix`: revalidated package layout after replacing the cleanup multiselect flow with `python3 tests/manual_package_build_check.py`
- `Backup interaction fix`: recompiled the main window controller after removing `yesno` from the backup flow via `python3 -m py_compile resources/lib/main_window.py resources/lib/cleanup.py tests/manual_cleanup_model_check.py tests/manual_cleanup_execution_check.py tests/manual_ui_asset_check.py`
- `Backup interaction fix`: rebuilt the addon package after reducing the backup flow to select dialogs only via `python3 tools/build_addon_zip.py`
- `Backup interaction fix`: revalidated package layout after reducing the backup flow to select dialogs only with `python3 tests/manual_package_build_check.py`
- `Backup interaction fix`: recompiled the main window controller after replacing the backup mode chooser with a review loop via `python3 -m py_compile resources/lib/main_window.py resources/lib/cleanup.py tests/manual_cleanup_model_check.py tests/manual_cleanup_execution_check.py tests/manual_ui_asset_check.py`
- `Backup interaction fix`: rebuilt the addon package after replacing the backup mode chooser with a review loop via `python3 tools/build_addon_zip.py`
- `Backup interaction fix`: revalidated package layout after replacing the backup mode chooser with a review loop via `python3 tests/manual_package_build_check.py`
- `Backup interaction fix`: recompiled the main window controller after removing the dead destination-view branch and moving cleanup apply to the bottom of the selector via `python3 -m py_compile resources/lib/main_window.py resources/lib/cleanup.py tests/manual_cleanup_model_check.py tests/manual_cleanup_execution_check.py tests/manual_ui_asset_check.py`
- `Backup interaction fix`: rebuilt the addon package after removing the dead destination-view branch and moving cleanup apply to the bottom of the selector via `python3 tools/build_addon_zip.py`
- `Backup interaction fix`: revalidated package layout after removing the dead destination-view branch and moving cleanup apply to the bottom of the selector via `python3 tests/manual_package_build_check.py`
- `Backup interaction fix`: recompiled the main window controller after reducing the backup-complete dialog to a minimal summary via `python3 -m py_compile resources/lib/main_window.py tests/manual_ui_asset_check.py`
- `Backup interaction fix`: rebuilt the addon package after reducing the backup-complete dialog to a minimal summary via `python3 tools/build_addon_zip.py`
- `Backup interaction fix`: revalidated package layout after reducing the backup-complete dialog to a minimal summary via `python3 tests/manual_package_build_check.py`
- `Live QA`: Windows testing confirmed the backup flow now runs through cleanup selection and backup execution, but the post-backup success summary still does not appear after completion
- `Live QA`: Windows testing indicates restore still does not complete successfully and needs a dedicated bug-fix pass before broader validation
- `Logging pass`: compiled targeted runtime modules with `python3 -m py_compile resources/lib/app.py resources/lib/log.py resources/lib/main_window.py resources/lib/restore_apply.py`
- `Logging pass`: revalidated restore apply success and preserved plain-Python importability with `python3 tests/manual_restore_apply_check.py`
- `Logging pass`: revalidated restore apply failure handling with `python3 tests/manual_restore_apply_failure_check.py`
- `Windows fix pass`: compiled the updated backup, dialog, logging, restore-apply, and restore-stage modules with `python3 -m py_compile resources/lib/app.py resources/lib/dialog.py resources/lib/log.py resources/lib/main_window.py resources/lib/restore_apply.py resources/lib/restore_stage.py tests/manual_dialog_text_check.py tests/manual_restore_stage_windows_path_check.py`
- `Windows fix pass`: validated dialog message composition with `python3 tests/manual_dialog_text_check.py`
- `Windows fix pass`: validated Windows restore-stage path normalization with `python3 tests/manual_restore_stage_windows_path_check.py`
- `Windows fix pass`: revalidated restore staging after Windows path handling changes with `python3 tests/manual_restore_stage_check.py`
- `Windows fix pass`: revalidated restore apply success with `python3 tests/manual_restore_apply_check.py`
- `Windows fix pass`: revalidated restore apply failure handling with `python3 tests/manual_restore_apply_failure_check.py`
- `Windows fix pass`: rebuilt the addon package after the backup/restore crash fixes via `python3 tools/build_addon_zip.py`
- `Windows fix pass`: revalidated package layout after the backup/restore crash fixes with `python3 tests/manual_package_build_check.py`
- `Windows apply fix`: compiled the restore-apply module and Windows apply-path check with `python3 -m py_compile resources/lib/restore_apply.py tests/manual_restore_apply_windows_path_check.py`
- `Windows apply fix`: validated Windows restore-apply path normalization with `python3 tests/manual_restore_apply_windows_path_check.py`
- `Windows apply fix`: revalidated restore apply success with `python3 tests/manual_restore_apply_check.py`
- `Windows apply fix`: revalidated restore apply failure handling with `python3 tests/manual_restore_apply_failure_check.py`
- `Windows apply fix`: revalidated restore staging after the apply-path changes with `python3 tests/manual_restore_stage_check.py`
- `Windows apply fix`: rebuilt the addon package after the restore-apply path fix via `python3 tools/build_addon_zip.py`
- `Windows apply fix`: revalidated package layout after the restore-apply path fix with `python3 tests/manual_package_build_check.py`
- `Startup unlock fix`: compiled the updated startup flow and staged-restore cleanup check with `python3 -m py_compile resources/lib/app.py resources/lib/restore_apply.py tests/manual_discard_pending_restore_check.py`
- `Startup unlock fix`: validated staged-restore cleanup with `python3 tests/manual_discard_pending_restore_check.py`
- `Startup unlock fix`: revalidated restore apply success with `python3 tests/manual_restore_apply_check.py`
- `Startup unlock fix`: revalidated restore apply failure handling with `python3 tests/manual_restore_apply_failure_check.py`
- `Startup unlock fix`: revalidated restore staging after the startup-flow changes with `python3 tests/manual_restore_stage_check.py`
- `Startup unlock fix`: rebuilt the addon package after the startup unlock change via `python3 tools/build_addon_zip.py`
- `Startup unlock fix`: revalidated package layout after the startup unlock change with `python3 tests/manual_package_build_check.py`
- `Live restore cutover`: compiled the live-restore modules and replacement checks with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/backup_engine.py resources/lib/backup_manifest.py resources/lib/backup_preflight.py resources/lib/backup_progress.py resources/lib/cleanup.py resources/lib/constants.py resources/lib/destination.py resources/lib/dialog.py resources/lib/log.py resources/lib/main_window.py resources/lib/paths.py resources/lib/restore_archive.py resources/lib/restore_live.py resources/lib/restore_preflight.py resources/lib/restore_warning.py tests/manual_path_resolution_check.py tests/manual_restore_archive_check.py tests/manual_restore_preflight_check.py tests/manual_restore_warning_check.py tests/manual_restore_live_check.py tests/manual_restore_live_skip_check.py tests/manual_restore_live_windows_path_check.py`
- `Live restore cutover`: revalidated runtime path resolution after removing restore staging with `python3 tests/manual_path_resolution_check.py`
- `Live restore cutover`: revalidated archive validation with `python3 tests/manual_restore_archive_check.py`
- `Live restore cutover`: revalidated live-restore preflight with `python3 tests/manual_restore_preflight_check.py`
- `Live restore cutover`: revalidated restore warning behavior with `python3 tests/manual_restore_warning_check.py`
- `Live restore cutover`: validated live restore overwrite behavior and self-exclusion with `python3 tests/manual_restore_live_check.py`
- `Live restore cutover`: validated skip-and-report behavior for locked files with `python3 tests/manual_restore_live_skip_check.py`
- `Live restore cutover`: validated Windows long-path handling for live restore with `python3 tests/manual_restore_live_windows_path_check.py`
- `Live restore cutover`: rebuilt the addon package after removing staged restore via `python3 tools/build_addon_zip.py`
- `Live restore cutover`: revalidated package layout after removing staged restore with `python3 tests/manual_package_build_check.py`
- `Backup self-exclusion fix`: compiled the updated backup modules and self-exclusion regression check with `python3 -m py_compile resources/lib/backup_preflight.py resources/lib/backup_engine.py tests/manual_backup_preflight_check.py tests/manual_backup_archive_check.py tests/manual_backup_self_exclusion_check.py`
- `Backup self-exclusion fix`: revalidated backup preflight with `python3 tests/manual_backup_preflight_check.py`
- `Backup self-exclusion fix`: revalidated backup archive collection with `python3 tests/manual_backup_archive_check.py`
- `Backup self-exclusion fix`: validated exclusion of `userdata/addon_data/script.kodi.mirror/` from backup scanning and archive collection with `python3 tests/manual_backup_self_exclusion_check.py`
- `Backup self-exclusion fix`: rebuilt the addon package after excluding this addon's addon-data from backup via `python3 tools/build_addon_zip.py`
- `Backup self-exclusion fix`: revalidated package layout after the backup self-exclusion change with `python3 tests/manual_package_build_check.py`
- `Restore UX simplification`: compiled the updated live-restore window flow with `python3 -m py_compile resources/lib/main_window.py`
- `Restore UX simplification`: revalidated live restore success and skip reporting with `python3 tests/manual_restore_live_check.py` and `python3 tests/manual_restore_live_skip_check.py`
- `Restore UX simplification`: rebuilt the addon package after removing the extra no-warning restore confirmation via `python3 tools/build_addon_zip.py`
- `Restore UX simplification`: revalidated package layout after the restore UX simplification with `python3 tests/manual_package_build_check.py`
- `Live QA`: Windows testing confirmed the no-warning restore path now reaches live restore after archive selection without an extra `Start live restore` step
- `Live QA`: Windows testing confirmed best-effort live restore can complete with a short skipped-file list instead of failing the whole operation, including a run that restored 11585 files and skipped 2 locked addon files

### 2026-03-17

- `UI simplification pass`: compiled the updated main window flow, control constants, addon entry path, and dialog helper imports with `python3 -m py_compile addon.py resources/lib/__init__.py resources/lib/app.py resources/lib/constants.py resources/lib/dialog.py resources/lib/main_window.py`
- `UI simplification pass`: revalidated the main window XML asset and guarded against the removed redundant destination button, stale staged-restore wording, and removed flow copy with `python3 tests/manual_ui_asset_check.py`
- `UI simplification pass`: searched the active UI/controller surface for stale staged-restore and removed main-action wording with `rg -n "stages|restart|Backup Destination|Flow|applies after restart|Choose Backup Destination" resources/lib resources/skins/default/1080i tests/manual_ui_asset_check.py`
- `UI simplification pass`: rebuilt the installable addon zip for live Kodi testing with `python3 tools/build_addon_zip.py`
- `UI simplification pass`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Addon metadata pass`: parsed `addon.xml` after adding icon metadata and updating the product text with `python3 -c "import xml.etree.ElementTree as ET; ET.parse('addon.xml')"`
- `Addon metadata pass`: rebuilt the installable addon zip after adding `resources/icon.png` with `python3 tools/build_addon_zip.py`
- `Addon metadata pass`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Addon metadata pass`: confirmed the packaged addon zip includes `script.kodi.mirror/resources/icon.png` with `python3 -c "import zipfile; z=zipfile.ZipFile('dist/script.kodi.mirror-0.1.0.zip'); names=set(z.namelist()); assert 'script.kodi.mirror/resources/icon.png' in names; print('icon packaged ok')"`
- `UI containment pass`: compiled the updated main window controller after tightening the cleanup summary text with `python3 -m py_compile resources/lib/main_window.py`
- `UI containment pass`: revalidated the main window XML asset after rebalancing card heights, shortening copy, and standardizing the action rail with `python3 tests/manual_ui_asset_check.py`
- `Cleanup window pass`: compiled the new cleanup window module, the updated main window wiring, and the UI asset check with `python3 -m py_compile resources/lib/constants.py resources/lib/main_window.py resources/lib/cleanup_window.py tests/manual_ui_asset_check.py`
- `Cleanup window pass`: revalidated the main window and cleanup window XML assets with `python3 tests/manual_ui_asset_check.py`
- `Cleanup window pass`: searched the active cleanup UI surface to confirm `Select all` and `Apply` remain while `Clear all` and `Apply cleanup selection` are gone with `rg -n "Clear all|Apply cleanup selection|Cleanup before backup|Select all|Apply" resources/lib resources/skins/default/1080i tests/manual_ui_asset_check.py`
- `Cleanup window pass`: rebuilt the installable addon zip after replacing the stock cleanup dialog with the custom cleanup window via `python3 tools/build_addon_zip.py`
- `Cleanup window pass`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Display-name and layout pass`: parsed `addon.xml` after renaming the addon to `Kodi Mirror` with `python3 -c "import xml.etree.ElementTree as ET; ET.parse('addon.xml')"`
- `Display-name and layout pass`: compiled the updated main window, cleanup window, constants, and UI asset check with `python3 -m py_compile resources/lib/main_window.py resources/lib/cleanup_window.py resources/lib/constants.py tests/manual_ui_asset_check.py`
- `Display-name and layout pass`: revalidated the main window and cleanup window XML assets after increasing text regions and moving the action rail down with `python3 tests/manual_ui_asset_check.py`
- `Display-name and layout pass`: rebuilt the installable addon zip after the rename/layout changes with `python3 tools/build_addon_zip.py`
- `Display-name and layout pass`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Remote navigation pass`: revalidated the main window and cleanup window XML assets after adding explicit D-pad focus chains with `python3 tests/manual_ui_asset_check.py`
- `Remote navigation pass`: rebuilt the installable addon zip after adding explicit focus movement for the main action rail and cleanup window via `python3 tools/build_addon_zip.py`
- `Remote navigation pass`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Remote navigation pass`: confirmed explicit `onup` / `ondown` navigation on the main action rail and explicit vertical/horizontal navigation on the cleanup window footer with `rg -n "onup|ondown|onleft|onright" resources/skins/default/1080i/script-kodi-mirror-main.xml resources/skins/default/1080i/script-kodi-mirror-cleanup.xml`
- `Restore cancel fix`: compiled the updated main window restore-browse flow with `python3 -m py_compile resources/lib/main_window.py`
- `Restore cancel fix`: rebuilt the installable addon zip after treating a returned directory path from the restore file picker as cancel instead of failure with `python3 tools/build_addon_zip.py`
- `Restore cancel fix`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Restore cancel fix`: confirmed the restore browse handler now logs both empty-path cancel and directory-path cancel paths with `rg -n "Restore archive browse returned directory path|Restore archive browse canceled" resources/lib/main_window.py`
- `Backup location overflow fix`: revalidated the main window XML asset after expanding the backup-location card and status text region with `python3 tests/manual_ui_asset_check.py`
- `Backup location overflow fix`: rebuilt the installable addon zip after moving the restore card down to keep backup-location status text contained with `python3 tools/build_addon_zip.py`
- `Backup location overflow fix`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Right-side card spacing fix`: revalidated the main window XML asset after increasing the restore-card height and moving the cleanup card down to stop section overlap with `python3 tests/manual_ui_asset_check.py`
- `Right-side card spacing fix`: rebuilt the installable addon zip after re-spacing the lower right-side cards with `python3 tools/build_addon_zip.py`
- `Right-side card spacing fix`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Backup folder label pass`: revalidated the main window XML asset after renaming the backup-location labels for path/status clarity with `python3 tests/manual_ui_asset_check.py`
- `Backup folder label pass`: rebuilt the installable addon zip after clarifying the backup-folder labels with `python3 tools/build_addon_zip.py`
- `Backup folder label pass`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Status label tweak`: revalidated the main window XML asset after changing `Folder Status` back to `Status` with `python3 tests/manual_ui_asset_check.py`
- `Status label tweak`: rebuilt the installable addon zip after the wording revert with `python3 tools/build_addon_zip.py`
- `Status label tweak`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Live QA`: Windows backup completed successfully from the updated UI flow with four cleanup targets selected, writing `C:\Users\Bryce\Desktop\KodiBackup-20260317-063003.zip` and logging `file_count=11574`
- `Live QA`: Windows live restore completed successfully from `C:\Users\Bryce\Desktop\KodiBackup-20260317-063003.zip` with `Restore warnings generated: none`, `restored_file_count=11530`, and `skipped_file_count=2`
- `Live QA`: Windows live restore skip reporting captured the expected locked-file behavior for `addons/peripheral.joystick/peripheral.joystick.dll` and `addons/service.subtitles.opensubtitles-com/resources/lib/os/model/response/.placeholder`

### 2026-03-18

- `CP-023`: verified the new README install and usage guidance plus the Android permissions note with `python3 -c "from pathlib import Path; text = Path('README.md').read_text(); assert 'Install from zip file' in text; assert 'Allow management of all files' in text; assert '/storage/emulated/0/Backup' in text; print('readme content ok')"`
- `CP-023`: confirmed the packaged addon artifact referenced by the README still exists and retains the Kodi-required top-level addon folder with `python3 -c "import os, zipfile; archive = 'dist/script.kodi.mirror-0.1.0.zip'; assert os.path.exists(archive); names = set(zipfile.ZipFile(archive).namelist()); assert 'script.kodi.mirror/addon.xml' in names; print('package reference ok')"`
- `CP-023`: checked the documentation patch for whitespace and formatting errors with `git diff --check README.md docs/progress.md`
- `Metadata wording pass`: parsed `addon.xml` after replacing the ambiguous `remote-friendly` summary wording with `python3 -c "import xml.etree.ElementTree as ET; ET.parse('addon.xml')"`
- `Metadata wording pass`: confirmed the old `remote-friendly` phrasing is gone and the new D-pad wording is present in addon metadata and README with `rg -n "remote-friendly|optimized for D-pad controls" addon.xml README.md`
- `Metadata wording pass`: checked the metadata/documentation patch for whitespace and formatting errors with `git diff --check addon.xml README.md docs/progress.md`
- `Restore confirmation pass`: compiled the updated restore UI/controller surface with `python3 -m py_compile resources/lib/constants.py resources/lib/main_window.py tests/manual_ui_asset_check.py tests/manual_restore_warning_check.py tests/manual_restore_live_check.py tests/manual_restore_live_skip_check.py`
- `Restore confirmation pass`: revalidated the main window XML asset after replacing the restore warning copy with an archive-path field via `python3 tests/manual_ui_asset_check.py`
- `Restore confirmation pass`: revalidated restore warning behavior after inserting the final restore confirmation step with `python3 tests/manual_restore_warning_check.py`
- `Restore confirmation pass`: revalidated live restore success and skip reporting after adding the confirmation dialog with `python3 tests/manual_restore_live_check.py` and `python3 tests/manual_restore_live_skip_check.py`
- `Restore confirmation pass`: confirmed the old restore-card warning copy is gone and the new archive-path / confirmation text is present with `rg -n "Warnings are shown for platform or Kodi version differences|Archive Path|The restore process can take a few minutes|Please be patient|Restore canceled at final confirmation" resources/lib resources/skins/default/1080i tests`
- `Restore card revert pass`: compiled the updated restore UI/controller surface after removing the archive-path field with `python3 -m py_compile resources/lib/constants.py resources/lib/main_window.py tests/manual_ui_asset_check.py tests/manual_restore_warning_check.py tests/manual_restore_live_check.py tests/manual_restore_live_skip_check.py`
- `Restore card revert pass`: revalidated the main window XML asset after restoring the platform/Kodi warning copy in the restore card with `python3 tests/manual_ui_asset_check.py`
- `Restore card revert pass`: revalidated restore warning behavior and the final restore confirmation step with `python3 tests/manual_restore_warning_check.py`
- `Restore card revert pass`: revalidated live restore success and skip reporting after removing the archive-path field with `python3 tests/manual_restore_live_check.py` and `python3 tests/manual_restore_live_skip_check.py`
- `Restore card revert pass`: confirmed the restore card warning copy is back, the archive-path label is gone, and the final confirmation text remains present with `rg -n "Warnings are shown for platform or Kodi version differences|Archive Path|The restore process can take a few minutes|Please be patient|Restore canceled at final confirmation" resources/lib resources/skins/default/1080i tests`
- `Restore confirm modal pass`: compiled the updated restore confirmation modal, controller wiring, and targeted checks with `python3 -m py_compile resources/lib/constants.py resources/lib/main_window.py resources/lib/restore_confirm_window.py tests/manual_ui_asset_check.py tests/manual_restore_warning_check.py tests/manual_restore_live_check.py tests/manual_restore_live_skip_check.py`
- `Restore confirm modal pass`: revalidated the main window and restore confirmation XML assets after replacing the stock selectable confirmation text with a custom modal via `python3 tests/manual_ui_asset_check.py`
- `Restore confirm modal pass`: revalidated restore warning behavior after replacing the final stock confirmation list with the custom modal via `python3 tests/manual_restore_warning_check.py`
- `Restore confirm modal pass`: revalidated live restore success and skip reporting after wiring the custom confirmation modal with `python3 tests/manual_restore_live_check.py` and `python3 tests/manual_restore_live_skip_check.py`
- `Restore confirm modal pass`: confirmed the controller now opens the custom confirmation window and the final confirmation copy exists only in the XML modal with `rg -n "Dialog\\(\\)\\.select\\(\\s*\\\"Start restore\\\"|open_restore_confirm_window|The restore process can take a few minutes|Please be patient|script-kodi-mirror-restore-confirm.xml" resources/lib resources/skins/default/1080i tests`
- `Restore confirm modal pass`: rebuilt the installable addon zip after adding the custom restore confirmation modal with `python3 tools/build_addon_zip.py`
- `Restore confirm modal pass`: revalidated package naming, top-level addon-folder layout, and addon-only contents with `python3 tests/manual_package_build_check.py`
- `Restore confirm modal pass`: confirmed the packaged addon zip includes the new restore confirmation module and XML asset with `python3 -c "import zipfile; names=set(zipfile.ZipFile('dist/script.kodi.mirror-0.1.0.zip').namelist()); assert 'script.kodi.mirror/resources/lib/restore_confirm_window.py' in names; assert 'script.kodi.mirror/resources/skins/default/1080i/script-kodi-mirror-restore-confirm.xml' in names; print('restore confirm packaged ok')"`
- `Restore confirm modal pass`: revalidated the XML asset after adding explicit D-pad focus paths and confirmed `onup` / `ondown` / `onleft` / `onright` navigation in the modal footer with `python3 tests/manual_ui_asset_check.py` and `rg -n "onup|ondown|onleft|onright" resources/skins/default/1080i/script-kodi-mirror-restore-confirm.xml`

## Change Log

### 2026-03-15

- Created initial `progress.md`
- Recorded agreed product scope and architecture direction
- Added full implementation plan and ordered `CP-00X` execution list
- Updated restore architecture to staged apply with self-exclusion for this addon
- Updated destination behavior to remember the last valid selected location
- Locked addon id, minimum Kodi target, desktop destination defaults, and staging path
- Added explicit backup and restore preflight checks to the implementation plan
- Completed `CP-001` with initial addon identity, version target, and package-root metadata
- Completed `CP-002` with a runnable addon bootstrap and base `resources/lib` module layout
- Completed `CP-003` with Kodi special-path runtime resolution for source roots and restore staging
- Completed `CP-004` with the primary XML-backed main window and supporting placeholder dialogs
- Completed `CP-005` with platform default backup destination resolution, directory creation, writability probes, and main-window status display
- Completed `CP-006` with browse-based destination selection, persistence of validated user choices, and active destination state display
- Completed `CP-007` with backup preflight checks for source readability, destination readiness, recursive size estimation, and free-space validation
- Completed `CP-008` with the approved cleanup target model, default selections, resolved cleanup paths, and cleanup summary display in the main window
- Completed `CP-009` with cleanup execution, skip reporting for missing targets, fail-fast cleanup errors, and cleanup result summaries in the backup flow
- Completed `CP-010` with the `backup_manifest.json` archive contract, manifest schema builder, and manifest placeholder integration in the backup flow
- Completed `CP-011` with recursive backup file walk, ZIP archive creation at compression level 6, manifest writing at archive root, and real backup output from the main workflow
- Completed `CP-012` with stage-based backup progress reporting and clearer success/failure summaries around the existing backup workflow
- Completed `CP-013` with ZIP archive selection from the main UI, restore archive validation against the current backup contract, and explicit unsupported-archive messaging
- Completed `CP-014` with restore preflight checks for manifest JSON validity, required restore roots, staging-directory readiness, and free-space validation before restore staging
- Completed `CP-015` with restore manifest parsing for platform and Kodi-version fields plus non-blocking mismatch warnings in the restore readiness flow
- Completed `CP-016` with staged restore extraction into the locked pending-restore path, pending restore plan creation, and hard failure for unsafe or unsupported archive entries
- Completed `CP-017` with startup detection of `pending_restore_plan.json`, generic replace-style apply for staged `userdata/` and `addons/`, and staging cleanup after successful restore apply
- Completed `CP-018` with explicit restore-apply exclusion of this addon's live addon folder and addon_data folder while preserving replace semantics for all other paths
- Completed `CP-019` with fail-fast restore-apply error classification by stage/path, preserved pending staging on apply failure, and clearer startup failure reporting
- Completed `CP-020` with shorter operational user messaging for restore preparation, restart-required apply, restore completion, and restore-apply failure states
- Completed `CP-021` with a stronger black / blue / white XML layout, a clearer action rail, and more scannable status panels for remote-first use
- Completed `CP-022` with a reusable addon-zip packaging script and a built `dist/script.kodi.mirror-0.1.0.zip` artifact using the Kodi-required top-level addon-folder layout for manual zip installation

### 2026-03-16

- Fixed the main window presentation after PC testing showed the prior XML rendered as a transparent overlay with the Kodi interface visible behind it
- Reworked the main screen into a centered modal-style layout with a dimmed backdrop, opaque primary panel, and solid information cards for readable remote-first use
- Tightened UI asset validation so the main skin must include both a fullscreen backdrop and a centered modal panel, preventing a repeat of the transparent-window regression
- Corrected the first UI fix after live testing showed the modal shell was still too translucent for real Kodi use
- Removed transparency from the main window shell and switched the skin to an addon-owned solid texture so background fill behavior no longer depends on the active Kodi skin's `white.png`
- Simplified the main screen again after live testing showed text overlap and clipping on real Windows data
- Rebuilt the main window into clearer stacked cards with dedicated wrapped fields for long paths and status text, plus shorter copy across the left action rail and restore guidance
- Replaced the placeholder Settings action with a real v1 settings menu for changing the backup destination or returning to the platform default destination
- Changed the Backup action so it no longer runs immediately and now requires an explicit confirmation after showing the destination and cleanup selections
- Corrected the backup interaction after live testing showed the prior confirmation path did not surface reliably on click
- Switched cleanup from default-on to opt-in, and changed Backup to a simpler `select cleanup options -> confirm -> run` flow
- Corrected the cleanup chooser after live testing showed Kodi's multiselect dialog did not present a reliable commit path for remote-style use
- Removed `yesno` from the backup interaction after repeated live failures showed that the current Kodi runtime was not presenting that confirmation path reliably
- Reworked the backup flow again after live testing showed the mode chooser still front-loaded cleanup editing in an awkward way for TV use
- Simplified the backup review loop again after live testing showed the destination-view branch was unnecessary and the cleanup editor needed its commit action at the end of the list
- Simplified the backup-complete dialog after live testing showed the prior multi-line summary was not surfacing reliably after archive creation
- Recorded two remaining live QA issues for the next handoff: missing backup-complete summary dialog and restore flow not working end-to-end
- Added targeted backup and restore stage logging so the next live QA pass can pinpoint whether failures occur before dialog handoff, during restore staging, or during restore apply
- Restored plain-Python importability for non-UI validation after the logging pass by making the logging module run outside Kodi when `xbmc` is unavailable
- Fixed the backup crash introduced by the logging pass after Windows QA showed the new backup preflight log was reading keys that do not exist in the preflight result
- Reworked all addon `Dialog().ok(...)` calls to send a single composed message string after Windows Kodi showed that this runtime rejects the older multi-argument call pattern
- Added Windows long-path handling for restore staging so deeply nested archive entries can extract under the locked pending-restore path without failing at normal path-length limits
- Updated restore messaging to state that KodiMirror must be run again after restart for the staged restore to apply, matching the current trigger path
- Added the same Windows long-path handling to restore apply so staged files that extracted successfully can also be copied into the live target roots during the relaunch step
- Changed startup pending-restore handling so a staged restore no longer hard-blocks KodiMirror after a failed apply: users can now apply, open the app without applying, or discard the staged restore
- Reopened the restore architecture after live Windows testing proved that staged apply on next launch still hits the same in-process file-lock constraints as live restore
- Removed the staged restore system entirely and cut over to best-effort live restore with overwrite-only semantics and skip/report handling for locked or unwritable files
- Removed pending-restore startup behavior, pending-plan handling, and staging-path runtime resolution so the addon no longer carries dead staged-restore code
- Excluded this addon's own `userdata/addon_data/script.kodi.mirror/` tree from backup scanning and archive creation so stale internal restore leftovers cannot break future backups
- Removed the extra no-warning restore confirmation step so selecting a valid archive now starts live restore immediately after validation
- Changed the restore completion dialog to state partial success explicitly when files are skipped during live restore

### 2026-03-17

- Simplified the main window into a cleaner remote-first layout with four primary actions, clearer card structure, corrected text containment, and short operational copy
- Replaced the stock cleanup select dialog with a custom cleanup window that keeps the four cleanup items visible, preserves `Select all`, removes `Clear all`, and returns to the backup review flow on `Apply`
- Added explicit D-pad navigation to the main action rail and cleanup window so the flow works on Android TV / Fire TV class devices without mouse input
- Renamed the display name to `Kodi Mirror`, added a packaged icon, and corrected stale addon metadata text that still described staged restore
- Fixed restore browse cancel handling so backing out of archive selection no longer shows a false `Backup archive does not exist` error
- Live Windows QA now confirms the updated UI can run a full backup and same-machine live restore successfully, with expected locked-file skips reported instead of failing the restore
- Updated `AGENTS.md` to codify explicit Kodi remote-navigation rules, runtime text-containment expectations, and defensive browse-cancel handling based on issues uncovered during the Windows UI pass

### 2026-03-18

- Completed `CP-023` with a new evergreen `README.md` covering current product behavior, install flow, backup and restore usage, current operational notes, and the Android file-permissions note for missing backup visibility
- Updated addon metadata and README wording to describe the product as optimized for D-pad controls instead of using `remote-friendly`, avoiding confusion with remote filesystem paths
- Updated the restore card to show the selected backup-zip path and added a final restore confirmation dialog that tells the user the restore process can take a few minutes
- Reverted the restore-card archive-path display, restored the platform/Kodi warning copy in that panel, and kept the final restore confirmation dialog
- Replaced the final stock restore confirmation list with a custom modal so the confirmation text is static copy, only `Start restore` and `Cancel` are selectable, and the footer has explicit D-pad focus paths

## Session Handoff

Latest state:

- `CP-001` through `CP-024` are complete.
- Windows now has strong live QA evidence for the normal path: backup succeeds, same-machine live restore succeeds, and locked files are reported as skips instead of failing the operation.
- Backup and restore flows are implemented end to end, including manifest validation, restore preflight, live overwrite-only apply, self-exclusion, and skip reporting for locked or unwritable files.
- The main window is now a remote-first modal with a simplified action rail and three status cards for backup folder, restore, and cleanup.
- The restore card now keeps the platform/Kodi warning copy in the panel, while the final restore confirmation dialog remains in place before live apply starts.
- Cleanup now uses a custom Kodi-styled window instead of the stock select dialog, with explicit D-pad navigation and an `Apply` return path to the backup review step.
- Restore archive cancel now exits cleanly without a false error dialog, including the Windows case where Kodi returns the current folder path on cancel.
- Restore now includes a custom confirmation modal before live apply that shows static guidance text and keeps only `Start restore` and `Cancel` as selectable actions.
- User-facing metadata and branding now use `Kodi Mirror`, and the addon zip includes the packaged icon at `resources/icon.png`.
- Addon metadata and README now describe the product as optimized for D-pad controls rather than `remote-friendly`, so the wording is clearer for backup-path discussions.
- Packaging continues to produce `dist/script.kodi.mirror-0.1.0.zip` with the correct top-level addon-folder layout.
- The repo now has an evergreen `README.md` with install and usage instructions, current operational notes, and the Android `Allow management of all files` permissions note for missing backup visibility.
- `AGENTS.md` now codifies the Kodi-specific UI/runtime lessons from this session so future edits preserve explicit remote navigation, contained text layouts, and defensive browse-cancel handling.
- Open work is now concentrated on `CP-025`, `CP-026`, and `CP-027`.

What the next session should do:

1. Run `CP-025` Android / Fire TV destination and permission validation on target hardware, including the Android storage-permissions path documented in the new README.
2. Keep `CP-026` open for broader cross-platform warning validation, especially the mismatch-warning path that same-machine Windows restore does not exercise.
3. Prepare `CP-027` once Android / Fire TV validation and the remaining warning-path evidence are in place.

Constraints to keep in view:

- Keep the implementation simple and explicit.
- Do not add fallback behavior unless it is currently required.
- Prefer Kodi special paths over OS-specific Kodi source detection.
- Preserve remote-friendly UX as a first-class requirement.
- Make live restore status and skipped-file reporting obvious to the user at every step.
