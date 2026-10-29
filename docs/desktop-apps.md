# Desktop apps on Linux

Linux desktops install FreeTube by default, and offer Brave from Brave's official package repository. FreeTube is a private YouTube client with no Google sign-in; subscriptions, history, and playlists stay in its own data directory. The package is the Flathub user Flatpak `io.freetubeapp.FreeTube`.

Desktop Macs install FreeTube from the official pinned disk image in the shared engine. Homebrew disabled the `freetube` cask, so the engine does not declare that cask. The disk image is desktop Macs only. Linux and WSL never receive it. This entry point installs the Flatpak. Omarchy keeps its own package path and is refused here.

## When it installs

`bash bootstrap.sh` copies `install-desktop-apps.sh`, `install-brave.sh`, and `brave.json` to `~/.local/lib/groundwork-linux/` and writes `home/run_after_33-groundwork-linux-desktop-apps.sh` into the local engine checkout. `brave.json` is copied from the `core` submodule, groundwork-core v0.7.0. That hook path is listed in the checkout's `.git/info/exclude`, so `git status` in the engine stays clean. `chezmoi apply` runs the hook. `update-all` and `groundwork-update` both apply the engine, so both run the hook. The hook runs FreeTube and Brave. A missing helper skips only that app.

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

Removing FreeTube from later applies means deleting the hook. A missing helper only skips that app, and the rest of the apply continues. Run `bash bootstrap.sh` on a clean engine to restore the hook and the helpers.

## Brave

Brave is the browser Groundwork offers on a non-Omarchy Linux desktop. Shields, Brave's built-in blocker, blocks ads and trackers. The install follows the per-family steps on [brave.com/linux](https://brave.com/linux/). Groundwork does not run `curl | sh`, and it does not install the Flatpak or the Snap. Those packages stay if you already have them. Groundwork does not uninstall a browser or delete profile data.

The browser choice, the policy overrides, and the extension offer come from [`core/browser/brave.json`](https://github.com/jasondockery/groundwork-core/blob/v0.7.0/browser/brave.json) in groundwork-core v0.7.0. This repository renders that file. It does not keep a second list. The contract for people is [Brave, the default browser](https://github.com/jasondockery/groundwork-core/blob/v0.7.0/docs/browser.md).

Reviewed on 2026-10-29 against that spec and against [brave.com/linux](https://brave.com/linux/). The spec records Brave's policy defaults from brave-core `cd9be34acde11812242364dded5f6aa7284be206`. A later Brave release that changes one of those defaults, or a change to the Linux install page, invalidates the review. Groundwork does not pin a Brave build number. Brave's official stable repository supplies package updates. That is the method on Brave's page.

### Install

| Family | What Groundwork runs after you say yes |
| --- | --- |
| Debian, Ubuntu, Mint | Brave's apt keyring and `brave-browser-release.sources`, then `apt install brave-browser` |
| Fedora 41 and newer | `dnf config-manager addrepo --from-repofile=https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo`, then `dnf install brave-browser` |
| Fedora before 41, and RHEL | `dnf config-manager --add-repo` with that same repo file, then `dnf install brave-browser` |
| openSUSE | `zypper addrepo` with that repo file, then `zypper install brave-browser` |
| Arch | `brave-bin` from the AUR when `paru`, `pikaur`, or `yay` is installed. Otherwise Groundwork prints `yay -Sy brave-bin` and installs nothing. |
| Fedora Atomic | Groundwork prints the `rpm-ostree` commands and installs nothing. The install needs a reboot. |
| Any other family | One line with https://brave.com/linux/. Nothing is installed. |

Brave publishes amd64 and arm64 packages. After you confirm, the package command is non-interactive. Headless machines and WSL skip Brave, using the same rules as FreeTube. Omarchy is refused.

The install needs administrator permission for the repository, the package, and the policy file. When a terminal is present, Groundwork asks once. The default is no. With no terminal, Groundwork writes nothing and does not record the install as done. Run `install-brave.sh` from a terminal to retry.

`groundwork-update` (configuration-only) installs Brave when it is missing and leaves an installed Brave alone. `update-all` does not upgrade Brave. It installs Brave only when administrator permission is already available without a prompt, rewrites the policy file when the rendered policy changed, and prints at most one default-browser notice. It does not ask.

### Default browser

When Brave is installed and `xdg-settings get default-web-browser` is not `brave-browser.desktop`, an interactive apply asks `Make Brave the default browser? [y/N]`. Yes runs `xdg-settings set default-web-browser brave-browser.desktop`. No is saved in `~/.config/groundwork/brave-default-declined`. Delete that file to be asked again. `update-all`, and any run without a terminal, print one notice with that command and do not change the default.

### Policies and Bitwarden

Groundwork writes `/etc/brave/policies/managed/groundwork.json`, owner root, group root, mode 0644. The JSON is the policy names and values from `brave.json` whose value differs from Brave's upstream default. A row that matches the upstream default is not written. `PasswordManagerEnabled` is included because Bitwarden is the password manager in the spec. A second run that renders the same JSON does not rewrite the file.

Bitwarden (`nngceckbapebfimnlniiiahkandclblb`) is the only extension the spec offers. Groundwork asks before writing `/usr/share/chromium/extensions/nngceckbapebfimnlniiiahkandclblb.json` with the Chrome Web Store update URL. The default is no. Brave then offers the extension. Groundwork does not force-install it. Chromium uses that same external-extension path, so Chromium offers it too when Chromium is installed. Confirm that offer on a real desktop. A decline is saved in `~/.config/groundwork/brave-extension-declined`.

### Other browsers

If Chrome or Chromium is on `PATH`, Groundwork prints one line about importing at `brave://settings/importData`. It does not remove that browser or its profile. If Brave is installed from Flatpak or Snap and the official package is not, Groundwork offers to install the official package and keep that data directory. It does not uninstall Flatpak or Snap, and it does not delete their data. A decline is saved in `~/.config/groundwork/brave-repo-move-declined`.

### What the fixture tests do not prove

The tests stub `apt`, `dnf`, `zypper`, `sudo`, and `xdg-settings`. They do not install Brave. On a real Ubuntu or Fedora desktop, still check that Brave installs, `brave://policy` shows these policies, the default changes only after a yes, and Bitwarden is offered.

### Remove Groundwork's Brave configuration

Groundwork does not uninstall Brave. Remove the `brave-browser` package with your distribution's package manager, or remove `brave-bin` with the AUR helper. Delete `/etc/brave/policies/managed/groundwork.json` and `/usr/share/chromium/extensions/nngceckbapebfimnlniiiahkandclblb.json` to drop the policy and the extension offer. Delete the decline files in `~/.config/groundwork/` to be asked again. Brave's profile, and any Flatpak or Snap data, stay until you delete them yourself.
