# Puts a persistent `agentville` command on PATH with uv, on Windows (PowerShell 5.1 or 7).
#
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/minhphamdonhat/agentville/main/install.ps1 | iex"
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/minhphamdonhat/agentville/main/install.ps1))) 0.1.0
#
# Arguments: an optional VERSION (latest, the default, or a release such as 0.1.0),
# -FromSource to install from the GitHub repository instead of PyPI, and -Yes to
# skip the question before installing uv.
# Environment: AGENTVILLE_NO_MODIFY_PATH=1 skips `uv tool update-shell`;
# AGENTVILLE_FROM_SOURCE=1 and AGENTVILLE_YES=1 match the switches; when CI is
# set or input is redirected, nothing is asked.
#
# It installs for the current user only and never asks for administrator rights.
# The only remote script it runs is Astral's official uv installer, pinned to
# $UvVersion, when uv is missing; it is downloaded to a temporary file first,
# then run. Running it again upgrades the install.
param(
    [Parameter(Position = 0)]
    [string]$Version = 'latest',
    [switch]$FromSource,
    [switch]$Yes
)

# The body runs in its own scope: under `irm | iex` the script runs in the user's
# session, and strict mode or the error preference must not leak into it.
& {
    param([string]$Version, [bool]$FromSource, [bool]$Yes)

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    # Windows PowerShell 5.1 may default to older TLS versions.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $PythonVersion = '3.15'
    $Package = 'agentville'
    $RepoUrl = 'https://github.com/minhphamdonhat/agentville'
    $UvVersion = '0.13.5'
    $UvInstallerUrl = "https://astral.sh/uv/$UvVersion/install.ps1"

    if ($env:AGENTVILLE_FROM_SOURCE -eq '1') { $FromSource = $true }
    if ($env:AGENTVILLE_YES -eq '1') { $Yes = $true }
    $NoModifyPath = $env:AGENTVILLE_NO_MODIFY_PATH -eq '1'

    if ($Version -eq 'stable') { $Version = 'latest' }
    if ($Version -ne 'latest' -and $Version -notmatch '^\d+\.\d+\.\d+$') {
        throw "VERSION must be latest or X.Y.Z, not '$Version'"
    }

    function Invoke-Uv {
        param([string[]]$Arguments)
        Write-Host "+ uv $($Arguments -join ' ')"
        & uv @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "uv $($Arguments -join ' ') exited with $LASTEXITCODE"
        }
    }

    function Test-Interactive {
        # Ask only a person at a console: never in CI, under -Yes, or with redirected input.
        if ($Yes -or $env:CI) { return $false }
        return -not [Console]::IsInputRedirected
    }

    function Install-Uv {
        if (Get-Command uv -ErrorAction SilentlyContinue) { return }
        Write-Host 'uv is not installed. Agentville installs with uv (https://docs.astral.sh/uv/).'
        Write-Host "Running Astral's official installer for uv $UvVersion, which puts uv in your user profile (no administrator rights):"
        Write-Host "  $UvInstallerUrl"
        if (Test-Interactive) {
            $answer = Read-Host 'Install uv now? [y/N]'
            if ($answer -notmatch '^(y|yes)$') {
                # throw, not exit: under `irm | iex` an exit would close the user's PowerShell window.
                throw 'Not installing uv. Install it yourself, then run this script again.'
            }
        }
        # Download to a temporary file first, so a cut-off transfer never runs half a script.
        $installer = Join-Path ([IO.Path]::GetTempPath()) "uv-installer-$([guid]::NewGuid().ToString('N')).ps1"
        try {
            Invoke-WebRequest -Uri $UvInstallerUrl -OutFile $installer -UseBasicParsing
            if ($NoModifyPath) { $env:UV_NO_MODIFY_PATH = '1' }
            & powershell -NoProfile -ExecutionPolicy ByPass -File $installer
            if ($LASTEXITCODE -ne 0) { throw "the uv installer exited with $LASTEXITCODE" }
        } finally {
            Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
        }
        # The uv installer puts uv in %USERPROFILE%\.local\bin by default; make it visible to this session.
        $env:Path = "$(Join-Path $env:USERPROFILE '.local\bin');$env:Path"
        if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
            throw 'uv was installed but is not on PATH; open a new terminal and run this script again.'
        }
    }

    Install-Uv

    if ($FromSource) {
        $spec = if ($Version -eq 'latest') { "git+$RepoUrl" } else { "git+$RepoUrl@agentville-cli--v$Version" }
    } else {
        $spec = if ($Version -eq 'latest') { $Package } else { "$Package==$Version" }
    }

    # --force and --upgrade make a re-run replace the install with the newest match,
    # also when it switches between PyPI and the repository.
    Invoke-Uv @('tool', 'install', '--force', '--upgrade', '--python', $PythonVersion, $spec)

    if ($NoModifyPath) {
        Write-Host "Skipping PATH changes (AGENTVILLE_NO_MODIFY_PATH=1); uv's tool folder is: $(& uv tool dir --bin)"
    } else {
        Invoke-Uv @('tool', 'update-shell')
    }

    Write-Host ''
    Write-Host 'The agentville command is installed. Open a new terminal so PATH is refreshed, then run:'
    Write-Host '  agentville install                    # Claude Code, user scope, stable channel'
    Write-Host '  agentville install --scope project    # this project only'
    Write-Host '  agentville install --channel beta     # or dev'
    Write-Host 'Upgrade: run this script again, or uv tool upgrade agentville'
    Write-Host 'Uninstall: uv tool uninstall agentville'
} $Version ([bool]$FromSource) ([bool]$Yes)
