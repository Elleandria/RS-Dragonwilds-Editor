@echo off
echo.
echo =============================================
echo   RuneScape Dragonwilds - Update Item Data
echo =============================================
echo.

echo Step 1: Make sure you have freshly exported the full Gameplay folder via FModel!
echo         Path: C:\Users\NYPD6\Desktop\Fmodel\Output\Exports\RSDragonwilds\Content\Gameplay
echo         (Export → Raw JSON → Content/Gameplay)
echo.
echo Press any key when ready...
pause >nul

echo.
echo Step 2: Cleaning - copying only valid ITEM_*.json files...
python CleanToItemJsons.py ^
  "C:\Users\NYPD6\Desktop\Fmodel\Output\Exports\RSDragonwilds\Content\Gameplay" ^
  --target "C:\Users\NYPD6\Desktop\Fmodel\Output\Exports\RSDragonwilds\Content\Gameplay-ITEMs"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR during CleanToItemJsons.py
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Step 3: Scanning UNCLEAN ITEM_ files...
python IDscan.py ^
  "C:\Users\NYPD6\Desktop\Fmodel\Output\Exports\RSDragonwilds\Content\Gameplay" ^
  --output "ItemID.json"

if %ERRORLEVEL% == 0 (
    echo.
    echo Done! ItemID.json has been updated.
    echo Only real inventory items from ITEM_* files are included.
    echo You can now start / refresh the save editor.
) else (
    echo.
    echo ERROR: IDscan.py failed (exit code %ERRORLEVEL%).
    echo Check the console output above for details.
)

echo.
pause