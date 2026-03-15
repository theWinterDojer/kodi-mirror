# KodiMirror Progress

## Project Summary

This project is a Kodi-native Python addon that provides a simple, remote-friendly backup and restore workflow for Kodi users.

The addon is intended to replace confusing backup solutions with a direct "clone-style" tool that backs up the active Kodi installation state by packaging the active `userdata/` and `addons/` directories, with optional cleanup of selected cache folders before compression. Restore uses staged, replace-style apply semantics so the restored Kodi state matches the backup as closely as possible while excluding this backup addon from self-overwrite.

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
- addon type: Kodi script addon
- minimum target: Kodi 20+
- restore staging path: `special://profile/addon_data/script.kodi.mirror/pending_restore/`

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
4. Warn if platform family or Kodi major version differs.
5. Confirm staged replace restore.
6. Stage restore data and tell the user a restart is required.
7. After restart, apply restore and show summary.

Settings flow:

- View or change default backup location
- No cleanup-preference persistence in v1; default cleanup selections are applied each time

### UI Implementation Approach

Use a small custom Kodi UI rather than chaining many stock dialogs.

Current preferred approach:

- One primary XML-backed window for the main workflow
- Dialogs only for confirmations, file browsing, and final results
- Progress dialog during backup and restore

## Backup Model

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
- Kodi restart is required to apply the staged restore

### Restore Safety Requirements

- Validate that the selected file is a supported backup archive
- Validate the presence and format of `backup_manifest.json`
- Protect against path traversal in archive entries
- Refuse to extract entries outside the intended Kodi destination
- Surface file copy failures clearly
- Do not perform live in-place restore of active Kodi roots
- Stage restore payload before apply
- Exclude this backup addon from restore apply so the running restore mechanism does not overwrite itself

### Restore Behavior

Restore target roots:

- active `special://home/userdata/`
- active `special://home/addons/`

Behavior:

- restore is staged first, not applied live
- apply restore with replace semantics for `userdata/` and `addons/`
- remove target files that are not present in the backup, except explicit self-exclusions for this addon
- fail fast if restore apply encounters a write/delete error that prevents a correct result
- report failures explicitly
- prompt the user to restart Kodi after staging so the restore can be applied

Restore self-exclusions:

- this addon's folder under `addons/<addon_id>/`
- this addon's data folder under `userdata/addon_data/<addon_id>/`

Restore flow detail:

1. User selects a backup zip.
2. Addon validates the archive and reads `backup_manifest.json`.
3. Addon stages restore content into a writable staging area.
4. Addon writes a pending restore plan describing staged source and intended targets.
5. Addon clearly tells the user that restore is prepared but not yet applied.
6. User restarts Kodi.
7. On next startup of this addon, pending restore is detected before normal UI flow.
8. Addon applies the staged replace restore, skipping this addon's own files.
9. Addon clears staged restore state and shows success or failure.

Known limitation:

The restored installation is intentionally not a perfect byte-for-byte clone because this backup addon excludes its own files from restore apply so the restore mechanism remains stable.

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
- A staged restore still depends on being able to complete the apply step successfully after restart.
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

- recursive file collection for `userdata/` and `addons/`
- zip creation with compression level 6
- `backup_manifest.json`
- file counting and size tracking
- progress updates

Definition of done:

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
- staging of restore payload and pending restore plan
- path-safe replace apply after restart
- self-exclusion for this addon during apply
- failure reporting and clear restart/apply messaging

Definition of done:

- a valid backup can be staged and then applied into a test environment
- unsafe archive entries are rejected
- restore apply halts on critical write/delete failure and reports it clearly

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

- [ ] `CP-001` Define addon identity, packaging format, and Kodi version target.
- [ ] `CP-002` Create addon skeleton with `addon.xml`, entrypoint, and base module layout.
- [ ] `CP-003` Implement runtime path resolution using Kodi special paths for source roots.
- [ ] `CP-004` Decide and implement main UI structure: primary XML window plus supporting dialogs.
- [ ] `CP-005` Define destination path policy by platform and implement writability checks.
- [ ] `CP-006` Implement browse/select destination flow and persistence of the last valid destination.
- [ ] `CP-007` Implement cleanup option model and defaults for the four approved paths.
- [ ] `CP-008` Implement cleanup execution and cleanup-result reporting.
- [ ] `CP-009` Define backup archive layout and `backup_manifest.json` schema.
- [ ] `CP-010` Implement backup file walk, filtering, and zip creation with compression level 6.
- [ ] `CP-011` Implement backup progress reporting and success/failure summaries.
- [ ] `CP-012` Implement restore archive selection and archive validation.
- [ ] `CP-013` Implement manifest parsing and restore warning logic for platform/Kodi mismatch.
- [ ] `CP-014` Implement staged restore payload extraction and pending restore plan creation.
- [ ] `CP-015` Implement startup detection of pending restore and replace-style restore apply.
- [ ] `CP-016` Exclude this addon's own addon folder and addon_data folder from restore apply.
- [ ] `CP-017` Implement fail-fast restore error handling and explicit restore-apply reporting.
- [ ] `CP-018` Implement clear user messaging for staged restore preparation, required restart, and restore completion.
- [ ] `CP-019` Apply black / blue / white Kodi UI styling and remote-friendly layout polish.
- [ ] `CP-020` Package addon into an installable zip for GitHub distribution.
- [ ] `CP-021` Write evergreen README with install and use instructions only.
- [ ] `CP-022` Run targeted validation for backup flow on one desktop platform.
- [ ] `CP-023` Run targeted validation for destination and permission behavior on Android / Fire TV class hardware.
- [ ] `CP-024` Run targeted validation for staged restore behavior and cross-platform warning messaging.
- [ ] `CP-025` Prepare first release candidate and record known limitations.

## Current Status

Current phase:

- Planning

Current decisions already made:

- Build from scratch as a Kodi-native addon
- Use addon id `script.kodi.mirror`
- Target Kodi 20+
- Back up active `userdata/` and `addons/`
- Allow full restore across platforms with warning
- Use `/storage/emulated/0/Backup` as the Android / Fire TV default destination
- Use `%USERPROFILE%\\Backup` as the Windows default destination
- Use `$HOME/Backup` as the Linux and macOS default destination
- Use explicit browse override plus persistence of the last valid destination
- Use ZIP compression level 6
- Use staged restore with restart-required apply
- Use `special://profile/addon_data/script.kodi.mirror/pending_restore/` as the staged restore working path
- Exclude this addon from restore apply to avoid self-overwrite during staged restore

Open items to resolve before implementation starts:

- None. The implementation plan is locked for v1.

## Change History

### 2026-03-15

- Created initial `progress.md`
- Recorded agreed product scope and architecture direction
- Added full implementation plan and ordered `CP-00X` execution list
- Updated restore architecture to staged apply with self-exclusion for this addon
- Updated destination behavior to remember the last valid selected location
- Locked addon id, minimum Kodi target, desktop destination defaults, and staging path

## Session Handoff

Latest state:

- Planning only
- No implementation files have been created yet
- No code has been validated yet

What the next session should do:

1. Start `CP-001` and `CP-002`.
2. Encode the locked defaults directly in the addon skeleton.
3. Avoid reopening product-scope questions unless implementation exposes a real blocker.

Constraints to keep in view:

- Keep the implementation simple and explicit.
- Do not add fallback behavior unless it is currently required.
- Prefer Kodi special paths over OS-specific Kodi source detection.
- Preserve remote-friendly UX as a first-class requirement.
- Make staged restore status obvious to the user at every step.
