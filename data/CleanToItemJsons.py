import shutil
from pathlib import Path
import argparse

def clean_to_items_only(source_dir: str, target_dir: str = None, dry_run: bool = False):
    src = Path(source_dir).resolve()
    if target_dir:
        dst = Path(target_dir).resolve()
        dst.mkdir(parents=True, exist_ok=True)
    else:
        dst = src

    print(f"Scanning: {src}")
    if dst != src:
        print(f"Copying only ITEM_*.json → {dst}")

    kept = 0
    skipped = 0

    for file in src.rglob("*.json"):
        if file.name.upper().startswith("ITEM_"):
            if dst != src:
                target = dst / file.name
                if dry_run:
                    print(f"  Would copy: {file.name}")
                else:
                    shutil.copy2(file, target)
            kept += 1
        else:
            if dry_run:
                print(f"  Would skip: {file.name}")
            skipped += 1

    print(f"\nResult:")
    print(f"  Kept ITEM_*.json: {kept}")
    print(f"  Skipped other .json: {skipped}")
    if dry_run:
        print("Dry run complete — no files changed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Exported Gameplay folder path")
    parser.add_argument("--target", help="Optional: clean output folder (only ITEM_ files copied here)")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without copying/deleting")
    args = parser.parse_args()

    clean_to_items_only(args.source, args.target, args.dry_run)