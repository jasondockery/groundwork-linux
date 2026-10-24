# Desktop apps on Linux

Linux desktops install FreeTube by default. FreeTube is a private YouTube client with no Google sign-in; subscriptions, history, and playlists stay in its own data directory. The package is the Flathub user Flatpak `io.freetubeapp.FreeTube`.

Desktop Macs install FreeTube from the official pinned disk image in the shared engine. Homebrew disabled the `freetube` cask, so the engine does not declare that cask. The disk image is desktop Macs only. Linux and WSL never receive it. This entry point installs the Flatpak. Omarchy keeps its own package path and is refused here.

## When it installs

`bash bootstrap.sh` copies `install-desktop-apps.sh` to `~/.local/lib/groundwork-linux/install-desktop-apps.sh` and writes `home/run_after_33-groundwork-linux-desktop-apps.sh` into the local engine checkout. That path is listed in the checkout's `.git/info/exclude`, so `git status` in the engine stays clean. `chezmoi apply` runs the hook. `update-all` and `groundwork-update` both apply the engine, so both run the hook.

`update-all` sets `GROUNDWORK_UPDATE_SCOPE=maintenance`. The hook installs FreeTube when it is missing and updates that Flatpak when it is present. `groundwork-update` sets `GROUNDWORK_UPDATE_SCOPE=configuration`. The hook installs FreeTube when it is missing and leaves an existing install unchanged.

Running `bash install-desktop-apps.sh` directly uses the same rules. A second run is safe. `--help` and unknown arguments exit before any install.

Install the `flatpak` package from your distribution before the first desktop apply. On Ubuntu/Debian: `sudo apt install flatpak`. The script adds the Flathub remote for the current user when it installs or updates FreeTube. If adding that remote, installing, or updating fails, the apply prints a warning and continues. The next `update-all` retries FreeTube. A missing `flatpak` command still stops that desktop apply.

## What it skips

Headless machines and WSL skip FreeTube. A stored `headless = true` in `~/.config/chezmoi/chezmoi.toml` skips it. With no stored answer, a session without `DISPLAY` and `WAYLAND_DISPLAY` is treated as headless. A stored `headless = false` installs it, including when `update-all` runs without a graphical session. WSL skips it even when WSLg sets a display. Omarchy is refused.

## Settings

Groundwork does not write FreeTube settings. FreeTube creates `~/.var/app/io.freetubeapp.FreeTube/config/FreeTube` when you use the app. That directory is the data location for the shared Syncthing contract; this repository does not seed it.

## Keeping the engine clean

The apply hook is local to the engine checkout on this machine. It is not a commit in `groundwork-mac`. If `git status` in the engine lists only `home/run_after_33-groundwork-linux-desktop-apps.sh`, run `bash bootstrap.sh` again. Bootstrap ignores that hook and continues. Other local engine edits still stop setup until you reconcile them.

`git clean -fdx` in the engine checkout removes the hook. Installer fixes in this repository apply on the next `bash bootstrap.sh`. Pulling the engine does not refresh the helper or the hook.

Removing FreeTube from later applies means deleting the hook. A missing helper only skips FreeTube, and the rest of the apply continues. Run `bash bootstrap.sh` on a clean engine to restore the hook and the helper.
