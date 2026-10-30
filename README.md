# groundwork-linux

The non-Omarchy Linux entry point for the Groundwork environment: T3 Code Nightly, Herdr, and Omarchy-style terminal habits where they fit. Omarchy on Apple Silicon uses [groundwork-omarchy-mac-arm64](https://github.com/jasondockery/groundwork-omarchy-mac-arm64) instead.

The existing shared provisioning implementation currently lives in `groundwork-mac`. This repo selects the Linux entry point and documents migration and OS operations; it does not fork that implementation. The visible engine checkout remains the chezmoi source and update owner. Shared operational guidance lives in [groundwork-core](https://github.com/jasondockery/groundwork-core); the original Groundwork curriculum remains available and unchanged.

## Setup

Clone this repo over HTTPS into a new directory; keep an old Groundwork checkout in place. Install Git and chezmoi through their supported OS sources first. Run `git submodule update --init core` so setup can read the Brave spec in groundwork-core. A Linux desktop also needs Flatpak from the distribution (Ubuntu/Debian: `sudo apt install flatpak`) so setup can install FreeTube, and administrator permission when you choose to install Brave. Headless and WSL targets skip those apps. Read `bootstrap.sh`, then run `bash bootstrap.sh` on Linux. For an existing installation, use [migration](docs/migration.md) instead so you can preview the new source before applying it.

`GROUNDWORK_ENGINE_DIR` selects the shared engine checkout, defaulting to `~/code/groundwork-mac`. `GROUNDWORK_REPO_URL` selects its Git URL, defaulting to `https://github.com/jasondockery/groundwork-mac.git`. Public HTTPS access needs no GitHub login. If your existing engine uses SSH, set this variable to that exact origin URL before running the wrapper; its remote is preserved. Existing engine checkouts must match that URL and be clean. The engine's own platform checks and installation requirements remain authoritative; this wrapper does not broaden supported architectures or desktop promises.

Read [Tailscale setup](docs/tailscale.md), choose the terminal multiplexer with `groundwork-configure`, and use its live prefix help. The target is Omarchy's `Ctrl+Space`, Alt+Enter splits, Ctrl+Alt+arrow pane focus, and matching tab/session actions. Existing selections and local overrides remain yours; choosing Both keeps tmux available alongside Herdr for tmux lessons.

## Updates and ownership

Desktop applies also prepare the shared engine's `groundwork-remote-desktop` helper. On GNOME, finish Settings → System → Remote Desktop → Desktop Sharing once; subsequent applies preserve its credentials and enable/start its native user service. Use an RDP client, including Windows App on a Mac, and the port shown by GNOME. Headless, container and WSL environments do not get a desktop service. Other compositors retain their own supported sharing path; Groundwork does not replace the desktop. See [desktop access](docs/tailscale.md#desktop-access).

After setup, run `update-all` from any directory for normal Groundwork tool
updates and maintenance. Run `groundwork-update` to synchronize and apply only
configuration using saved settings. Configuration applies can install newly
declared tools; they do not request routine upgrades or cleanup. Existing
installations receive the new command on their next successful `update-all`.
Use `groundwork-configure` to change preferences.

On a Linux desktop, `update-all` also installs or updates FreeTube, the Flathub
user Flatpak `io.freetubeapp.FreeTube`. `groundwork-update` installs that
Flatpak when it is missing and leaves an existing install unchanged. The same
apply installs Brave from Brave's official package repository and makes it the
default browser once. `update-all` does not install or upgrade Brave. The
distribution's updater upgrades an installed Brave from that repository. With
no terminal, `update-all` prints one notice and leaves Brave uninstalled. When
Brave is already installed, it rewrites managed policies when they changed.
In a desktop session it may make the one-time default switch when the current
default is unset or the distribution's stock browser, and otherwise prints at
most one default-browser notice. It does not ask questions. See [desktop apps](docs/desktop-apps.md).

Both commands belong to the visible `groundwork-mac` engine checkout selected
during setup. This entry-point checkout contains setup guidance, not applied
home files, and does not need pulling before daily maintenance. Pull it with
`git pull --ff-only` only when you need newer entry-point documentation or
bootstrap code, after reviewing local changes. Keep Linux OS updates with your
distribution's supported updater; `update-all` does not promise a distribution
upgrade. Do not copy the engine's home files here.

T3 Code follows the selected Nightly channel; Herdr follows the engine's
supported package source. Neither tool is authenticated automatically.
[Shared agent-tool guidance](https://github.com/jasondockery/groundwork-core/blob/main/docs/ai-tools-and-remote-access.md)
explains the boundary.

## Desktop apps

Linux desktops install [FreeTube](https://freetubeapp.io/) by default: a private YouTube client with no Google sign-in. The package is the Flathub user Flatpak `io.freetubeapp.FreeTube`. Desktop Macs get the official pinned FreeTube disk image from the shared engine. Homebrew disabled the `freetube` cask, so the engine does not declare it. Linux and WSL never receive that disk image. This repository installs the Linux Flatpak and skips it on headless and WSL targets. Groundwork writes no FreeTube settings.

The same desktops offer [Brave](https://brave.com/linux/) from Brave's official package repository and make it the default browser once, with `xdg-settings`, after a short launch check passes (a Brave window opens in a throwaway profile for a few seconds). Groundwork never overrides a default you chose later, respects a saved no, and only offers when your default is not the distribution's stock browser. With no desktop session it defers and prints one line. Policies and the Bitwarden offer are rendered from groundwork-core (`core/browser/brave.json`). Groundwork does not uninstall another browser or delete profile data. See [desktop apps](docs/desktop-apps.md).

## History purges (opt-in)

`bash bootstrap.sh --with-git-filter-repo` installs `git-filter-repo` for your user with pipx, with no root. It is off by default and is never installed otherwise. Setup never rewrites history. The procedure is the shared [history purge runbook](https://github.com/jasondockery/groundwork-core/blob/v0.8.1/docs/history-purge.md); the proof check and removal are in [git-filter-repo](docs/git-filter-repo.md).

## License

[MIT](LICENSE), matching the Groundwork family.

## Common developer setup and macOS containers

The family uses one developer tool set across personal and managed machines, with independent identity and optional-app preferences. See the [shared setup guide](https://github.com/jasondockery/groundwork-core/blob/main/docs/developer-setup.md) for tool and platform ownership.

For a macOS machine, Groundwork recommends Colima plus the Docker CLI. The single [Docker Desktop to Colima guide](https://github.com/jasondockery/groundwork-mac/blob/main/docs/docker-desktop-to-colima.md) covers migration scenarios, data transfer, verification, rollback, and Docker Desktop uninstallation after acceptance. This recommendation applies to macOS; this repository’s Linux, WSL, or Omarchy environment keeps its native container path.
