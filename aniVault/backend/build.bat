@echo off
REM AniVault — build the standalone .exe
REM Run this from inside the backend/ folder.

echo Installing/checking dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building AniVault.exe (this can take a minute)...
pyinstaller anivault.spec --noconfirm

echo.
echo Done. Your executable is at: dist\AniVault.exe
echo You can move dist\AniVault.exe anywhere you like — a "data" folder
echo (database + cached images) will be created next to it on first run.
pause