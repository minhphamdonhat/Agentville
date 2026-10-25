#!/usr/bin/env bash
# Puts a persistent `agentville` command on PATH with uv, on Linux and macOS.
#
#   curl --proto '=https' --tlsv1.2 -LsSf https://raw.githubusercontent.com/minhphamdonhat/Agentville/main/install.sh | bash
#   ... | bash -s 0.1.0            # one version from PyPI
#   ... | bash -s -- --from-source # the GitHub repository instead of PyPI
#
# It installs for the current user only and never uses sudo. The only remote
# script it runs is Astral's official uv installer, pinned to UV_VERSION, when
# uv is missing; it is downloaded to a temporary file first, then run.
# Running it again upgrades the install.
set -euo pipefail

PYTHON_VERSION="3.15"
PACKAGE="agentville"
REPO_URL="https://github.com/minhphamdonhat/Agentville"
UV_VERSION="0.13.5"
UV_INSTALLER_URL="https://astral.sh/uv/${UV_VERSION}/install.sh"
CURL_FLAGS=(--proto '=https' --tlsv1.2 -LsSf)

usage() {
  cat <<'USAGE'
Usage: install.sh [VERSION] [--from-source] [--yes]

  VERSION        latest (default) or a release such as 0.1.0
  --from-source  install from git+https://github.com/minhphamdonhat/Agentville instead of PyPI;
                 with VERSION, from the tag agentville-cli--vVERSION
  --yes, -y      do not ask before installing uv

Environment:
  AGENTVILLE_NO_MODIFY_PATH=1  skip `uv tool update-shell`, which adds uv's tool folder to PATH
  AGENTVILLE_FROM_SOURCE=1     same as --from-source
  AGENTVILLE_YES=1             same as --yes
  CI                           when set, nothing is asked, as when stdin is not a terminal
USAGE
}

version="latest"
from_source="${AGENTVILLE_FROM_SOURCE:-0}"
assume_yes="${AGENTVILLE_YES:-0}"
no_modify_path="${AGENTVILLE_NO_MODIFY_PATH:-0}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --from-source) from_source=1 ;;
    --yes|-y) assume_yes=1 ;;
    --help|-h) usage; exit 0 ;;
    -*) echo "error: unknown option: $1 (try --help)" >&2; exit 2 ;;
    *) version="$1" ;;
  esac
  shift
done

case "$version" in
  latest|stable) version="latest" ;;
  *)
    if ! [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo "error: VERSION must be latest or X.Y.Z, not '$version'" >&2
      exit 2
    fi
    ;;
esac

say() { printf '%s\n' "$*"; }

run() {
  say "+ $*"
  "$@"
}

interactive() {
  # Ask only a person at a terminal: never in CI, under --yes, or when stdin is a pipe (curl | bash).
  [ "$assume_yes" != "1" ] && [ -z "${CI:-}" ] && [ -t 0 ]
}

ensure_uv() {
  if command -v uv > /dev/null 2>&1; then
    return 0
  fi
  say "uv is not installed. Agentville installs with uv (https://docs.astral.sh/uv/)."
  say "Running Astral's official installer for uv ${UV_VERSION}, which puts uv in your home folder (no sudo):"
  say "  ${UV_INSTALLER_URL}"
  if interactive; then
    local answer=""
    printf 'Install uv now? [y/N] '
    read -r answer || answer=""
    case "$answer" in
      y|Y|yes|YES) ;;
      *) say "Not installing uv. Install it yourself, then run this script again."; exit 1 ;;
    esac
  fi
  if ! command -v curl > /dev/null 2>&1; then
    say "error: curl is needed to download uv." >&2
    exit 1
  fi
  # Download to a temporary file first, so a cut-off transfer never runs half a script.
  uv_installer="$(mktemp)"
  trap 'rm -f "${uv_installer:-}"' EXIT
  curl "${CURL_FLAGS[@]}" --output "$uv_installer" "$UV_INSTALLER_URL"
  if [ "$no_modify_path" = "1" ]; then
    env UV_NO_MODIFY_PATH=1 sh "$uv_installer"
  else
    sh "$uv_installer"
  fi
  # The uv installer puts uv in ~/.local/bin by default; make it visible to this shell.
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv > /dev/null 2>&1; then
    say "error: uv was installed but is not on PATH; open a new terminal and run this script again." >&2
    exit 1
  fi
}

ensure_uv

if [ "$from_source" = "1" ]; then
  if [ "$version" = "latest" ]; then
    spec="git+${REPO_URL}"
  else
    spec="git+${REPO_URL}@agentville-cli--v${version}"
  fi
elif [ "$version" = "latest" ]; then
  spec="$PACKAGE"
else
  spec="${PACKAGE}==${version}"
fi

# --force and --upgrade make a re-run replace the install with the newest match,
# also when it switches between PyPI and the repository.
run uv tool install --force --upgrade --python "$PYTHON_VERSION" "$spec"

if [ "$no_modify_path" = "1" ]; then
  say "Skipping PATH changes (AGENTVILLE_NO_MODIFY_PATH=1); uv's tool folder is: $(uv tool dir --bin)"
else
  run uv tool update-shell
fi

say ""
say "The agentville command is installed. Open a new terminal so PATH is refreshed, then run:"
say "  agentville install                    # Claude Code, user scope, stable channel"
say "  agentville install --scope project    # this project only"
say "  agentville install --channel beta     # or dev"
say "Upgrade: run this script again, or uv tool upgrade agentville"
say "Uninstall: uv tool uninstall agentville"
