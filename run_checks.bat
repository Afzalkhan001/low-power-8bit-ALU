@echo off
rem One-click setup check for the Low-Power 8-Bit ALU project (Windows).
rem Double-click this file. It runs every check and opens the website.
setlocal
cd /d "%~dp0"
title Low-Power 8-Bit ALU - setup check

set "PY="
python --version >nul 2>nul && set "PY=python"
if not defined PY (py -3 --version >nul 2>nul && set "PY=py -3")
if not defined PY (
  echo.
  echo Python was not found.
  echo Install it from https://www.python.org/downloads
  echo and tick "Add Python to PATH" during the install. Then run this file again.
  goto end_fail
)
for /f "delims=" %%v in ('%PY% --version') do echo Using %%v
echo.

echo [1/5] Gate-level check: 16 ops x 65,536 input pairs (about 20 seconds)...
%PY% model\alu_model.py
if errorlevel 1 goto fail
echo.

echo [2/5] Generating the Spectre netlists...
%PY% virtuoso\gen_netlist.py
if errorlevel 1 goto fail
echo.

echo [3/5] Transistor netlist check (switch level)...
%PY% virtuoso\switch_sim.py > "%TEMP%\alu8_switch.txt"
if errorlevel 1 (type "%TEMP%\alu8_switch.txt" & goto fail)
findstr /c:"SWITCH-LEVEL RESULT" "%TEMP%\alu8_switch.txt"
echo.

echo [4/5] Building the website...
%PY% simulator\build_sim.py
if errorlevel 1 goto fail
%PY% website\build_site.py
if errorlevel 1 goto fail
echo.

echo [5/5] Website engine check (needs Node.js, optional)...
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js not installed - skipped. This check is optional.
) else (
  node simulator\test_engine.js
  if errorlevel 1 goto fail
)

echo.
echo ==============================================
echo  ALL CHECKS PASSED
echo ==============================================
echo The website is website\index.html
if /i "%~1"=="--no-open" exit /b 0
start "" "website\index.html"
pause
exit /b 0

:fail
echo.
echo ==============================================
echo  A CHECK FAILED - read the message above.
echo  See the Troubleshooting table in SETUP.md
echo ==============================================
:end_fail
if /i "%~1"=="--no-open" exit /b 1
pause
exit /b 1
