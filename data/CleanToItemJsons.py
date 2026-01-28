import shutil
from pathlib import Path
import argparse
import json

def clean_to_items_only(source_dir: str, target_dir: str = None, dry_run: bool = False):
    src = Path(source_dir).resolve()
    if target_dir:
        dst = Path(target_dir).resolve()
        dst.mkdir(parents=True, exist_ok=True)
    else:
        dst = src

    print(f"Scanning: {src}")
    if dst != src:
        print(f"Copying valid ITEM_*.json → {dst}")

    kept = 0
    skipped = 0

    BUILDING_KEYWORDS = {
        "roof", "wall", "floor", "foundation", "door", "window", "stair", "beam", "pillar",
        "ramp", "ceiling", "arch", "column", "railing", "balcony", "deck", "fence", "gate",
        "blueprint", "structure", "plot", "frame", "support", "tile", "panel", "trim",
        "chimney", "post", "trimming", "ledger", "joist"
    }

    for file in src.rglob("*.json"):
        if not file.name.upper().startswith("ITEM_"):
            if dry_run:
                print(f"  Skip (not ITEM_): {file.name}")
            skipped += 1
            continue

        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Normalize to list
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                data = []

            is_junk = False
            for entry in data:
                props = entry.get("Properties", {})
                name_obj = props.get("Name", {})
                name = (
                    name_obj.get("SourceString") or
                    name_obj.get("LocalizedString") or
                    props.get("DisplayName", {}).get("SourceString", "") or
                    ""
                ).lower()

                # Skip obvious building / non-inventory items
                if any(kw in name for kw in BUILDING_KEYWORDS):
                    is_junk = True
                    break

                # Require at least one inventory-related field
                has_inventory_sign = any(key in props for key in [
                    "PersistenceID", "ItemID", "PersistentID",
                    "Icon", "Weight", "MaxStackSize", "BaseDurability",
                    "PowerLevel", "VitalShield", "ItemFilterTags"
                ])

                if not has_inventory_sign:
                    is_junk = True
                    break

            if is_junk:
                if dry_run:
                    print(f"  Skip (junk/building): {file.name}")
                skipped += 1
                continue

        except Exception as e:
            if dry_run:
                print(f"  Error reading {file.name}: {e}")
            skipped += 1
            continue

        # Copy the file if it passed all checks
        if dst != src:
            target = dst / file.name
            if dry_run:
                print(f"  Would copy: {file.name}")
            else:
                shutil.copy2(file, target)
        kept += 1

    print(f"\nResult:")
    print(f"  Kept real items: {kept}")
    print(f"  Skipped junk/non-ITEM: {skipped}")
    if dry_run:
        print("Dry run complete — no files changed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy only real inventory ITEM_*.json files")
    parser.add_argument("source", help="Exported Gameplay folder path")
    parser.add_argument("--target", help="Optional: clean output folder")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    clean_to_items_only(args.source, args.target, args.dry_run)