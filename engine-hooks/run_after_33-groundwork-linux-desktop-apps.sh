#!/usr/bin/env bash
# Local apply hook installed by groundwork-linux bootstrap.sh.
# chezmoi apply runs it, which is how update-all and groundwork-update
# install or update the FreeTube Flatpak. The helper owns the skip rules.
set -euo pipefail

helper="${GROUNDWORK_LINUX_DESKTOP_APPS:-$HOME/.local/lib/groundwork-linux/install-desktop-apps.sh}"
if [[ ! -x "$helper" ]]; then
  echo "Groundwork: Linux desktop app helper is not executable: $helper" >&2
  echo "Groundwork: a missing helper only skips FreeTube. The rest of the apply continues." >&2
  exit 0
fi
exec "$helper" "$@"
