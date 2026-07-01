@echo off
REM Speedrun dev launcher: build, seed a default MCAT deck, run against an
REM isolated base folder (your real Anki collection is never touched).
pushd "%~dp0"

set PYTHONWARNINGS=default
set PYTHONPYCACHEPREFIX=out\pycache
set ANKIDEV=1
set QTWEBENGINE_REMOTE_DEBUGGING=8080
set QTWEBENGINE_CHROMIUM_FLAGS=--remote-allow-origins=http://localhost:8080
set ANKI_API_PORT=40000
set ANKI_API_HOST=127.0.0.1
if not defined PYENV set PYENV=out\pyenv
set "SPEEDRUN_BASE=%CD%\extra\speedrun-base"

call tools\ninja pylib qt || exit /b 1
%PYENV%\Scripts\python tools\seed_mcat.py "%SPEEDRUN_BASE%" || exit /b 1
%PYENV%\Scripts\python tools\run.py -b "%SPEEDRUN_BASE%" %* || exit /b 1

popd
