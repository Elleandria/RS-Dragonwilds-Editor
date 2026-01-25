import os
import shutil
import json
from pathlib import Path
import argparse
from datetime import datetime

# ────────────────────────────────────────────────
#  CONFIG - adjust only if paths change
# ────────────────────────────────────────────────

FMODEL_ICONS_FOLDER = r"C:\Users\NYPD6\Desktop\Fmodel\Output\Exports\RSDragonwilds\Content\Art\UI\Icons"
ASSETS_UI_FOLDER    = r"C:\Users\NYPD6\Documents\GitHub\RS-Dragonwilds Editor\assets\UI"
ITEMID_JSON_PATH    = r"C:\Users\NYPD6\Documents\GitHub\RS-Dragonwilds Editor\data\ItemID.json"
OLD_ICONS_FOLDER    = Path(ASSETS_UI_FOLDER) / "old"
MISSING_ICONS_TXT   = Path(__file__).parent / "MissingIcons.txt"  # next to this script

# ────────────────────────────────────────────────

def copy_all_icons(skip_journal: bool = False):
    src_root = Path(FMODEL_ICONS_FOLDER)
    dst = Path(ASSETS_UI_FOLDER)

    if not src_root.is_dir():
        print(f"❌ FModel icons folder not found: {src_root}")
        return False

    dst.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    skipped_journal = 0
    skipped_building = 0
    errors = 0

    print(f"Copying icons from:\n  {src_root}\n  → {dst}\n")

    forbidden_folder_keywords = {"build", "building", "furniture"}

    for root, dirs, files in os.walk(src_root):
        current_folder = Path(root)
        folder_name_lower = current_folder.name.lower()

        if any(kw in folder_name_lower for kw in forbidden_folder_keywords):
            skipped_building += len([f for f in files if f.lower().endswith(".png")])
            print(f"  Skipped entire folder (Build/Building/Furniture): {current_folder.name}")
            continue

        for file in files:
            if not file.lower().endswith(".png"):
                continue

            name_lower = file.lower()
            src_file = Path(root) / file

            if skip_journal and "_journal_" in name_lower:
                skipped_journal += 1
                continue

            if "_building_" in name_lower or "_build_" in name_lower:
                skipped_building += 1
                continue

            target = dst / file
            try:
                if target.exists() and target.stat().st_mtime >= src_file.stat().st_mtime:
                    skipped += 1
                else:
                    shutil.copy2(src_file, target)
                    copied += 1
                    print(f"  Copied / Updated: {file}")
            except Exception as e:
                print(f"  Error copying {file}: {e}")
                errors += 1

    print(f"\nCopy finished:")
    print(f"  Copied/Updated: {copied}")
    print(f"  Skipped (already up-to-date): {skipped}")
    print(f"  Skipped (_journal_ icons): {skipped_journal}")
    print(f"  Skipped (_build_ / _building_ icons): {skipped_building}")
    print(f"  Skipped due to Build/Building/Furniture folders: included in above count")
    print(f"  Errors: {errors}")
    return True


def deprecate_unused_icons(exclude_files=None):
    if exclude_files is None:
        exclude_files = set()

    if not os.path.exists(ITEMID_JSON_PATH):
        print(f"\n⚠️  ItemID.json not found → skipping deprecation check")
        return

    try:
        with open(ITEMID_JSON_PATH, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception as e:
        print(f"Failed to read ItemID.json: {e}")
        return

    expected_icons = {item.get("IconFile", "").strip() for item in items if item.get("IconFile")}

    current_icons = {
        f.name for f in Path(ASSETS_UI_FOLDER).glob("*.png") 
        if f.is_file() and f.parent.name != "old"
    }

    deprecated = current_icons - expected_icons
    protected = deprecated & exclude_files
    deprecated -= exclude_files

    if protected:
        print(f"\nProtected (excluded from move): {len(protected)}")
        for fn in sorted(protected):
            print(f"      {fn}")

    if not deprecated:
        print("\n✓  No potentially deprecated icons found (after exclusions) — assets\\UI is clean")
        return

    OLD_ICONS_FOLDER.mkdir(exist_ok=True)

    moved = 0
    skipped = 0

    print(f"\nPotentially deprecated icons ({len(deprecated)}):")
    for fn in sorted(deprecated):
        src = Path(ASSETS_UI_FOLDER) / fn
        dst = OLD_ICONS_FOLDER / fn

        try:
            if dst.exists():
                print(f"  Skipped (already in old): {fn}")
                skipped += 1
            else:
                shutil.move(src, dst)
                print(f"  Moved to old/: {fn}")
                moved += 1
        except Exception as e:
            print(f"  Failed to move {fn}: {e}")

    print(f"\nDeprecation move finished:")
    print(f"  Moved to old/: {moved}")
    print(f"  Skipped (already in old): {skipped}")


def report_missing_icons():
    if not os.path.exists(ITEMID_JSON_PATH):
        print(f"\nCannot check missing icons — ItemID.json not found")
        return

    try:
        with open(ITEMID_JSON_PATH, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception as e:
        print(f"Failed to read ItemID.json for missing check: {e}")
        return

    current_icons = {
        f.name for f in Path(ASSETS_UI_FOLDER).glob("*.png") 
        if f.is_file() and f.parent.name != "old"
    }

    missing = []
    for item in items:
        name = item.get("SourceString", "").strip()
        icon = item.get("IconFile", "").strip()
        if icon and icon not in current_icons:
            missing.append((name, icon))

    if not missing:
        print("\n✓  No missing icons — all referenced IconFile entries are present")
        with open(MISSING_ICONS_TXT, "w", encoding="utf-8") as f:
            f.write("No missing icons found.\n")
        return

    print(f"\nMissing icons ({len(missing)}):")
    lines = []
    for name, icon in sorted(missing):
        line = f"{name} → {icon}"
        print(f"  {line}")
        lines.append(line)

    with open(MISSING_ICONS_TXT, "w", encoding="utf-8") as f:
        f.write(f"Missing icons report ({len(missing)} total) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 50 + "\n")
        f.write("\n".join(lines) + "\n")

    print(f"\nMissing icons list saved to: {MISSING_ICONS_TXT}")


def main():
    parser = argparse.ArgumentParser(description="Update icons from FModel export and move unreferenced ones to old/")
    parser.add_argument("--skip-journal", action="store_true",
                        help="Skip copying any icons containing '_journal_'")
    parser.add_argument("--skip", "--exclude", nargs="*", default=["ICON_PLACEHOLDER.png"],
                        help="Additional filenames to never move to old/")
    args = parser.parse_args()

    exclude_set = set(args.skip)

    print("=== Dragonwilds Save Editor - Icon Updater ===\n")
    success = copy_all_icons(skip_journal=args.skip_journal)
    if success:
        deprecate_unused_icons(exclude_set)
        report_missing_icons()
    print("\nFinished.")


if __name__ == "__main__":
    main()