<#
.SYNOPSIS
Installs {{ PACKAGE_NAME }} for the current user with uv. No administrator rights, no system folder.

.DESCRIPTION
Target is stable (default, newest release), pre (allow pre-releases) or a version such as 1.2.3.
-Yes answers yes to every question; it is implied when CI is set or there is no interactive console.
Set {{ ENV_PREFIX }}_NO_MODIFY_PATH=1 to leave PATH alone.
Running it again upgrades or switches the version in place.

.EXAMPLE
powershell -ExecutionPolicy ByPass -c "irm {{ INSTALL_BASE_URL }}/install.ps1 | iex"

.EXAMPLE
& ([scriptblock]::Create((irm {{ INSTALL_BASE_URL }}/install.ps1))) 1.2.3
#>
param(
    [Parameter(Position = 0)]
    [string]$Target = 'stable',
    [Alias('y')]
    [switch]$Yes
)

# The body runs in its own scope: under `irm | iex` the script runs in the user's
# session, and strict mode or the error preference must not leak into it.
& {
    param([string]$Target, [bool]$Yes)

    $ErrorActionPreference = 'Stop'
    Set-StrictMode -Version Latest

    $App = '{{ PACKAGE_NAME }}'
    $UvVersion = '{{ UV_VERSION }}'
    $UvInstallerUrl = "https://astral.sh/uv/$UvVersion/install.ps1"
    $NoModifyPathVar = '{{ ENV_PREFIX }}_NO_MODIFY_PATH'

    # Windows PowerShell 5.1 may default to older TLS versions.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $AssumeYes = [bool]$Yes
    if ($env:CI -or -not [Environment]::UserInteractive -or [Console]::IsInputRedirected) { $AssumeYes = $true }

    function Confirm-Step([string]$Question) {
        if ($AssumeYes) { return $true }
        $answer = Read-Host "$Question [Y/n]"
        return ($answer -eq '' -or $answer -match '^(y|yes)$')
    }

    $UvArgs = @('tool', 'install', '--upgrade')
    if ($Target -eq 'stable') {
        $Spec = $App
    } elseif ($Target -eq 'pre') {
        $Spec = $App
        $UvArgs += '--prerelease=allow'
    } elseif ($Target -match '^[0-9]+(\.[0-9]+){1,2}((a|b|rc)[0-9]+)?$') {
        $Spec = "$App==$Target"
    } else {
        throw "unknown version or channel '$Target'; use stable, pre or a version such as 1.2.3"
    }

    # 1. uv, in the user's bin folder.
    $UvCommand = Get-Command uv -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($UvCommand) {
        $Uv = $UvCommand.Source
    } else {
        $UvDir = if ($env:UV_INSTALL_DIR) { $env:UV_INSTALL_DIR } else { Join-Path $HOME '.local\bin' }
        $Uv = Join-Path $UvDir 'uv.exe'
        if (-not (Test-Path $Uv)) {
            Write-Host "$App needs uv, which is not installed. uv $UvVersion goes to $UvDir."
            if (-not (Confirm-Step 'Install uv now?')) { throw 'cancelled; install uv (https://docs.astral.sh/uv/) and run this again' }
            # Download to a temporary file first, then run it; never stream it into a shell.
            $Installer = Join-Path ([IO.Path]::GetTempPath()) "uv-installer-$([guid]::NewGuid().ToString('N')).ps1"
            try {
                Invoke-WebRequest -Uri $UvInstallerUrl -OutFile $Installer -UseBasicParsing
                $env:UV_NO_MODIFY_PATH = '1'
                powershell -NoProfile -ExecutionPolicy ByPass -File $Installer
                if ($LASTEXITCODE -ne 0) { throw "the uv installer failed with exit code $LASTEXITCODE" }
            } finally {
                Remove-Item -LiteralPath $Installer -Force -ErrorAction SilentlyContinue
            }
            if (-not (Test-Path $Uv)) { throw "uv was not found at $Uv after its installer ran" }
        }
    }

    # 2. The tool. --upgrade makes a second run an upgrade, and a new version spec replaces the old one.
    Write-Host "Installing $Spec with uv tool install."
    & $Uv @UvArgs $Spec
    if ($LASTEXITCODE -ne 0) { throw "uv tool install failed with exit code $LASTEXITCODE" }

    # 3. PATH. Say what will change before changing it.
    $BinDir = (& $Uv tool dir --bin).Trim()
    $OnPath = ($env:Path -split ';') -contains $BinDir
    if (-not $OnPath) {
        if ([Environment]::GetEnvironmentVariable($NoModifyPathVar)) {
            Write-Host "$BinDir is not on PATH and $NoModifyPathVar is set, so PATH is left alone. Add it to your user PATH yourself."
        } else {
            Write-Host "$BinDir is not on PATH. uv tool update-shell will add it to your user PATH."
            if (Confirm-Step "Add $BinDir to PATH?") {
                & $Uv tool update-shell
                if ($LASTEXITCODE -ne 0) { throw "uv tool update-shell failed with exit code $LASTEXITCODE" }
                Write-Host 'Open a new terminal to pick up the new PATH.'
            } else {
                Write-Host "PATH unchanged. Add $BinDir to your user PATH to run $App by name."
            }
        }
    }

    $Exe = Join-Path $BinDir "$App.exe"
    $Installed = if (Test-Path $Exe) { (& $Exe --version) } else { $App }
    Write-Host ''
    Write-Host "$Installed is installed at $Exe"
    Write-Host "Upgrade: run this installer again.  Uninstall: uv tool uninstall $App"
} $Target ([bool]$Yes)
