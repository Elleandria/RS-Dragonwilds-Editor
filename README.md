
# Runescape:Dragonwilds Save Editor

RSD-Save Editor is a simple python script that injects items into your save file (.json) so when you log back in they are in the slots you place them in. This is only currently setup for items right now, just a fast and easy way to inject them with custom GUIDs so there isn't any issue with disappearing items later.

Currently updated for Patch 0.11 (March 31st, 2026)
**REPORT ALL ISSUES IN THE DISCORD**

https://github.com/Elleandria/RS-Dragonwilds-Editor (Will have WIP/unstable builds)
https://discord.gg/PbXZrWzEkH (Public Discord)

**PLEASE CHECK THE PUBLIC GITHUB FOR THE RAW PYTHON FILES**


## Authors

- [@Elleandria](https://www.github.com/Elleandria)

## Setup

- Extract \Gameplay and \art\UI\Icons using FModel or other datamining tool (Mapping file needed)
- Run the CleanToItemJsons.py and THEN IDscan.py inside of data\ so that ITEM_*.json are cleaned 
- Verify ItemID.json integrity for errrors before running UpdateIcons.py inside of assets\
- Verify assets\UI and assets\UI\old for correct image icons, MissingIcons.txt should have a list of the last imported SourceString <-> IconFile relations. (Missing Icons or Missing SourceStrings for Icons)
- Once all data and assets are verified you can compile the pyinstaller using the .spec in root
- Booom, profit or get errors, I don't know half the time :3


## Demo

- Upon opening the save editor select "Browse" and navigate to the character you wish to inject items into.
![Tutorial 1](https://i.imgur.com/ERggqeJ.png)

- Use the dropdown or search for the item you wish to add 
![Tutorial 2](https://i.imgur.com/FL1UbPr.png)

- Place the item count you wish each slot to have (Item counts can be large, up to 9999, but in-game you must split them to move them at all or they will dissapear or revert to 1) Denote the in-game max count for ease of use
![Tutorial 3](https://i.imgur.com/fmC0pOT.png)

- Enter the Start and End slots you want the Item + Count entered previously to be placed in; 
-Slots 0–7 are your Action Bar slots.

-Slots 8–31 are your Main Inventory slots.

-Slots 32–55 are your Rune Inventory slots.

-Slots 56–79 are your Quest Inventory slots.
![Tutorial 4](https://i.imgur.com/5dWLlLW.png)
![Tutorial 5](https://i.imgur.com/UEBQDjh.png)

- Enter any world with the character save you selected before and boom, you should now have the items in the selected slots!
![Tutorial 6](https://i.imgur.com/Q8jqnvY.png)

Happy Modding <3 :D