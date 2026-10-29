#!/usr/bin/env bash
# bash 4.0+ (Linux). Install Brave from Brave's official package repository.
# Policies and the extension offer are rendered from core/browser/brave.json
# (groundwork-core v0.7.0). This script does not uninstall a browser or delete
# profile data. Prompts default to no.
# Fixture seams, not user settings: GROUNDWORK_OS_RELEASE_FILE,
# GROUNDWORK_OSRELEASE_FILE, GROUNDWORK_OMARCHY_DIR, GROUNDWORK_OSTREE_FILE,
# GROUNDWORK_ROOT, GROUNDWORK_BRAVE_SPEC.
set -euo pipefail

BRAVE_PAGE=https://brave.com/linux/
BRAVE_APT_KEY_URL=https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg
BRAVE_APT_SOURCES_URL=https://brave-browser-apt-release.s3.brave.com/brave-browser.sources
BRAVE_RPM_REPO_URL=https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo

usage() {
  echo "Usage: $0"
  echo "Install Brave from its official package repository and offer it as the default browser."
  echo "Debian, Ubuntu, and Mint install curl when it is missing, then use Brave's apt repository."
  echo "Fedora and RHEL install dnf-plugins-core, then add Brave's repo. Fedora 41 and newer use dnf addrepo."
  echo "Older Fedora and RHEL use dnf --add-repo. openSUSE uses non-interactive zypper and imports the repo key."
  echo "Arch uses an AUR helper for brave-bin."
  echo "Fedora Atomic prints the rpm-ostree commands and does not install. Other families print ${BRAVE_PAGE}."
  echo "Headless and WSL targets skip Brave. Omarchy is refused."
  echo "A terminal asks before installing, offering Bitwarden, or changing the default. The default answer is no."
  echo "update-all does not upgrade Brave and does not ask. The distribution updates Brave from Brave's repository."
}

for arg in "$@"; do
  case "$arg" in
    --help | -h) usage; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; usage >&2; exit 64 ;;
  esac
done

note() {
  printf 'Groundwork: %s\n' "$*"
}

warn() {
  printf 'Groundwork: %s\n' "$*" >&2
}

retry_command() {
  printf 'bash %q' "$0"
}

work=""
cleanup() {
  if [[ -n "${work}" ]]; then
    rm -rf "$work"
  fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM

[[ "$(uname -s)" == Linux ]] || { echo "Run this installer on Linux." >&2; exit 1; }

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

if is_wsl; then
  note "skipping Brave on WSL."
  exit 0
fi

if answer="$(read_headless_answer)"; then
  if [[ "$answer" == true ]]; then
    note "skipping Brave on a headless machine."
    exit 0
  fi
elif [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  note "skipping Brave on a headless machine."
  exit 0
fi

parse_os_release() {
  local file line key value
  file="${GROUNDWORK_OS_RELEASE_FILE:-/etc/os-release}"
  OS_ID=""
  OS_VERSION_ID=""
  OS_ID_LIKE=""
  OS_VARIANT_ID=""
  [[ -r "$file" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[A-Z0-9_]+= ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    fi
    case "$key" in
      ID) OS_ID="$value" ;;
      VERSION_ID) OS_VERSION_ID="$value" ;;
      ID_LIKE) OS_ID_LIKE="$value" ;;
      VARIANT_ID) OS_VARIANT_ID="$value" ;;
    esac
  done <"$file"
}

is_atomic() {
  case "$OS_VARIANT_ID" in
    silverblue | kinoite | sericea | onyx) return 0 ;;
  esac
  [[ -e "${GROUNDWORK_OSTREE_FILE:-/run/ostree-booted}" ]]
}

distro_family() {
  local like=" ${OS_ID_LIKE} "
  if [[ "$OS_ID" == fedora ]] && is_atomic; then
    printf 'atomic\n'
  elif [[ "$OS_ID" == opensuse-tumbleweed || "$OS_ID" == opensuse-leap || "$OS_ID" == opensuse || "$like" == *" suse "* || "$like" == *" opensuse "* ]]; then
    printf 'opensuse\n'
  elif [[ "$OS_ID" == fedora ]]; then
    printf 'fedora\n'
  elif [[ "$OS_ID" == rhel || "$OS_ID" == centos || "$OS_ID" == rocky || "$OS_ID" == almalinux || "$like" == *" rhel "* || "$like" == *" fedora "* ]]; then
    printf 'rhel\n'
  elif [[ "$OS_ID" == debian || "$OS_ID" == ubuntu || "$OS_ID" == linuxmint || "$OS_ID" == pop || "$OS_ID" == elementary || "$like" == *" debian "* || "$like" == *" ubuntu "* ]]; then
    printf 'debian\n'
  elif [[ "$OS_ID" == arch ]]; then
    printf 'arch\n'
  else
    printf 'unknown\n'
  fi
}

root_path() {
  printf '%s%s' "${GROUNDWORK_ROOT:-}" "$1"
}

state_dir() {
  printf '%s/groundwork' "${XDG_CONFIG_HOME:-$HOME/.config}"
}

marked() {
  [[ -f "$(state_dir)/$1" ]]
}

mark_state() {
  local dir
  dir="$(state_dir)"
  mkdir -p "$dir"
  : >"${dir}/$1"
}

interactive() {
  [[ -t 0 && -t 2 && "${GROUNDWORK_UPDATE_SCOPE:-}" != maintenance ]]
}

# Prints a prompt and reads one answer. Returns 0 for yes, 1 for no, 2 for EOF.
confirm() {
  local prompt="$1" answer
  while true; do
    printf '%s [y/N] ' "$prompt" >&2
    if ! IFS= read -r answer; then
      printf '\n' >&2
      return 2
    fi
    case "$answer" in
      y | Y | yes | Yes | YES) return 0 ;;
      n | N | no | No | NO | "") return 1 ;;
      *) printf 'Enter y or n.\n' >&2 ;;
    esac
  done
}

SUDO_NONINTERACTIVE=0
sudo_announced=0
sudo_cmd() {
  if [[ "$SUDO_NONINTERACTIVE" -eq 1 ]]; then
    sudo -n "$@"
    return
  fi
  if [[ "$sudo_announced" -eq 0 ]]; then
    printf 'Groundwork: if sudo asks for a password, that prompt is next.\n' >&2
    sudo_announced=1
  fi
  sudo "$@"
}

brave_installed() {
  if command -v brave-browser >/dev/null 2>&1; then
    return 0
  fi
  [[ -x "$(root_path /usr/bin/brave-browser)" ]]
}

find_aur_helper() {
  local candidate
  AUR_HELPER=""
  for candidate in paru pikaur yay; do
    if command -v "$candidate" >/dev/null 2>&1; then
      AUR_HELPER="$candidate"
      return 0
    fi
  done
  return 1
}

flatpak_brave_present() {
  command -v flatpak >/dev/null 2>&1 || return 1
  flatpak info com.brave.Browser >/dev/null 2>&1
}

snap_brave_present() {
  command -v snap >/dev/null 2>&1 || return 1
  snap list brave >/dev/null 2>&1
}

resolve_spec() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -n "${GROUNDWORK_BRAVE_SPEC:-}" ]]; then
    BRAVE_SPEC="$GROUNDWORK_BRAVE_SPEC"
  elif [[ -f "${script_dir}/brave.json" ]]; then
    BRAVE_SPEC="${script_dir}/brave.json"
  elif [[ -f "${script_dir}/core/browser/brave.json" ]]; then
    BRAVE_SPEC="${script_dir}/core/browser/brave.json"
  else
    BRAVE_SPEC=""
  fi
  if [[ -z "$BRAVE_SPEC" || ! -f "$BRAVE_SPEC" ]]; then
    warn "Brave spec is missing. Initialize the core submodule and rerun bootstrap.sh."
    return 1
  fi
  command -v python3 >/dev/null 2>&1 || {
    warn "python3 is required to read the Brave spec."
    return 1
  }
}

render_spec() {
  work="$(mktemp -d)" || return 1
  python3 - "$BRAVE_SPEC" "$work" <<'PY'
import json
import os
import re
import sys

spec_path, work_dir = sys.argv[1], sys.argv[2]
with open(spec_path, encoding="utf-8") as handle:
    spec = json.load(handle)
if spec.get("schemaVersion") != 1:
    sys.stderr.write("Groundwork: unsupported Brave spec schemaVersion.\n")
    sys.exit(1)
default = spec.get("default") or {}
if default.get("id") != "brave" or default.get("channel") != "release":
    sys.stderr.write("Groundwork: this installer uses Brave release, not Brave Origin.\n")
    sys.exit(1)
desktop = (default.get("desktopIds") or {}).get("linux") or ""
if re.fullmatch(r"[A-Za-z0-9_.-]+\.desktop", desktop) is None:
    sys.stderr.write("Groundwork: the Brave spec has no Linux desktop id.\n")
    sys.exit(1)
extensions = spec.get("extensions") or []
bitwarden = any(
    isinstance(item, dict) and item.get("id") == "nngceckbapebfimnlniiiahkandclblb"
    for item in extensions
)
rendered = {}
for entry in spec.get("policies") or []:
    if not isinstance(entry, dict):
        sys.stderr.write("Groundwork: a Brave policy entry is not an object.\n")
        sys.exit(1)
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        sys.stderr.write("Groundwork: a Brave policy is missing its name.\n")
        sys.exit(1)
    if "value" not in entry or "upstreamDefault" not in entry:
        sys.stderr.write("Groundwork: a Brave policy is missing value or upstreamDefault.\n")
        sys.exit(1)
    reason = entry.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        sys.stderr.write("Groundwork: a Brave policy is missing its reason.\n")
        sys.exit(1)
    if entry["value"] == entry["upstreamDefault"]:
        continue
    condition = entry.get("when")
    if condition is not None:
        if condition == "Bitwarden is the password manager.":
            if not bitwarden:
                continue
        else:
            sys.stderr.write("Groundwork: unsupported Brave policy condition.\n")
            sys.exit(1)
    rendered[name] = entry["value"]
offers = []
for item in extensions:
    if not isinstance(item, dict) or item.get("install") != "offer":
        sys.stderr.write("Groundwork: Brave extensions are offered, never forced.\n")
        sys.exit(1)
    ext_id = item.get("id")
    if re.fullmatch(r"[a-p]{32}", ext_id or "") is None:
        sys.stderr.write("Groundwork: invalid Brave extension id.\n")
        sys.exit(1)
    url = item.get("updateUrl")
    if not isinstance(url, str) or not url.startswith("https://"):
        sys.stderr.write("Groundwork: Brave extension update URL must be https.\n")
        sys.exit(1)
    label = item.get("name") if isinstance(item.get("name"), str) else ext_id
    offers.append({"name": label, "id": ext_id, "updateUrl": url})
os.makedirs(os.path.join(work_dir, "extensions"), exist_ok=True)
with open(os.path.join(work_dir, "policy.json"), "w", encoding="utf-8") as handle:
    json.dump(rendered, handle, indent=2)
    handle.write("\n")
with open(os.path.join(work_dir, "desktop-id"), "w", encoding="utf-8") as handle:
    handle.write(desktop + "\n")
with open(os.path.join(work_dir, "offers.json"), "w", encoding="utf-8") as handle:
    json.dump(offers, handle)
    handle.write("\n")
for offer in offers:
    path = os.path.join(work_dir, "extensions", offer["id"] + ".json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"external_update_url": offer["updateUrl"]}, handle, indent=2)
        handle.write("\n")
PY
  render_status=$?
  [[ "$render_status" -eq 0 ]] || return "$render_status"
  desktop_id="$(<"$work/desktop-id")"
  desktop_id="${desktop_id//$'\n'/}"
}

files_match() {
  [[ -f "$1" && -f "$2" ]] && cmp -s "$1" "$2"
}

write_root_file() {
  local src="$1" dest="$2"
  if files_match "$src" "$dest"; then
    return 0
  fi
  if [[ "$SUDO_NONINTERACTIVE" -eq 1 ]] && ! sudo -n true; then
    warn "A Brave file was not written because administrator permission is not available. Run $(retry_command) from a terminal."
    return 1
  fi
  sudo_cmd install -D -o root -g root -m 0644 "$src" "$dest"
}

# Download as the user, then install the file as root only after curl succeeds.
# A failed transfer deletes the temp file and the destination, including a
# partial file left by an older run. A later success replaces the destination.
fetch_root_file() {
  local url="$1" dest="$2" tmp status
  tmp="$(mktemp)" || return 1
  curl --max-time 60 -fsSLo "$tmp" "$url"
  status=$?
  if [[ "$status" -ne 0 ]]; then
    rm -f "$tmp"
    sudo_cmd rm -f -- "$dest" || true
    return 1
  fi
  if ! sudo_cmd install -D -o root -g root -m 0644 "$tmp" "$dest"; then
    rm -f "$tmp"
    return 1
  fi
  rm -f "$tmp"
}

install_debian() {
  local key src
  key="$(root_path /usr/share/keyrings/brave-browser-archive-keyring.gpg)"
  src="$(root_path /etc/apt/sources.list.d/brave-browser-release.sources)"
  if ! command -v curl >/dev/null 2>&1; then
    sudo_cmd DEBIAN_FRONTEND=noninteractive apt-get install -y curl || {
      warn "curl is not installed, so Brave was not installed. Run: sudo apt install curl"
      return 1
    }
    if ! command -v curl >/dev/null 2>&1; then
      warn "curl is not installed, so Brave was not installed. Run: sudo apt install curl"
      return 1
    fi
  fi
  fetch_root_file "$BRAVE_APT_KEY_URL" "$key" || return 1
  fetch_root_file "$BRAVE_APT_SOURCES_URL" "$src" || return 1
  sudo_cmd apt update || return 1
  sudo_cmd DEBIAN_FRONTEND=noninteractive apt install -y brave-browser || return 1
}

install_dnf() {
  local repo form
  form="$1"
  repo="$(root_path /etc/yum.repos.d/brave-browser.repo)"
  if [[ ! -f "$repo" && ! -f "$(state_dir)/brave-rpm-repo-added" ]]; then
    sudo_cmd dnf install -y dnf-plugins-core || {
      warn "dnf config-manager is not available, so Brave was not installed. Run: sudo dnf install dnf-plugins-core"
      return 1
    }
    if [[ "$form" == dnf5 ]]; then
      sudo_cmd dnf config-manager addrepo --from-repofile="$BRAVE_RPM_REPO_URL" || return 1
    else
      sudo_cmd dnf config-manager --add-repo "$BRAVE_RPM_REPO_URL" || return 1
    fi
    mark_state brave-rpm-repo-added
  fi
  sudo_cmd dnf install -y brave-browser || return 1
}

install_opensuse() {
  local repo
  repo="$(root_path /etc/zypp/repos.d/brave-browser.repo)"
  if [[ ! -f "$repo" && ! -f "$(state_dir)/brave-rpm-repo-added" ]]; then
    sudo_cmd zypper --non-interactive --gpg-auto-import-keys addrepo "$BRAVE_RPM_REPO_URL" || return 1
    mark_state brave-rpm-repo-added
  fi
  sudo_cmd zypper --non-interactive --gpg-auto-import-keys install brave-browser || return 1
}

install_arch() {
  printf 'Groundwork: the AUR helper may ask for an administrator password. That prompt is next.\n' >&2
  "$AUR_HELPER" -Sy --noconfirm brave-bin
}

install_family() {
  case "$family" in
    debian) install_debian ;;
    fedora)
      if [[ "$fedora_major" -ge 41 ]]; then
        install_dnf dnf5
      else
        install_dnf dnf4
      fi
      ;;
    rhel) install_dnf dnf4 ;;
    opensuse) install_opensuse ;;
    arch) install_arch ;;
    *) return 1 ;;
  esac
}

report_other_browsers() {
  local name found=0
  for name in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$name" >/dev/null 2>&1; then
      found=1
    fi
  done
  if [[ "$found" -eq 1 ]]; then
    note "Chrome or Chromium is installed. Import bookmarks, passwords, and history in Brave at brave://settings/importData. Groundwork will not remove it or its profile."
  fi
}

offer_names() {
  python3 - "$work/offers.json" <<'PY'
import json
import sys
offers = json.load(open(sys.argv[1], encoding="utf-8"))
print(", ".join(item["name"] for item in offers))
PY
}

handle_repo_move() {
  local label="$1" prompt
  if marked brave-repo-move-declined; then
    note "Keeping the Brave install from ${label} and its data directory."
    return 1
  fi
  prompt="Brave from ${label} is a separate profile, and that copy stays installed. Install the official package? Bookmarks move only at brave://settings/importData. Passwords stay in Bitwarden."
  if [[ "${GROUNDWORK_UPDATE_SCOPE:-}" == maintenance ]] || ! interactive; then
    note "Brave from ${label} is a separate profile, and that copy stays installed. To install the official package, run $(retry_command) from a terminal. Bookmarks move only at brave://settings/importData. Passwords stay in Bitwarden."
    return 1
  fi
  if confirm "$prompt"; then
    return 0
  elif [[ "$?" -eq 1 ]]; then
    mark_state brave-repo-move-declined
    note "Leaving the Brave install from ${label} in place. It is a separate profile. Bookmarks move only at brave://settings/importData. Passwords stay in Bitwarden."
  else
    note "Brave was left unchanged."
  fi
  return 1
}

write_policy() {
  local dest
  dest="$(root_path /etc/brave/policies/managed/groundwork.json)"
  if files_match "$work/policy.json" "$dest"; then
    return 0
  fi
  write_root_file "$work/policy.json" "$dest" || return 1
  did_policy=1
  note "Wrote Brave managed policies to ${dest}."
}

write_extensions() {
  local offer id src dest
  while IFS= read -r id; do
    [[ -n "$id" ]] || continue
    src="${work}/extensions/${id}.json"
    dest="$(root_path "/usr/share/chromium/extensions/${id}.json")"
    write_root_file "$src" "$dest" || return 1
  done < <(python3 -c 'import json,sys; print("\n".join(item["id"] for item in json.load(open(sys.argv[1], encoding="utf-8"))))' "$work/offers.json")
}

handle_extension() {
  local names count
  count="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1], encoding="utf-8"))))' "$work/offers.json")"
  [[ "$count" -eq 0 ]] && return 0
  if marked brave-extension-declined; then
    return 0
  fi
  names="$(offer_names)"
  if marked brave-extension-accepted; then
    write_extensions || warn "The extension offer was not written. Run $(retry_command) from a terminal to retry."
    return 0
  fi
  if [[ "${GROUNDWORK_UPDATE_SCOPE:-}" == maintenance ]] || ! interactive; then
    note "${names} is not offered in Brave yet. To offer it, run $(retry_command) from a terminal."
    return 0
  fi
  if confirm "Offer ${names} in Brave? Brave asks before it enables the extension."; then
    if [[ "$admin_ok" -eq 0 ]]; then
      if confirm "Groundwork needs administrator permission to write the extension offer. Continue?"; then
        admin_ok=1
      else
        note "The extension was not offered. Run $(retry_command) from a terminal to retry."
        return 0
      fi
    fi
    if write_extensions; then
      mark_state brave-extension-accepted
      note "Offered ${names} in Brave. Brave asks before it enables the extension."
    else
      warn "The extension offer was not written. Run $(retry_command) from a terminal to retry."
    fi
  elif [[ "$?" -eq 1 ]]; then
    mark_state brave-extension-declined
    note "The extension was not offered. Groundwork will not ask again."
  else
    note "The extension was not offered."
  fi
}

handle_default() {
  local current
  [[ "$brave_is_installed" -eq 1 ]] || return 0
  if ! command -v xdg-settings >/dev/null 2>&1; then
    note "xdg-settings is not available, so the default browser was not changed. Install xdg-utils, then run: xdg-settings set default-web-browser ${desktop_id}"
    return 0
  fi
  current="$(xdg-settings get default-web-browser 2>/dev/null || true)"
  current="${current//[[:space:]]/}"
  if [[ "$current" == "$desktop_id" ]]; then
    return 0
  fi
  if marked brave-default-declined; then
    return 0
  fi
  if [[ "${GROUNDWORK_UPDATE_SCOPE:-}" == maintenance ]] || ! interactive; then
    note "Brave is not the default browser. To make it the default, run: xdg-settings set default-web-browser ${desktop_id}"
    return 0
  fi
  if confirm "Make Brave the default browser?"; then
    if xdg-settings set default-web-browser "$desktop_id"; then
      note "Brave is now the default browser."
    else
      warn "The default browser was not changed. Run: xdg-settings set default-web-browser ${desktop_id}"
    fi
  elif [[ "$?" -eq 1 ]]; then
    mark_state brave-default-declined
    note "Keeping the current default browser. Groundwork will not ask again."
  else
    note "The default browser was not changed."
  fi
}

parse_os_release || true
family="$(distro_family)"
fedora_major="${OS_VERSION_ID%%.*}"

case "$family" in
  atomic)
    note "Fedora Atomic installs Brave with rpm-ostree and then needs a reboot. Groundwork did not change this system. Run these commands:"
    printf '%s\n' "run0 curl -fsSLo /etc/yum.repos.d/brave-browser.repo ${BRAVE_RPM_REPO_URL}"
    printf '%s\n' "rpm-ostree install brave-browser"
    exit 0
    ;;
  unknown)
    note "This Linux family has no Brave package in Groundwork. See ${BRAVE_PAGE}"
    exit 0
    ;;
esac

if [[ "$family" == fedora && ! "$fedora_major" =~ ^[0-9]+$ ]]; then
  note "Fedora's version is missing, so Brave was not installed. See ${BRAVE_PAGE}"
  exit 0
fi

brave_is_installed=0
if brave_installed; then
  brave_is_installed=1
fi

if [[ "$family" == arch && "$brave_is_installed" -eq 0 ]] && ! find_aur_helper; then
  note "Arch needs an AUR helper such as paru, pikaur, or yay to install brave-bin. Example: yay -Sy brave-bin"
  exit 0
fi

resolve_spec || exit 1
render_spec || exit 1
report_other_browsers

move_label=""
if flatpak_brave_present; then
  move_label="Flatpak"
fi
if snap_brave_present; then
  if [[ -n "$move_label" ]]; then
    move_label="Flatpak and Snap"
  else
    move_label="Snap"
  fi
fi
if [[ -n "$move_label" && "$brave_is_installed" -eq 0 ]]; then
  if ! handle_repo_move "$move_label"; then
    exit 0
  fi
elif [[ -n "$move_label" ]]; then
  note "Brave is also installed from ${move_label}. That copy is a separate profile and stays installed. Bookmarks move only at brave://settings/importData. Passwords stay in Bitwarden."
fi

scope="${GROUNDWORK_UPDATE_SCOPE:-}"
if [[ "$scope" == configuration && "$brave_is_installed" -eq 1 ]]; then
  note "Configuration-only apply: keeping the installed Brave."
  exit 0
fi

if [[ "$scope" == maintenance ]]; then
  SUDO_NONINTERACTIVE=1
fi

policy_dest="$(root_path /etc/brave/policies/managed/groundwork.json)"
need_install=0
need_policy=0
if [[ "$brave_is_installed" -eq 0 ]]; then
  need_install=1
fi
if ! files_match "$work/policy.json" "$policy_dest"; then
  need_policy=1
fi

admin_ok=0
did_policy=0
if [[ "$need_install" -eq 1 || "$need_policy" -eq 1 ]]; then
  if [[ "$scope" == maintenance ]]; then
    if ! sudo -n true; then
      if [[ "$need_install" -eq 1 ]]; then
        note "Brave was not installed because administrator permission is not available. Run $(retry_command) from a terminal. This run did not change Brave."
      else
        note "Brave policies were not written because administrator permission is not available. Run $(retry_command) from a terminal. This run did not change Brave."
      fi
      exit 0
    fi
    admin_ok=1
  elif ! interactive; then
    if [[ "$need_install" -eq 1 ]]; then
      note "Brave was not installed because this run has no terminal to ask for administrator permission. Run $(retry_command) from a terminal to retry."
    else
      note "Brave policies were not written because this run has no terminal to ask for administrator permission. Run $(retry_command) from a terminal to retry."
    fi
    exit 0
  elif confirm "Groundwork needs administrator permission to install Brave and write its managed policies. Continue?"; then
    admin_ok=1
  else
    note "Brave was left unchanged. Run $(retry_command) from a terminal when you want to install it."
    exit 0
  fi
fi

if [[ "$need_install" -eq 1 ]]; then
  if ! install_family; then
    warn "Brave wasn't installed. Nothing was recorded as done. The rest of the apply continues. Run $(retry_command) from a terminal to retry."
    exit 0
  fi
  brave_is_installed=1
  note "Installed Brave from the official package repository."
fi

if [[ "$need_policy" -eq 1 ]]; then
  write_policy || {
    warn "Brave policies were not written. Nothing was recorded as done. Run $(retry_command) from a terminal to retry."
    exit 0
  }
fi

handle_extension
handle_default

if [[ "$did_policy" -eq 0 && "$need_install" -eq 0 && "$brave_is_installed" -eq 1 ]]; then
  note "Brave is already installed and its managed policies match."
fi
