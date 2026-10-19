# groundwork-linux

The non-Omarchy Linux entry point for the Groundwork environment: T3 Code Nightly, Herdr, and Omarchy-style terminal habits where they fit. Omarchy on Apple Silicon uses [groundwork-omarchy-mac-arm64](https://github.com/jasondockery/groundwork-omarchy-mac-arm64) instead.

The existing shared provisioning implementation currently lives in `groundwork-mac`. This repo selects the Linux entry point and documents migration and OS operations; it does not fork that implementation. The visible engine checkout remains the chezmoi source and update owner. Shared operational guidance lives in [groundwork-core](https://github.com/jasondockery/groundwork-core); the original Groundwork curriculum remains available and unchanged.

## Setup

Clone this repo over HTTPS into a new directory; keep an old Groundwork checkout in place. Install Git and chezmoi through their supported OS sources first. Read `bootstrap.sh`, then run `bash bootstrap.sh` on Linux. For an existing installation, use [migration](docs/migration.md) instead so you can preview the new source before applying it.

`GROUNDWORK_ENGINE_DIR` selects the shared engine checkout, defaulting to `~/code/groundwork-mac`. `GROUNDWORK_REPO_URL` selects its Git URL, defaulting to `https://github.com/jasondockery/groundwork-mac.git`. Public HTTPS access needs no GitHub login. If your existing engine uses SSH, set this variable to that exact origin URL before running the wrapper; its remote is preserved. Existing engine checkouts must match that URL and be clean. The engine's own platform checks and installation requirements remain authoritative; this wrapper does not broaden supported architectures or desktop promises.

Read [Tailscale setup](docs/tailscale.md), choose the terminal multiplexer with `groundwork-configure`, and use its live prefix help. The target is Omarchy's `Ctrl+Space`, Alt+Enter splits, Ctrl+Alt+arrow pane focus, and matching tab/session actions. Existing selections and local overrides remain yours; choosing Both keeps tmux available alongside Herdr for tmux lessons.

## Updates and ownership

Desktop applies also prepare the shared engine's `groundwork-remote-desktop` helper. On GNOME, finish Settings → System → Remote Desktop → Desktop Sharing once; subsequent applies preserve its credentials and enable/start its native user service. Use an RDP client, including Windows App on a Mac, and the port shown by GNOME. Headless, container and WSL environments do not get a desktop service. Other compositors retain their own supported sharing path; Groundwork does not replace the desktop. See [desktop access](docs/tailscale.md#desktop-access).

Update this entry point with a reviewed `git pull --ff-only`. The engine owns applied configuration and `update-all`; do not copy its home files here. T3 Code follows the selected Nightly channel; Herdr follows the engine's supported package source. Neither tool is authenticated automatically. [Shared agent-tool guidance](https://github.com/jasondockery/groundwork-core/blob/main/docs/ai-tools-and-remote-access.md) explains the boundary.

## License

[MIT](LICENSE), matching the Groundwork family.

## Common developer setup and macOS containers

The family uses one developer tool set across personal and managed machines, with independent identity and optional-app preferences. See the [shared setup guide](https://github.com/jasondockery/groundwork-core/blob/main/docs/developer-setup.md) for tool and platform ownership.

For a macOS machine, Groundwork recommends Colima plus the Docker CLI. The single [Docker Desktop to Colima guide](https://github.com/jasondockery/groundwork-mac/blob/main/docs/docker-desktop-to-colima.md) covers migration scenarios, data transfer, verification, rollback, and Docker Desktop uninstallation after acceptance. This recommendation applies to macOS; this repository’s Linux, WSL, or Omarchy environment keeps its native container path.
