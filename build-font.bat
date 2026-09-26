@echo off
rem Double-click to build the font from every image in scans\.
rem Or drag a folder of scans onto this file to use that folder instead.
rem Edit FAMILY below to rename the font.
setlocal enabledelayedexpansion

set "FAMILY=LinHand"

set "ROOT=%~dp0"
set "SCANS=%~1"
if "%SCANS%"=="" set "SCANS=%ROOT%scans"

if not exist "%ROOT%template\manifest.json" (
  echo ERROR: template\manifest.json missing. Run this first:
  echo     python "%ROOT%tools\make_template.py" --out "%ROOT%template"
  goto :done
)

set "ARGS="
set "N=0"
for %%F in ("%SCANS%\*.jpg" "%SCANS%\*.jpeg" "%SCANS%\*.png") do (
  set "ARGS=!ARGS! --sheet "%%~nF=%%~fF""
  set /a N+=1
  echo   sheet %%~nF  ^<-  %%~nxF
)

if %N%==0 (
  echo ERROR: no .jpg/.jpeg/.png found in:
  echo     %SCANS%
  echo Name each photo after its sheet id, e.g. S1.jpg, S2.jpg.
  goto :done
)

echo.
echo Building "%FAMILY%" from %N% sheet^(s^)...
echo.
python "%ROOT%tools\build_font.py" --manifest "%ROOT%template\manifest.json"!ARGS! --out "%ROOT%build\%FAMILY%.ttf" --family "%FAMILY%"

if errorlevel 1 (
  echo.
  echo ==== BUILD FAILED ====
  echo Read the FAIL line above. Fixes are in README.md, section "Knobs".
  goto :done
)

echo.
echo ==== OK ====
echo Font  : %ROOT%build\%FAMILY%.ttf
echo Proof : %ROOT%build\%FAMILY%_proof.png
echo.
echo Opening the proof image. Check every character is the right character
echo BEFORE you install the font, then right-click the .ttf to install.
start "" "%ROOT%build\%FAMILY%_proof.png"

:done
echo.
pause
