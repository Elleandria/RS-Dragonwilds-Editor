import os
import json
import re
import argparse
from pathlib import Path

# ----------------------------------------------------------------
#  Helper functions (v2 update)
# -----------------------------------------------------------------

def extract_icon_filename(icon_obj):
    if not icon_obj or "ObjectName" not in icon_obj:
        return "ICON PLACEHOLDER.png"
    match = re.search(r"Texture2D'([^']+)'", icon_obj["ObjectName"])
    if match:
        path = match.group(1)
        return f"{Path(path).name}.png"
    return "ICON PLACEHOLDER.png"


def get_category(name, default="Basic Item"):
    categories = {
        "Sword": "Melee Weapons",
        "Scimitar": "Melee Weapons",
        "Dagger": "Melee Weapons",
        "Knife": "Melee Weapons",
        "Axe": "Melee Weapons",
        "Battleaxe": "Melee Weapons",
        "Warhammer": "Melee Weapons",
        "Maul": "Melee Weapons",
        "Club": "Melee Weapons",
        "Whip": "Melee Weapons",
        "Spear": "Polearms",
        "Halberd": "Polearms",
        "Staff": "Staves",
        "Bow": "Bows",
        "Crossbow": "Crossbows",
        "Shield": "Shields",
        "Kite": "Shields",
        "Buckler": "Shields",
        "Defender": "Shields",
        "Platebody": "Chestplates",
        "Body": "Chestplates",
        "Robe": "Chestplates",
        "Tunic": "Chestplates",
        "Platelegs": "Leggings",
        "Legs": "Leggings",
        "Chaps": "Leggings",
        "Helm": "Helms",
        "Cowl": "Helms",
        "Hat": "Helms",
        "Hood": "Helms",
        "Boots": "Boots",
        "Gloves": "Gloves",
        "Ring": "Rings",
        "Amulet": "Amulets",
        "Necklace": "Amulets",
        "Pendant": "Amulets",
        "Arrow": "Arrows",
        "Bolt": "Arrows",
        "Dart": "Arrows",
        "Pickaxe": "Tools",
        "Hatchet": "Tools",
        "Ore": "Ores",
        "Bar": "Bars",
        "Logs": "Woodcutting",
        "Plank": "Woodcutting",
        "Wood": "Woodcutting",
        "Rune": "Runes",
        "Essence": "Runecrafting",
        "Seeds":"Farming",
        "Seed":"Farming",
        "Pie": "Food",
        "Stew": "Food",
        "Soup": "Food",
        "Burnt": "Food",
        "Dried": "Food",
        "Fried": "Food",
        "Crunchies": "Food",
        "Roast": "Food",
        "Mushroom": "Food",
        "Potato": "Food",
        "Onion": "Food",
        "Potion": "Potions",
        "Infusion": "Potions",
        "Herb": "Herbs",
        "Grimy": "Grimy Herbs",
        "Clean": "Herbs",
        "Skillcape": "Skillcapes",
        "Tome": "Tombs",
        "Cape": "Capes",
        "Cloak": "Capes",
        "Scarf": "Helms",
        "TEST": "TEST",
    }

    name_lower = name.lower()
    for key, cat in categories.items():
        if key.lower() in name_lower:
            return cat
    return default


def process_item_json(data):
    items = []
    if isinstance(data, list):
        for entry in data:
            items.extend(process_item_json(entry))
        return items
    if not isinstance(data, dict):
        return []
    props = data.get("Properties", {})
    if not props:
        return []

    name_obj = props.get("Name", {})
    source_string = (
        name_obj.get("SourceString") or
        name_obj.get("LocalizedString") or
        props.get("DisplayName", {}).get("SourceString", "")
    ).strip()

    pid = (
        props.get("PersistenceID") or
        props.get("ItemID") or
        props.get("PersistentID")
    )

    if not source_string or not pid:
        return []

    item = {
        "SourceString": source_string,
        "PersistenceID": pid,
        "Weight": props.get("Weight", 0.0),
        "MaxStackSize": props.get("MaxStackSize", 1),
        "VitalShield": props.get("VitalShield", 0),
        "IconFile": extract_icon_filename(props.get("Icon")),
        "Category": get_category(source_string),
    }
    if "PowerLevel" in props:
        item["PowerLevel"] = props["PowerLevel"]
    if "BaseDurability" in props and props["BaseDurability"] > 0:
        item["BaseDurability"] = props["BaseDurability"]

    return [item]


def main():
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", nargs="?",
                        default=r"C:\Users\NYPD6\Desktop\Fmodel\Output\Exports\RSDragonwilds\Content\Gameplay")
    parser.add_argument("--output", default="ItemID.json")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_path = Path(args.output)

    if not output_path.is_absolute():
        output_path = script_dir / output_path

    if not input_dir.is_dir():
        print(f"Error: Input directory not found: {input_dir}")
        return

    all_items = []
    print(f"Scanning: {input_dir}")

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.upper().endswith(".JSON") and file.upper().startswith("ITEM_"):
                path = Path(root) / file
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    extracted = process_item_json(data)
                    if extracted:
                        all_items.extend(extracted)
                        print(f"  + {len(extracted)} items from {file}")
                except Exception as e:
                    print(f"  Skip {file}: {e}")

    # Deduplicate by PID
    seen = {}
    unique_items = []
    for item in all_items:
        pid = item["PersistenceID"]
        if pid not in seen:
            seen[pid] = True
            unique_items.append(item)

    unique_items.sort(key=lambda x: x["SourceString"].lower())

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_items, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Wrote {len(unique_items)} items to:\n{output_path}")


if __name__ == "__main__":
    main()