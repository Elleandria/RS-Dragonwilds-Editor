@echo off
title Dragonwilds Save Editor - Update All

cd /d "%~dp0"

echo.
echo === 1: Updating ItemID.json ===
python data\IDscan.py

echo.
echo === 2: Updating all icons (overwriting in assets\UI) ===
python assets\UpdateIcons.py

echo.
echo === Update finished (Check Icons and don't be stupid, rebuild exe!) ===
echo Icons in: assets\UI\
echo Deprecated moved to: assets\UI\old\
echo Check dep text file for missing icons or deprecation report.
pause