@echo off
rem Puts a persistent agentville command on PATH with uv, from the Windows Command Prompt.
rem
rem   curl --proto "=https" --tlsv1.2 -fsSL https://raw.githubusercontent.com/minhphamdonhat/agentville/main/install.cmd -o install.cmd && install.cmd && del install.cmd
rem
rem It downloads install.ps1 next to your temporary files, runs it with PowerShell
rem and passes its arguments on, such as a VERSION (0.1.0) or -FromSource.
rem It installs for the current user only and never asks for administrator rights.
rem No labels or GOTO here: the file keeps LF line endings, which CMD reads safely without them.
setlocal
set "AGENTVILLE_PS1=%TEMP%\agentville-install-%RANDOM%%RANDOM%.ps1"
curl.exe --proto "=https" --tlsv1.2 -fsSL "https://raw.githubusercontent.com/minhphamdonhat/agentville/main/install.ps1" -o "%AGENTVILLE_PS1%"
if errorlevel 1 (
  echo error: could not download install.ps1 1>&2
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%AGENTVILLE_PS1%" %*
set "AGENTVILLE_EXIT=%ERRORLEVEL%"
del "%AGENTVILLE_PS1%" >nul 2>&1
exit /b %AGENTVILLE_EXIT%
