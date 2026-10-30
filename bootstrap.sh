#!/usr/bin/env bash
set -euo pipefail

ENGINE_DESKTOP_HOOK=home/run_after_33-groundwork-linux-desktop-apps.sh

usage() {
  echo "Usage: $0 [--prepare-only] [--with-git-filter-repo]"
  echo "Prepare the shared Groundwork engine, then run its Linux setup."
  echo "On a Linux desktop, setup registers an apply hook for FreeTube and Brave."
  echo "--prepare-only clones the engine and prints preview steps without applying it."
  echo "--with-git-filter-repo installs git-filter-repo for your user with pipx, never with root. It is off by default."
  echo "See docs/git-filter-repo.md."
}

ignore_engine_desktop_hook() {
  local exclude="$engine_dir/.git/info/exclude"
  mkdir -p "$(dirname "$exclude")"
  if [[ -s "$exclude" && -n "$(tail -c 1 "$exclude")" ]]; then
    printf '\n' >>"$exclude"
  fi
  if [[ ! -f "$exclude" ]] || ! grep -qxF "$ENGINE_DESKTOP_HOOK" "$exclude"; then
    printf '%s\n' "$ENGINE_DESKTOP_HOOK" >>"$exclude"
  fi
}

install_linux_desktop_apps() {
  local script_dir helper brave_helper spec_src spec_dest hook_src hook_dest lib
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  lib="${HOME}/.local/lib/groundwork-linux"
  mkdir -p "$lib"
  helper="${lib}/install-desktop-apps.sh"
  brave_helper="${lib}/install-brave.sh"
  spec_src="${script_dir}/core/browser/brave.json"
  spec_dest="${lib}/brave.json"
  if [[ ! -f "$spec_src" ]]; then
    echo "The core submodule is missing browser/brave.json. Run git submodule update --init core, then rerun this entry point." >&2
    exit 1
  fi
  cp "${script_dir}/install-desktop-apps.sh" "$helper"
  cp "${script_dir}/install-brave.sh" "$brave_helper"
  cp "$spec_src" "$spec_dest"
  chmod 755 "$helper" "$brave_helper"
  chmod 644 "$spec_dest"
  hook_src="${script_dir}/engine-hooks/run_after_33-groundwork-linux-desktop-apps.sh"
  hook_dest="${engine_dir}/${ENGINE_DESKTOP_HOOK}"
  mkdir -p "$(dirname "$hook_dest")"
  cp "$hook_src" "$hook_dest"
  chmod 755 "$hook_dest"
  ignore_engine_desktop_hook
  printf 'Registered the Linux desktop apply hook at %s\n' "$hook_dest"
}

prepare_only=0
with_git_filter_repo=0
for arg in "$@"; do
  case "$arg" in
    --prepare-only) prepare_only=1 ;;
    --with-git-filter-repo) with_git_filter_repo=1 ;;
    --help | -h) usage; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; usage >&2; exit 64 ;;
  esac
done

[[ $(uname -s) == Linux ]] || { echo "Run this entry point on Linux." >&2; exit 1; }
if command -v omarchy >/dev/null 2>&1 || [[ -d /usr/share/omarchy ]]; then
  echo "Omarchy owns this environment. Use groundwork-omarchy-mac-arm64 on Apple Silicon." >&2
  exit 1
fi

command -v git >/dev/null 2>&1 || { echo "Install Git with this OS's package manager first." >&2; exit 1; }
if [[ $prepare_only -eq 0 ]] && ! command -v chezmoi >/dev/null 2>&1; then
  echo "Install chezmoi first using https://www.chezmoi.io/install/; then rerun this entry point." >&2
  exit 1
fi

engine_dir=${GROUNDWORK_ENGINE_DIR:-$HOME/code/groundwork-mac}
engine_url=${GROUNDWORK_REPO_URL:-https://github.com/jasondockery/groundwork-mac.git}
if [[ -e $engine_dir ]]; then
  [[ $(git -C "$engine_dir" rev-parse --show-toplevel) == "$engine_dir" ]] || {
    echo "The engine path must be its own Git checkout: $engine_dir" >&2; exit 1;
  }
  [[ $(git -C "$engine_dir" remote get-url origin) == "$engine_url" ]] || {
    echo "The engine origin differs from the selected URL; inspect it before continuing." >&2; exit 1;
  }
  if ! engine_status=$(git -C "$engine_dir" status --porcelain); then
    echo "Cannot inspect the engine's Git status. Repair it before setup." >&2
    exit 1
  fi
  if [[ "$engine_status" == "?? $ENGINE_DESKTOP_HOOK" ]]; then
    ignore_engine_desktop_hook
    echo "Groundwork: ignoring the local Linux desktop engine hook so the engine checkout stays clean."
    if ! engine_status=$(git -C "$engine_dir" status --porcelain); then
      echo "Cannot inspect the engine's Git status. Repair it before setup." >&2
      exit 1
    fi
  fi
  [[ -z $engine_status ]] || {
    echo "The engine has local edits. Preserve and reconcile them before setup." >&2; exit 1;
  }
else
  mkdir -p "$(dirname "$engine_dir")"
  git clone "$engine_url" "$engine_dir"
fi

if [[ $prepare_only -eq 1 ]]; then
  printf 'Prepared engine at %s. No configuration was applied.\n' "$engine_dir"
  printf 'Read docs/migration.md, then initialize, preview, and apply that source explicitly.\n'
  exit 0
fi

# Opt-in only: a default run never installs git-filter-repo. The helper installs per
# user with no root and never runs a history rewrite. See docs/git-filter-repo.md.
if [[ $with_git_filter_repo -eq 1 ]]; then
  bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-git-filter-repo.sh"
fi

# Register the desktop hook before apply so this run and later update-all runs
# execute it. chezmoi apply is what update-all uses for declared tools.
install_linux_desktop_apps
exec chezmoi --source "$engine_dir" init --apply
