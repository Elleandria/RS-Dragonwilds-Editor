@echo off
echo Updating Item data...

REM 1: Export whole Gameplay folder via FModel (manual step reminder)
echo Reminder: Export Gameplay folder in FModel first!

REM 2: Clean to only ITEM_*.json
python CleanToItemJsons.py "C:\Users\NYPD6\Desktop\Fmodel\Output\Exports\RSDragonwilds\Content\Gameplay" --target "C:\Users\NYPD6\Desktop\Fmodel\Output\Exports\RSDragonwilds\Content\Gameplay-Clean"

REM 3: Scan the cleaned folder
python IDscan.py "C:\Users\NYPD6\Desktop\Fmodel\Output\Exports\RSDragonwilds\Content\Gameplay-Clean"

echo Done!
pause