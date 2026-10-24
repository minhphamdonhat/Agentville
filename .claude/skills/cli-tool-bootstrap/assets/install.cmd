@echo off
rem Installs {{ PACKAGE_NAME }} from cmd.exe for the current user by running install.ps1.
rem   curl --proto "=https" --tlsv1.2 -fsSL {{ INSTALL_BASE_URL }}/install.cmd -o install.cmd && install.cmd && del install.cmd
rem   curl --proto "=https" --tlsv1.2 -fsSL {{ INSTALL_BASE_URL }}/install.cmd -o install.cmd && install.cmd 1.2.3 && del install.cmd
rem Argument: stable (default), pre or a version such as 1.2.3.
rem No labels, GOTO or CALL :label here: the file is served with LF line endings, which CMD reads safely without them.
setlocal EnableExtensions

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=stable"

echo(%TARGET%| findstr /r /x "[0-9A-Za-z.]*" >nul
if errorlevel 1 (
  echo install.cmd: unknown version or channel "%TARGET%"; use stable, pre or a version such as 1.2.3 1>&2
  exit /b 2
)

powershell -NoProfile -ExecutionPolicy ByPass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; & ([scriptblock]::Create((irm '{{ INSTALL_BASE_URL }}/install.ps1'))) '%TARGET%'"
exit /b %ERRORLEVEL%
