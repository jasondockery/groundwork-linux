#!/usr/bin/env bash
# Install or update EasyEffects on a Linux desktop.
# Package: Flathub user Flatpak com.github.wwmm.easyeffects.
# Headless and WSL targets skip it. Omarchy is refused. A machine without
# PipeWire skips it because EasyEffects does not support PulseAudio.
# A distribution package or system Flatpak already on the machine is kept;
# Groundwork does not replace it or write EasyEffects settings.
# update-all runs this with GROUNDWORK_UPDATE_SCOPE=maintenance and updates an
# existing user Flatpak. A configuration-only apply installs it when missing and
# leaves an existing install unchanged. A failed remote-add, install, or update
# warns and returns success so the rest of chezmoi apply continues; the next
# update-all retries EasyEffects. A missing flatpak command still fails. This
# script does not write EasyEffects settings.
# bash 4.0+ (Linux).
set -euo pipefail

APP_ID=com.github.wwmm.easyeffects
FLATHUB_URL=https://dl.flathub.org/repo/flathub.flatpakrepo

usage() {
  echo "Usage: $0"
  echo "Install or update EasyEffects, the Flathub user Flatpak ${APP_ID}."
  echo "Headless and WSL targets skip it. Omarchy is refused."
  echo "A machine without PipeWire skips it. EasyEffects needs PipeWire."
  echo "A distribution package already installed is kept."
  echo "Groundwork does not write EasyEffects settings."
  echo "update-all updates an existing user Flatpak. A configuration-only apply keeps one."
}

for arg in "$@"; do
  case "$arg" in
    --help | -h) usage; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; usage >&2; exit 64 ;;
  esac
done

[[ "$(uname -s)" == Linux ]] || { echo "Run this installer on Linux." >&2; exit 1; }
# GROUNDWORK_OMARCHY_DIR lets a fixture stand in for /usr/share/omarchy.
omarchy_share="${GROUNDWORK_OMARCHY_DIR:-/usr/share/omarchy}"
if command -v omarchy >/dev/null 2>&1 || [[ -d "$omarchy_share" ]]; then
  echo "Omarchy owns this environment. Use groundwork-omarchy-mac-arm64 on Apple Silicon." >&2
  exit 1
fi

is_wsl() {
  local osrelease="" file lower
  file="${GROUNDWORK_OSRELEASE_FILE:-/proc/sys/kernel/osrelease}"
  if [[ -r "$file" ]]; then
    osrelease="$(<"$file")"
  fi
  lower="${osrelease,,}"
  if [[ "$lower" == *microsoft* ]]; then
    return 0
  fi
  [[ -n "${WSL_DISTRO_NAME:-}" || -n "${WSL_INTEROP:-}" ]]
}

read_headless_answer() {
  local config line value
  config="${XDG_CONFIG_HOME:-$HOME/.config}/chezmoi/chezmoi.toml"
  [[ -f "$config" ]] || return 2
  line="$(grep -E '^[[:space:]]*headless[[:space:]]*=' "$config" | head -n 1 || true)"
  [[ -n "$line" ]] || return 2
  value="${line#*=}"
  value="${value%%#*}"
  value="${value//[[:space:]]/}"
  case "$value" in
    true | false) printf '%s\n' "$value" ;;
    *) return 2 ;;
  esac
}

pipewire_available() {
  command -v pipewire >/dev/null 2>&1 || command -v pw-cli >/dev/null 2>&1
}

if is_wsl; then
  echo "Groundwork: skipping EasyEffects on WSL."
  exit 0
fi

if answer="$(read_headless_answer)"; then
  if [[ "$answer" == true ]]; then
    echo "Groundwork: skipping EasyEffects on a headless machine."
    exit 0
  fi
elif [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  echo "Groundwork: skipping EasyEffects on a headless machine."
  exit 0
fi

if ! pipewire_available; then
  echo "Groundwork: skipping EasyEffects because PipeWire is not available. EasyEffects is a PipeWire equalizer and does not support PulseAudio."
  exit 0
fi

if command -v easyeffects >/dev/null 2>&1; then
  echo "Groundwork: keeping the installed EasyEffects. Groundwork does not replace a distribution package or write EasyEffects settings."
  exit 0
fi

if ! command -v flatpak >/dev/null 2>&1; then
  echo "EasyEffects needs Flatpak on this desktop. Install the flatpak package from your distribution, then rerun this script or update-all." >&2
  echo "Ubuntu/Debian: sudo apt install flatpak" >&2
  echo "Arch, Fedora, and Debian/Ubuntu also package easyeffects if you prefer the distribution install." >&2
  exit 1
fi

installed=0
if flatpak info --user "$APP_ID" >/dev/null 2>&1; then
  installed=1
elif flatpak info --system "$APP_ID" >/dev/null 2>&1; then
  echo "Groundwork: keeping the installed EasyEffects. Groundwork does not replace a system Flatpak or write EasyEffects settings."
  exit 0
fi

if [[ "$installed" -eq 1 && "${GROUNDWORK_UPDATE_SCOPE:-}" == configuration ]]; then
  echo "Configuration-only apply: keeping the installed EasyEffects. Run update-all to update it."
  exit 0
fi

flatpak_continue() {
  echo "Groundwork: EasyEffects wasn't installed or updated. The rest of the apply continues. Run update-all to retry it." >&2
  exit 0
}

flatpak remote-add --user --if-not-exists flathub "$FLATHUB_URL" || flatpak_continue
if [[ "$installed" -eq 0 ]]; then
  flatpak install --user -y --noninteractive flathub "$APP_ID" || flatpak_continue
  printf 'Groundwork: installed EasyEffects (%s) for this user.\n' "$APP_ID"
else
  flatpak update --user -y --noninteractive "$APP_ID" || flatpak_continue
  printf 'Groundwork: updated EasyEffects (%s).\n' "$APP_ID"
fi
