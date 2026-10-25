#!/usr/bin/env bash
# Installs {{ PACKAGE_NAME }} for the current user with uv. No sudo, no system folder.
#
#   curl --proto '=https' --tlsv1.2 -fsSL {{ INSTALL_BASE_URL }}/install.sh | bash
#   curl --proto '=https' --tlsv1.2 -fsSL {{ INSTALL_BASE_URL }}/install.sh | bash -s 1.2.3
#   curl --proto '=https' --tlsv1.2 -fsSL {{ INSTALL_BASE_URL }}/install.sh | bash -s -- -y pre
#
# Argument: stable (default, newest release), pre (allow pre-releases) or a version such as 1.2.3.
# Options:  -y, --yes   answer yes to every question (implied when CI is set or there is no terminal)
# Environment:
#   {{ ENV_PREFIX }}_NO_MODIFY_PATH=1   leave PATH and shell profiles alone
# Running it again upgrades or switches the version in place.
set -euo pipefail

APP="{{ PACKAGE_NAME }}"
UV_VERSION="{{ UV_VERSION }}"
UV_INSTALLER_URL="https://astral.sh/uv/${UV_VERSION}/install.sh"
NO_MODIFY_PATH_VAR="{{ ENV_PREFIX }}_NO_MODIFY_PATH"

say() { printf '%s\n' "$*"; }
die() { printf '%s installer: error: %s\n' "$APP" "$*" >&2; exit 1; }

usage() {
  say "Usage: install.sh [-y] [stable|pre|VERSION]"
  say "Installs $APP for the current user with uv tool install."
}

assume_yes=0
target="stable"
while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes) assume_yes=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) usage >&2; exit 2 ;;
    *) target="$1" ;;
  esac
  shift
done

# No questions in CI or without a terminal: `curl | bash` gives the script stdin, so ask on /dev/tty.
if [ -n "${CI:-}" ] || ! ( : </dev/tty ) 2>/dev/null; then
  assume_yes=1
fi

uv_args=(tool install --upgrade)
case "$target" in
  stable) spec="$APP" ;;
  pre) spec="$APP"; uv_args+=(--prerelease=allow) ;;
  *)
    [[ "$target" =~ ^[0-9]+(\.[0-9]+){1,2}((a|b|rc)[0-9]+)?$ ]] \
      || die "unknown version or channel '$target'; use stable, pre or a version such as 1.2.3"
    spec="${APP}==${target}" ;;
esac

confirm() {
  [ "$assume_yes" -eq 1 ] && return 0
  local answer=""
  printf '%s [Y/n] ' "$1" >/dev/tty
  read -r answer </dev/tty || answer=""
  case "$answer" in ""|y|Y|yes|Yes|YES) return 0 ;; *) return 1 ;; esac
}

download() { # download URL FILE
  if command -v curl >/dev/null 2>&1; then
    curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location --output "$2" "$1"
  elif command -v wget >/dev/null 2>&1; then
    wget --https-only --secure-protocol=TLSv1_2 --quiet --output-document="$2" "$1"
  else
    die "curl or wget is needed"
  fi
}

if [ "$(id -u)" -eq 0 ] && [ -z "${CI:-}" ]; then
  say "Note: running as root installs $APP for the root user only; sudo is not needed."
fi

# 1. uv, in the user's bin folder.
uv_bin="$(command -v uv 2>/dev/null || true)"
if [ -z "$uv_bin" ]; then
  uv_dir="${UV_INSTALL_DIR:-${XDG_BIN_HOME:-$HOME/.local/bin}}"
  uv_bin="$uv_dir/uv"
  if [ ! -x "$uv_bin" ]; then
    say "$APP needs uv, which is not installed. uv $UV_VERSION goes to $uv_dir."
    confirm "Install uv now?" || die "cancelled; install uv (https://docs.astral.sh/uv/) and run this again"
    tmp="$(mktemp)"
    trap 'rm -f "$tmp"' EXIT
    download "$UV_INSTALLER_URL" "$tmp"
    UV_NO_MODIFY_PATH=1 sh "$tmp"
    [ -x "$uv_bin" ] || die "uv was not found at $uv_bin after its installer ran"
  fi
fi

# 2. The tool. --upgrade makes a second run an upgrade, and a new version spec replaces the old one.
say "Installing $spec with uv tool install."
"$uv_bin" "${uv_args[@]}" "$spec"

# 3. PATH. Say what will change before changing it.
bin_dir="$("$uv_bin" tool dir --bin)"
case ":$PATH:" in
  *":$bin_dir:"*) ;;
  *)
    if [ -n "${!NO_MODIFY_PATH_VAR:-}" ]; then
      say "$bin_dir is not on PATH and $NO_MODIFY_PATH_VAR is set, so PATH is left alone. Add it with:"
      say "  export PATH=\"$bin_dir:\$PATH\""
    else
      say "$bin_dir is not on PATH. uv tool update-shell will add it to your shell profile."
      if confirm "Add $bin_dir to PATH?"; then
        "$uv_bin" tool update-shell
        say "Open a new terminal to pick up the new PATH."
      else
        say "PATH unchanged. Add it with: export PATH=\"$bin_dir:\$PATH\""
      fi
    fi
    ;;
esac

installed="$("$bin_dir/$APP" --version 2>/dev/null || say "$APP")"
say ""
say "$installed is installed at $bin_dir/$APP"
say "Upgrade: run this installer again.  Uninstall: uv tool uninstall $APP"
