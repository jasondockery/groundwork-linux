#!/usr/bin/env bash
# Local apply hook installed by groundwork-linux bootstrap.sh.
# chezmoi apply runs it, which is how update-all and groundwork-update
# install or update the FreeTube Flatpak. The helper owns the skip rules.
set -euo pipefail

helper="${GROUNDWORK_LINUX_DESKTOP_APPS:-$HOME/.local/lib/groundwork-linux/install-desktop-apps.sh}"
if [[ ! -x "$helper" ]]; then
  echo "Groundwork: Linux desktop app helper is missing: $helper" >&2
  echo "Re-run bootstrap.sh from groundwork-linux to restore it." >&2
  exit 1
fi
exec "$helper" "$@"
