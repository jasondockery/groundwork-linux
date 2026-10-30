#!/usr/bin/env bash
# Local apply hook installed by groundwork-linux bootstrap.sh.
# chezmoi apply runs it, which is how update-all and groundwork-update
# install FreeTube and Brave (Brave becomes the default once). Each helper owns its skip rules.
# bash 4.0+ (Linux).
set -euo pipefail

run_helper() {
  local helper="$1"
  local label="$2"
  shift 2
  if [[ ! -x "$helper" ]]; then
    echo "Groundwork: ${label} helper is not executable: ${helper}" >&2
    echo "Groundwork: a missing helper only skips ${label}. The rest of the apply continues." >&2
    return 0
  fi
  "$helper" "$@"
}

freetube="${GROUNDWORK_LINUX_DESKTOP_APPS:-$HOME/.local/lib/groundwork-linux/install-desktop-apps.sh}"
brave="${GROUNDWORK_LINUX_BRAVE:-$HOME/.local/lib/groundwork-linux/install-brave.sh}"
freetube_status=0
brave_status=0
run_helper "$freetube" "FreeTube" "$@" || freetube_status=$?
run_helper "$brave" "Brave" "$@" || brave_status=$?
if [[ "$freetube_status" -ne 0 ]]; then
  exit "$freetube_status"
fi
exit "$brave_status"
