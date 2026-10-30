# Desktop apps on Linux

Linux desktops install FreeTube by default, install Brave from Brave's official package repository and make it the default browser once. FreeTube is a private YouTube client with no Google sign-in; subscriptions, history, and playlists stay in its own data directory. The package is the Flathub user Flatpak `io.freetubeapp.FreeTube`.

Desktop Macs install FreeTube from the official pinned disk image in the shared engine. Homebrew disabled the `freetube` cask, so the engine does not declare that cask. The disk image is desktop Macs only. Linux and WSL never receive it. This entry point installs the Flatpak. Omarchy keeps its own package path and is refused here.

## When it installs

`bash bootstrap.sh` copies `install-desktop-apps.sh`, `install-brave.sh`, and `brave.json` to `~/.local/lib/groundwork-linux/` and writes `home/run_after_33-groundwork-linux-desktop-apps.sh` into the local engine checkout. `brave.json` is copied from the `core` submodule, groundwork-core. That hook path is listed in the checkout's `.git/info/exclude`, so `git status` in the engine stays clean. `chezmoi apply` runs the hook. `update-all` and `groundwork-update` both apply the engine, so both run the hook. The hook runs FreeTube and Brave. A missing helper skips only that app.

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

The browser choice, the policy overrides, and the extension offer come from [`core/browser/brave.json`](https://github.com/jasondockery/groundwork-core/blob/main/browser/brave.json) in groundwork-core. This repository renders that file. It does not keep a second list. The contract for people is [Brave, the default browser](https://github.com/jasondockery/groundwork-core/blob/main/docs/browser.md).

Reviewed on 2026-10-29 against that spec and against [brave.com/linux](https://brave.com/linux/). The spec records Brave's policy defaults from brave-core `cd9be34acde11812242364dded5f6aa7284be206`. A later Brave release that changes one of those defaults, or a change to the Linux install page, invalidates the review. Groundwork does not pin a Brave build number. Brave's official stable repository supplies package updates. That is the method on Brave's page.

### Install

| Family | What Groundwork runs after you say yes |
| --- | --- |
| Debian, Ubuntu, Mint | `curl` when it is missing (`sudo apt install curl`), then Brave's apt keyring and `brave-browser-release.sources`, then `apt install brave-browser` |
| Fedora 41 and newer | `dnf install dnf-plugins-core`, then `dnf config-manager addrepo --from-repofile=https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo`, then `dnf install brave-browser` |
| Fedora before 41, and RHEL | `dnf install dnf-plugins-core`, then `dnf config-manager --add-repo` with that same repo file, then `dnf install brave-browser` |
| openSUSE | `zypper --non-interactive --gpg-auto-import-keys addrepo` with that repo file, then the same flags on `zypper install brave-browser` |
| Arch | `brave-bin` from the AUR when `paru`, `pikaur`, or `yay` is installed. Otherwise Groundwork prints `yay -Sy brave-bin` and installs nothing. |
| Fedora Atomic | Groundwork prints the `rpm-ostree` commands and installs nothing. The install needs a reboot. |
| Any other family | One line with https://brave.com/linux/. Nothing is installed. |

Brave publishes amd64 and arm64 packages. After you confirm, the package command is non-interactive. A failed keyring or sources download removes only its temporary file. The previous file stays until a later download succeeds and replaces it. If the Fedora, RHEL, or openSUSE repo file is missing or empty, Groundwork deletes `~/.config/groundwork/brave-rpm-repo-added` and adds the repository again. Headless machines and WSL skip Brave, using the same rules as FreeTube. Omarchy is refused.

The install needs administrator permission for the repository, the package, and the policy file. When a terminal is present, Groundwork asks once. The default is no. With no terminal, Groundwork writes nothing and does not record the install as done. Run `install-brave.sh` from a terminal to retry.

`groundwork-update` (configuration-only) installs Brave when it is missing and a terminal can ask, and leaves an installed Brave alone apart from the one-time default switch below. `update-all` does not install or upgrade Brave. With no terminal it prints one notice and leaves Brave uninstalled. When Brave is already installed, it rewrites the policy file when the rendered policy changed and handles the default as below. It does not ask.

### Default browser

Brave becomes the default once, automatically (Jason's decision, 2026-10-30; contract in groundwork-core `docs/browser.md`, "Setting the default"). The steps:

1. Brave is installed and `xdg-settings get default-web-browser` is not already `brave-browser.desktop`. If it already is, Groundwork only records that and never touches it again.
2. A local desktop session exists (`DISPLAY` or `WAYLAND_DISPLAY`, and no `SSH_CONNECTION` or `SSH_TTY`, so `ssh -X` does not count). With none (SSH, cron, WSL, headless), Groundwork changes nothing and prints one line saying to run `install-brave.sh` from a terminal on the desktop.
3. A launch check passes. Groundwork says a Brave window will open, then starts the installed Brave with a throwaway profile (`--user-data-dir` in a temporary directory, a private `HOME`, `XDG_*` and 0700 `XDG_RUNTIME_DIR`, no D-Bus address or caller runtime directory, only the display: the absolute Wayland socket path, or `DISPLAY` and `XAUTHORITY` on X11. It runs in its own process group, which is killed afterwards, and its core size limit is 1 block so a piped core handler does not save a dump). It must stay up for 5 seconds, then close on SIGTERM within 10 seconds with status 0. The temporary directory is deleted. Your Brave profile is never opened. A crash, early exit, or hang prints one line, changes nothing, and is not remembered, so the next run checks again.
4. If the current default is unset or the distribution's stock browser (`firefox.desktop`, `firefox-esr.desktop`, `org.mozilla.firefox.desktop`, `firefox_firefox.desktop`, `org.gnome.Epiphany.desktop`), Groundwork runs `xdg-settings set default-web-browser brave-browser.desktop` without asking, whether or not a terminal is present. `update-all` included. It then verifies with `xdg-settings get default-web-browser` and prints one line saying so and how to switch back: `xdg-settings set default-web-browser <previous>`, or the desktop's Default Applications settings when there was no previous default.
5. Any other default was chosen by the person, so it only gets the offer: `Make Brave the default browser? [y/N]` in a terminal, asked before the launch check, which runs only after a yes. Yes does the check and the switch above. No is saved in `~/.config/groundwork/brave-default-declined`. Without a terminal, one line shows the command and nothing changes.

The switch is recorded in `~/.config/groundwork/brave-default-set` only after `xdg-settings get` confirms it. With that file present, Groundwork never switches or offers again, so a default you pick later stays. A saved decline also stops every later switch and offer. Delete either file to let Groundwork decide again. An unset default counts as stock. On Raspberry Pi OS (`ID=raspbian` or `/etc/rpi-issue`) Chromium counts as stock too; on other distributions that ship Chromium as the default, Chromium is a chosen default and only gets the offer.

To decline ahead of time, create the file before the first run: `mkdir -p ~/.config/groundwork && touch ~/.config/groundwork/brave-default-declined`. Groundwork cannot tell Firefox you chose on Ubuntu from the packaged default, so it treats that as stock.

### Policies and Bitwarden

Groundwork writes `/etc/brave/policies/managed/groundwork.json`, owner root, group root, mode 0644. The JSON is the policy names and values from `brave.json` whose value differs from Brave's upstream default. A row that matches the upstream default is not written. `PasswordManagerEnabled` is included because Bitwarden is the password manager in the spec. A second run that renders the same JSON does not rewrite the file.

Bitwarden (`nngceckbapebfimnlniiiahkandclblb`) is the only extension the spec offers. Groundwork asks before writing `/usr/share/chromium/extensions/nngceckbapebfimnlniiiahkandclblb.json` with the Chrome Web Store update URL. The default is no. Brave then offers the extension. Groundwork does not force-install it. Chromium uses that same external-extension path, so Chromium offers it too when Chromium is installed. Confirm that offer on a real desktop. A decline is saved in `~/.config/groundwork/brave-extension-declined`.

### Other browsers

If Chrome or Chromium is on `PATH`, Groundwork prints one line about importing at `brave://settings/importData`. It does not remove that browser or its profile. If Brave is installed from Flatpak or Snap and the official package is not, Groundwork offers the official package as a separate profile and leaves the Flatpak or Snap copy installed. Bookmarks move only at `brave://settings/importData`. Passwords stay in Bitwarden. It does not uninstall Flatpak or Snap, and it does not delete their data. A decline is saved in `~/.config/groundwork/brave-repo-move-declined`.

### What the fixture tests do not prove

The tests stub `apt`, `dnf`, `zypper`, `sudo`, and `xdg-settings`. They use a fake Brave that stays up or crashes on request, so they do not prove a real window opens or that `xdg-settings` works on any desktop. On a real Ubuntu or Fedora desktop, still check that Brave installs, `brave://policy` shows these policies, the launch check opens and closes a window, `xdg-settings get default-web-browser` prints `brave-browser.desktop` once and stays on a later choice, and Bitwarden is offered.

### Remove Groundwork's Brave configuration

Groundwork does not uninstall Brave. Remove the `brave-browser` package with your distribution's package manager, or remove `brave-bin` with the AUR helper. Delete `/etc/brave/policies/managed/groundwork.json` and `/usr/share/chromium/extensions/nngceckbapebfimnlniiiahkandclblb.json` to drop the policy and the extension offer. While Brave stays installed, the next apply rewrites `groundwork.json` when the rendered policy is missing or changed. Dropping the offer also requires deleting `~/.config/groundwork/brave-extension-accepted`, or that apply writes the offer file again without asking. Also delete Brave's repository files, or apt, dnf, and zypper keep using that repository:

- `/usr/share/keyrings/brave-browser-archive-keyring.gpg`
- `/etc/apt/sources.list.d/brave-browser-release.sources`
- `/etc/yum.repos.d/brave-browser.repo`
- `/etc/zypp/repos.d/brave-browser.repo`
- `~/.config/groundwork/brave-rpm-repo-added`

`brave-rpm-repo-added` is not a gate. The installer does not read it. Delete it with the repo file if an older run left it behind. If the repo file is already gone, the next install removes that marker and adds the repository again. Delete the decline files in `~/.config/groundwork/` to be asked again. Brave's profile, and any Flatpak or Snap data, stay until you delete them yourself.
