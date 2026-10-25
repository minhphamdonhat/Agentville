# Shell installer pattern

Rules for `{{ SKILL_ROOT }}/assets/install.sh`, `{{ SKILL_ROOT }}/assets/install.ps1` and `{{ SKILL_ROOT }}/assets/install.cmd`, taken from the installers of Claude Code, uv, rustup, Deno and Bun. Check a project's current docs before you quote one of its details; flags and URLs change.

## The shared pattern

| Rule | How the templates do it |
| --- | --- |
| Install into a user-level folder; never `sudo`, never a system folder. | `uv tool install`, which puts the command in `uv tool dir --bin` (by default `$HOME/.local/bin`). |
| One positional argument picks a version or channel. | `stable` (default), `pre` or `1.2.3`; checked against a regular expression before use. |
| Pass the argument through the one-liner. | bash: `curl ... \| bash -s 1.2.3`; PowerShell: `& ([scriptblock]::Create((irm URL))) 1.2.3`; cmd: `install.cmd 1.2.3`. |
| An environment variable turns off every PATH and profile change. | `<ENV_PREFIX>_NO_MODIFY_PATH=1`, in the style of `UV_NO_MODIFY_PATH`. |
| `-y` answers yes; no prompt at all when `CI` is set or there is no terminal. | bash asks on `/dev/tty` because `curl \| bash` uses stdin for the script; PowerShell checks `[Console]::IsInputRedirected`. |
| Downloads are HTTPS only, TLS 1.2 or newer. | `curl --proto '=https' --tlsv1.2`, or `wget --https-only --secure-protocol=TLSv1_2`; PowerShell adds `Tls12` to `SecurityProtocol`. |
| Download to a file, then run it, never stream into a shell from inside the installer. | bash saves the uv installer with `mktemp`, runs it, then deletes it on exit; PowerShell saves it to a temporary `.ps1`, runs it with `-File`, then deletes it. |
| Pin what the installer itself fetches. | The uv installer URL holds the uv version: `https://astral.sh/uv/<UV_VERSION>/install.sh` and `.../install.ps1`, with a released version read from `git ls-remote --tags --refs https://github.com/astral-sh/uv`. |
| Keep PowerShell settings out of the user's session. | The body runs inside `& { ... }`, so `Set-StrictMode` and `$ErrorActionPreference` do not leak into it under `irm \| iex`. |
| Print the change before touching PATH, and ask unless `-y`. | `<bin> is not on PATH. uv tool update-shell will add it to your shell profile.` |
| A second run upgrades or switches version in place. | `uv tool install --upgrade <spec>`. |
| End with where it went, how to upgrade and how to uninstall. | `Uninstall: uv tool uninstall acme-tool` |
| Tell Windows and new-shell users to open a new terminal. | `Open a new terminal to pick up the new PATH.` |

## One-liners to document

```text
curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/acme/acme-tool/main/install.sh | bash
curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/acme/acme-tool/main/install.sh | bash -s 1.2.3
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/acme/acme-tool/main/install.ps1 | iex"
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/acme/acme-tool/main/install.ps1))) 1.2.3
curl --proto "=https" --tlsv1.2 -fsSL https://raw.githubusercontent.com/acme/acme-tool/main/install.cmd -o install.cmd && install.cmd && del install.cmd
```

`irm URL | iex` cannot pass an argument; the scriptblock form can. `-ExecutionPolicy ByPass` applies to that one process only, so it changes no machine policy.

## Reference installers

| Installer | One-liner shape | Folder | Version argument | PATH opt-out |
| --- | --- | --- | --- | --- |
| Claude Code | `curl -fsSL <url>/install.sh \| bash`; `irm <url>/install.ps1 \| iex`; `install.cmd` | `$HOME/.local/bin` | `bash -s 1.2.3`, `bash -s latest` | none needed |
| uv | `curl -LsSf <url>/install.sh \| sh`; `powershell -ExecutionPolicy ByPass -c "irm <url>/install.ps1 \| iex"` | `$HOME/.local/bin` | version in the URL path | `UV_NO_MODIFY_PATH` |
| rustup | `curl --proto '=https' --tlsv1.2 -sSf <url> \| sh` | `$HOME/.cargo/bin` | `-s -- --default-toolchain <v>` | `--no-modify-path` |
| Deno | `curl -fsSL <url>/install.sh \| sh` | `$HOME/.deno/bin` | `sh -s v1.2.3` | `--no-modify-path` |
| Bun | `curl -fsSL <url>/install \| bash` | `$HOME/.bun/bin` | `bash -s "bun-v1.2.3"` | profile edit is printed |

All five install per user, need no administrator rights and can run unattended with `-y` or with no terminal.

## Shipping binaries: verify before you move into place

With `distribution: binary`, the installer downloads a release asset instead of running `uv tool install`, and it must verify the asset before it is made executable. Claude Code is the model: each release publishes a manifest of SHA-256 checksums per platform, the manifest itself is signed, and the installer checks the binary against the manifest before installing it.

1. Download `SHA256SUMS` (or a JSON manifest) and its signature for the requested version.
2. Verify the signature with a public key embedded in the installer, such as with `minisign -Vm SHA256SUMS -P <public-key>`, `gpg --verify` or `cosign verify-blob`. Stop on failure.
3. Compute the asset's SHA-256 and compare it with the manifest entry for the platform. Stop on a mismatch.
4. Move the binary into the user folder only after both checks pass.

```bash
expected="$(awk -v f="$asset" '$2 == f || $2 == "*" f { print $1 }' "$tmp/SHA256SUMS")"
if command -v sha256sum >/dev/null 2>&1; then actual="$(sha256sum "$tmp/$asset" | cut -d' ' -f1)"
else actual="$(shasum -a 256 "$tmp/$asset" | cut -d' ' -f1)"; fi
[ -n "$expected" ] && [ "$expected" = "$actual" ] || die "checksum mismatch for $asset"
```

```powershell
$expected = (Select-String -Path "$tmp\SHA256SUMS" -Pattern " \*?$([regex]::Escape($asset))$").Line.Split(' ')[0]
$actual = (Get-FileHash -Algorithm SHA256 "$tmp\$asset").Hash.ToLower()
if (-not $expected -or $expected -ne $actual) { throw "checksum mismatch for $asset" }
```

Probe for `sha256sum` and fall back to `shasum -a 256`, because macOS ships only the second. A checksum from the same server as the binary only catches corruption; the signature is what catches a tampered release.

## Line endings

`raw.githubusercontent.com` serves the committed blob, and `.gitattributes` with `text` stores every text file in the blob with LF; `eol=` changes only the working tree. So a `*.cmd text eol=crlf` line does not give users a CRLF download.

* Keep `install.cmd` free of labels, `GOTO` and `CALL :label`; `cmd.exe` misreads those in an LF batch file and reads every other line safely. The template follows this rule, so pin `*.sh text eol=lf` and `*.cmd text eol=lf`.
* A batch file that needs labels must be stored with CRLF bytes: mark it `*.cmd -text` and commit it with CRLF, because only an unconverted blob reaches users as CRLF.
