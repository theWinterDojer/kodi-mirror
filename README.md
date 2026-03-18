# Kodi Mirror

Kodi Mirror is a Kodi-native backup and restore addon optimized for D-pad controls. It creates a ZIP backup of the active Kodi `userdata/` and `addons/` roots, and it can apply that backup back into the active Kodi environment with clear warning and skip reporting.

## What It Does

- Backup of the active `userdata/` and `addons/` roots
- Optional cleanup of the approved cache and package paths before backup
- ZIP archive output with `backup_manifest.json`
- Platform-aware default backup folder with browse override and saved last valid destination
- Best-effort live restore with overwrite-only behavior while Kodi Mirror is running
- Warning-only restore for platform-family or Kodi-major mismatch

## Install

Install from the packaged addon zip:

1. Download the current `script.kodi.mirror-<version>.zip` artifact from this repo, or build it locally with `python3 tools/build_addon_zip.py`.
2. If you build locally, the zip is written to `dist/`.
3. In Kodi, open `Add-ons`, choose `Install from zip file`, and select the Kodi Mirror zip.

## Backup

1. Open Kodi Mirror.
2. Review the backup folder shown on the main screen.
3. Use `Settings` if you want to switch to another destination. Kodi Mirror remembers the last valid folder you choose.
4. Start `Backup`, review the cleanup selection, and confirm.
5. Kodi Mirror writes a ZIP backup to the selected folder and shows the result when the backup finishes.

Default backup folder:

- Android / Fire TV: `/storage/emulated/0/Backup`
- Windows: `%USERPROFILE%\Backup`
- Linux: `$HOME/Backup`
- macOS: `$HOME/Backup`

Android note:

If you do not see your backup `.zip` file or backup folder on an Android device, enable Kodi file access in Android Settings > Apps > Kodi > Permissions > Files and Media and set it to `Allow management of all files`.

## Restore

1. Open Kodi Mirror.
2. Choose `Restore` and select a backup zip.
3. If Kodi Mirror detects a platform-family or Kodi-major mismatch, it shows a warning and lets you continue.
4. Restore runs live against the active `userdata/` and `addons/` roots.
5. Kodi Mirror reports restored and skipped files when the restore completes.

## Notes

- Restore is best-effort while Kodi is running. Locked or unwritable files are skipped and reported instead of stopping the whole restore.
- Restore does not delete files that are absent from the backup zip.
- Cross-platform restore is allowed, but some platform-specific addons may not work after restore.
- Kodi Mirror excludes its own addon folder and addon-data folder from live restore so it does not overwrite itself during the running operation.
