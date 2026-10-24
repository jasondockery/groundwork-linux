# Move an existing Linux Groundwork installation

Use the [shared migration guide](https://github.com/jasondockery/groundwork-core/blob/main/docs/migrating-from-groundwork.md) for backups, local edits, preview, applying the new source, acceptance, and rollback. Keep the original `groundwork` checkout and its remote unchanged.

On the same Linux installation that used Groundwork, clone this repo to a new directory and run `bash bootstrap.sh --prepare-only`. This prepares the visible shared engine, defaulting to `~/code/groundwork-mac`, without applying configuration. The implementation currently remains there; this repo is the Linux entry point and OS guide.

Use that engine path in the shared guide's `chezmoi --source ... diff` and `apply` steps. Preserve the old stored answers instead of forcing a fresh interview. An old terminal multiplexer selection remains in effect; choose Both through `groundwork-configure` after migration if you want Herdr primary and tmux available for lessons. Verify the Omarchy-aligned keys rather than restoring the old Groundwork map by default.

This migration is for non-Omarchy Linux. No existing Groundwork-on-Omarchy migration is supported or needed for this task. Native Omarchy uses its dedicated environment repo.

## Desktop apps

Linux desktops install FreeTube from this entry point as the Flathub user Flatpak `io.freetubeapp.FreeTube`. After the engine apply, run `bash bootstrap.sh` on a clean engine checkout to register the local apply hook that `update-all` runs. Headless and WSL targets skip FreeTube. See [desktop apps](desktop-apps.md).
