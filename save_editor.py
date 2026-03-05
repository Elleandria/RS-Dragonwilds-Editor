import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import json
import uuid
import os
import sys
import subprocess
import threading
import webbrowser
from collections import OrderedDict
from PIL import Image, ImageTk
import time

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#ffffe0", relief="solid", borderwidth=1, font=("Georgia", 9))
        label.pack()

    def hide_tip(self, event=None):
        tw = self.tipwindow
        if tw:
            tw.destroy()
            self.tipwindow = None

def resource_path(relative_path):
    """Bundled read-only assets (packed inside the exe by PyInstaller)."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def runtime_path(relative_path):
    """Runtime read-write paths — always next to the exe on disk.
    Used for data/ItemID.json and assets/UI/ which the updater writes."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

ASSETS_DIR = resource_path("assets")   # bundled tab/chrome icons (read-only)
UI_DIR = runtime_path(os.path.join("assets", "UI"))   # updater writes icons here
DATA_DIR = runtime_path("data")                        # updater writes ItemID.json here
SLOT_ICON_SIZE = 58
ICON_MAP, POWER_MAP = {}, {}
POWER_BADGES = {}
ICON_CACHE = {}
ITEM_ICON_SIZE = 32
SELECTED_ICON_SIZE = int(ITEM_ICON_SIZE * 1.2)
PLACEHOLDER_ICON = None
PLACEHOLDER_ICON_SELECTED = None

injection_queue = []

def generate_guid():
    return uuid.uuid4().hex[:22]

def init_inventory_gui(parent):
    try:
        icons = {
            "tab": {
                "main": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Items_Normal.png")).resize((96,48))),
                "rune": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Runes_Normal.png")).resize((96,48))),
                "arrow": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_ArrowsBolts_Normal.png")).resize((96,48))),
                "quest": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Quests_Normal.png")).resize((96,48)))
            },
            "tab_selected": {
                "main": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Items_Highlight.png")).resize((96,48))),
                "rune": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Runes_Highlight.png")).resize((96,48))),
                "arrow": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_ArrowsBolts_Highlight.png")).resize((96,48))),
                "quest": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Quests_Highlight.png")).resize((96,48)))
            },
            "loadout": [
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentHelmet.png")).resize((48,48))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentBody.png")).resize((48,48))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentLegs.png")).resize((48,48))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentCape.png")).resize((48,48))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentTrinket.png")).resize((32,32)))
            ]
        }
    except Exception as e:
        print("Inventory icon loading failed:", e)
        return {}

    global POWER_BADGES
    if not POWER_BADGES:
        POWER_BADGES = {
            lvl: ImageTk.PhotoImage(
                Image.open(os.path.join(ASSETS_DIR, f"PowerLevel{lvl}.png"))
                .resize((25, 25))
            )
            for lvl in range(1, 5)
        }

    parent._icon_refs = icons
    current_tab = "main"
    slot_labels = {}

    bar = tk.Frame(parent, bg="#333"); bar.pack(pady=10)
    for i in range(8):
        lbl = tk.Label(bar, text=str(i), width=8, height=4, bg="#444", fg="white",
                       bd=2, relief="groove")
        lbl.grid(row=0, column=i, padx=4, pady=4)
        slot_labels[i] = lbl

    tab_switch = tk.Frame(parent, bg="#1c1b18"); tab_switch.pack(pady=(5,0))
    grids_wrap = tk.Frame(parent, bg="#222");      grids_wrap.pack(pady=(0,10))

    tab_frames, tab_buttons = {}, {}
    def switch(name):
        nonlocal current_tab
        if name == current_tab:
            return
        for t, b in tab_buttons.items():
            b.configure(image=icons["tab_selected"][t] if t==name else icons["tab"][t])
        tab_frames[current_tab].lower(); tab_frames[name].lift(); current_tab = name

    for t in ("main", "rune", "arrow", "quest"):
        img = icons["tab_selected"][t] if t==current_tab else icons["tab"][t]
        lbl = tk.Label(tab_switch, image=img, bg="#1c1b18")
        lbl.pack(side=tk.LEFT, padx=18)
        lbl.bind("<Button-1>", lambda e,n=t: switch(n))
        tab_buttons[t] = lbl

    tab_start = {"main":8, "rune":32, "arrow":56, "quest":80}
    for name,start in tab_start.items():
        f = tk.Frame(grids_wrap, bg="#222"); f.grid(row=0,column=0,sticky="nsew")
        tab_frames[name] = f
        for r in range(3):
            for c in range(8):
                num = start + r*8 + c
                lbl = tk.Label(f, text=str(num), width=8, height=4, bg="#444", fg="white",
                               bd=2, relief="ridge")
                lbl.grid(row=r,column=c, padx=4,pady=4)
                slot_labels[num] = lbl
        f.lower()
    tab_frames[current_tab].lift()

    load = tk.Frame(parent, bg="#222"); load.pack(pady=(10,20))

    loadout_labels = []
    for i, img in enumerate(icons["loadout"]):
        lbl = tk.Label(
            load, image=img, width=62, height=62,
            bg="#444", bd=2, relief="ridge"
        )
        lbl.grid(row=0, column=i, padx=10, pady=8)
        loadout_labels.append(lbl)

    parent._inventory_widgets = {
        "slot_labels": slot_labels,
        "loadout_labels": loadout_labels
    }
    parent._icon_refs = icons
    return slot_labels

def reset_inventory_tab(inv_frame: tk.Frame) -> None:
    widgets = getattr(inv_frame, "_inventory_widgets", {})
    slot_labels = widgets.get("slot_labels", {})
    loadout_labels = widgets.get("loadout_labels", [])

    for idx, lbl in slot_labels.items():
        lbl.configure(image="", text=str(idx), width=8, height=4)
        lbl.image = None
        for binding in lbl.bind():
            lbl.unbind(binding)
        lbl._tooltip = None
        _set_count_badge(lbl, None)
        _set_power_badge(lbl, None)
        if idx < 8:
            lbl.grid(row=0, column=idx, padx=4, pady=4)
        else:
            tab_start = {"main": 8, "rune": 32, "arrow": 56, "quest": 80}
            for tab, start in tab_start.items():
                if start <= idx < start + 24:
                    row = (idx - start) // 8
                    col = (idx - start) % 8
                    lbl.grid(row=row, column=col, padx=4, pady=4)
                    break

    ph_imgs = getattr(inv_frame, "_icon_refs", {}).get("loadout", [])
    for idx, (lbl, ph) in enumerate(zip(loadout_labels, ph_imgs)):
        lbl.configure(image=ph, width=62, height=62)
        lbl.image = ph
        for binding in lbl.bind():
            lbl.unbind(binding)
        lbl._tooltip = None
        _set_count_badge(lbl, None)
        _set_power_badge(lbl, None)
        lbl.grid(row=0, column=idx, padx=10, pady=8)

def refresh_inventory_icons(file_path: str, inv_frame: tk.Frame) -> None:
    if not os.path.isfile(file_path):
        reset_inventory_tab(inv_frame)
        return

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            save = json.load(fh)
    except Exception as exc:
        print("Save parse error:", exc)
        reset_inventory_tab(inv_frame)
        return

    root_inv = save.get("Inventory", {})
    inv_dict = root_inv.get("Inventory") or {k: v for k, v in root_inv.items() if k.isdigit()}

    loadout_dict = (
        save.get("Loadout") or
        root_inv.get("Loadout") or
        save.get("PersonalInventory", {}).get("Loadout", {})
    )

    widgets = getattr(inv_frame, "_inventory_widgets", {})
    slot_labels = widgets.get("slot_labels", {})
    loadout_labels = widgets.get("loadout_labels", [])

    _, _, item_lookup, _ = load_item_list()

    for idx, lbl in slot_labels.items():
        lbl.configure(image="", text=str(idx), width=8, height=4)
        lbl.image = None
        for binding in list(lbl.bind()):
            lbl.unbind(binding)
        lbl._tooltip = None
        _set_count_badge(lbl, None)
        _set_power_badge(lbl, None)
        if idx < 8:
            lbl.grid(row=0, column=idx, padx=4, pady=4)
        else:
            tab_start = {"main": 8, "rune": 32, "arrow": 56, "quest": 80}
            for tab, start in tab_start.items():
                if start <= idx < start + 24:
                    row = (idx - start) // 8
                    col = (idx - start) % 8
                    lbl.grid(row=row, column=col, padx=4, pady=4)
                    break

    ph_imgs = getattr(inv_frame, "_icon_refs", {}).get("loadout", [])
    for idx, (lbl, ph) in enumerate(zip(loadout_labels, ph_imgs)):
        lbl.configure(image=ph, width=62, height=62)
        lbl.image = ph
        for binding in list(lbl.bind()):
            lbl.unbind(binding)
        lbl._tooltip = None
        _set_count_badge(lbl, None)
        _set_power_badge(lbl, None)
        lbl.grid(row=0, column=idx, padx=10, pady=8)

    def get_item_name(item_id: str | None) -> str | None:
        if not item_id:
            return None
        for name, entry in item_lookup.items():
            if entry.get("PersistenceID") == item_id:
                return name
        return None

    for idx_str, entry in inv_dict.items():
        if not idx_str.isdigit():
            continue
        item_id = entry.get("ItemData")
        if not item_id:
            continue
        icon_img = get_icon_image(item_id)
        if not icon_img:
            continue
        idx = int(idx_str)
        lbl = slot_labels.get(idx)
        if not lbl:
            continue
        lbl.configure(
            image=icon_img,
            text="",
            width=SLOT_ICON_SIZE,
            height=SLOT_ICON_SIZE,
            compound="center"
        )
        lbl.image = icon_img
        _set_count_badge(lbl, entry.get("Count"))
        _set_power_badge(lbl, item_id)
        item_name = get_item_name(item_id)
        if item_name:
            lbl._tooltip = ToolTip(lbl, item_name)
            lbl.bind("<Button-1>", lambda e, name=item_name: webbrowser.open(f"https://dragonwilds.runescape.wiki/w/{name.replace(' ', '_')}"))

    missing_report = []
    for idx_str, entry in loadout_dict.items():
        if not idx_str.isdigit():
            continue
        idx = int(idx_str)
        if idx >= len(loadout_labels):
            continue

        item_id = entry.get("ItemData")
        if not item_id and "PlayerInventoryItemIndex" in entry:
            ref = str(entry["PlayerInventoryItemIndex"])
            item_id = inv_dict.get(ref, {}).get("ItemData")

        icon_img = get_icon_image(item_id)
        if not icon_img:
            missing_report.append((idx, item_id))
            continue

        lbl = loadout_labels[idx]
        lbl.configure(image=icon_img)
        lbl.image = icon_img
        _set_count_badge(lbl, entry.get("Count"))
        _set_power_badge(lbl, item_id)
        item_name = get_item_name(item_id)
        if item_name:
            lbl._tooltip = ToolTip(lbl, item_name)
            lbl.bind("<Button-1>", lambda e, name=item_name: webbrowser.open(f"https://dragonwilds.runescape.wiki/w/{name.replace(' ', '_')}"))

    if missing_report:
        print("Load-out slots left on mask (no mapping):")
        for idx, iid in missing_report:
            print(f" slot {idx}: ItemData {iid!r} not found in ItemID.json or assets/UI/")


def _set_count_badge(parent_lbl: tk.Label, count: int | None) -> None:
    badge = getattr(parent_lbl, "_badge", None)
    if badge is None:
        badge = tk.Label(
            parent_lbl, text="", fg="white", bg="#444",
            font=("Consolas", 10, "bold"), padx=2, pady=0
        )
        badge.place(relx=1.0, rely=1.0, anchor="se")
        parent_lbl._badge = badge
    if count is None or count <= 1:
        badge.config(text="")
        badge.place_forget()
    else:
        badge.config(text=str(count))
        badge.place(relx=1.0, rely=1.0, anchor="se")


def _set_power_badge(parent_lbl: tk.Label, item_id: str | None) -> None:
    badge = getattr(parent_lbl, "_pwr_badge", None)
    if badge is None:
        badge = tk.Label(parent_lbl, image="", bd=0, bg=parent_lbl["bg"], highlightthickness=0)
        badge.place(relx=0, rely=0, anchor="nw")
        parent_lbl._pwr_badge = badge

    if not item_id:
        badge.config(image="")
        badge.place_forget()
        return

    lvl = POWER_MAP.get(item_id)
    if lvl in POWER_BADGES:
        badge.config(image=POWER_BADGES[lvl])
        badge.image = POWER_BADGES[lvl]
        badge.place(relx=0, rely=0, anchor="nw")
    else:
        badge.config(image="")
        badge.place_forget()

def load_item_list():
    global ICON_MAP, POWER_MAP
    items, display_map, lookup, categorized_items = [], {}, {}, {}

    json_path = os.path.join(DATA_DIR, "ItemID.json")
    if not os.path.exists(json_path):
        messagebox.showerror(
            "Missing Item Data",
            f"ItemID.json not found in:\n{DATA_DIR}\n\n"
            "Run 'Update Game Data' from the Tools menu to generate fresh item data."
        )
        return items, display_map, lookup, categorized_items

    try:
        with open(json_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        messagebox.showerror("Parse Error", f"Cannot read ItemID.json:\n{e}")
        return items, display_map, lookup, categorized_items

    for entry in data:
        pid = entry.get("PersistenceID")
        icon = entry.get("IconFile")
        if pid and icon:
            ICON_MAP[pid] = icon
            for size in (ITEM_ICON_SIZE, SELECTED_ICON_SIZE):
                cache_key = (pid, size)
                if cache_key not in ICON_CACHE:
                    try:
                        p = os.path.join(UI_DIR, icon)
                        if not os.path.exists(p):
                            print(f"Icon file missing: {p} for ItemID {pid}")
                            continue
                        img = Image.open(p).convert("RGBA").resize(
                            (size, size),
                            Image.LANCZOS
                        )
                        tk_img = ImageTk.PhotoImage(img)
                        ICON_CACHE[cache_key] = tk_img
                    except Exception as e:
                        print(f"Failed to preload icon {icon} for ItemID {pid}: {e}")

    for entry in data:
        name = entry.get("SourceString", "").strip()
        if not name:
            continue
        category = entry.get("Category", "Miscellaneous")
        original_category = category
        category = category.lower()
        if category not in categorized_items:
            categorized_items[category] = []
        categorized_items[category].append((name, original_category))
        items.append(name)
        display_map[name] = name
        lookup[name] = entry
        pid = entry.get("PersistenceID")
        pwr = entry.get("PowerLevel")
        if pid and pwr is not None:
            POWER_MAP[pid] = pwr

    print(f"Loaded {len(categorized_items)} categories: {sorted(categorized_items.keys())}")
    return items, display_map, lookup, categorized_items

def get_icon_image(item_id: str) -> ImageTk.PhotoImage | None:
    if not item_id:
        return None

    cache_key = (item_id, SLOT_ICON_SIZE)
    if cache_key in ICON_CACHE:
        return ICON_CACHE[cache_key]

    icon_name = ICON_MAP.get(item_id)
    if not icon_name:
        return None

    try:
        p = os.path.join(UI_DIR, icon_name)
        if not os.path.exists(p):
            print(f"Icon file missing: {p} for ItemID {item_id}")
            return None
        img = Image.open(p).convert("RGBA").resize(
            (SLOT_ICON_SIZE, SLOT_ICON_SIZE),
            Image.LANCZOS
        )
        tk_img = ImageTk.PhotoImage(img)
        ICON_CACHE[cache_key] = tk_img
        return tk_img
    except Exception as e:
        print(f"Failed to load icon {icon_name} for ItemID {item_id}: {e}")
        return None

def get_box_icon_image(item_id: str, size: int = ITEM_ICON_SIZE) -> ImageTk.PhotoImage | None:
    if not item_id:
        return None

    cache_key = (item_id, size)
    if cache_key in ICON_CACHE:
        return ICON_CACHE[cache_key]

    icon_name = ICON_MAP.get(item_id)
    if not icon_name:
        print(f"No icon found for ItemID {item_id}")
        return None

    try:
        p = os.path.join(UI_DIR, icon_name)
        if not os.path.exists(p):
            print(f"Icon file missing: {p} for ItemID {item_id}")
            return None
        img = Image.open(p).convert("RGBA").resize(
            (size, size),
            Image.LANCZOS
        )
        tk_img = ImageTk.PhotoImage(img)
        ICON_CACHE[cache_key] = tk_img
        return tk_img
    except Exception as e:
        print(f"Failed to load box icon {icon_name} for ItemID {item_id}: {e}")
        return None

def inject_items():
    file_path = entry_file.get()
    if not os.path.isfile(file_path):
        messagebox.showerror("Error", "File not found!")
        return
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            save_data = json.load(f)
    except json.JSONDecodeError:
        messagebox.showerror("Error", "Invalid JSON format in save file.")
        return

    if not injection_queue:
        selected = selected_item.get().strip()
        if not selected:
            messagebox.showerror("Error", "Please select an item or add items to the queue.")
            return

        item_data = item_lookup.get(selected)
        if not item_data:
            messagebox.showerror("Error", "Invalid item selection or missing entry.")
            return

        try:
            start_slot = int(entry_start.get())
            end_slot = int(entry_end.get())
            count = int(entry_count.get()) if entry_count.winfo_ismapped() else 1
            durability = int(entry_durability.get()) if entry_durability.winfo_ismapped() else None
        except ValueError:
            messagebox.showerror("Error", "Inputs must be valid numbers!")
            return

        temp_entry = {
            "item_name": selected,
            "persistence_id": item_data["PersistenceID"],
            "count": count,
            "start_slot": start_slot,
            "end_slot": end_slot,
            "durability": durability,
            "vitalshield": item_data.get("VitalShield")
        }
        temp_queue = [temp_entry]
    else:
        temp_queue = injection_queue

    backup_path = file_path.replace(".json", "_backup.json")
    if not os.path.exists(backup_path):
        with open(backup_path, 'w', encoding='utf-8') as backup:
            json.dump(save_data, backup, indent=4)

    inventory = save_data.get("Inventory", {})
    new_items = {}
    for entry in sorted(temp_queue, key=lambda e: e["start_slot"]):
        for slot in range(entry["start_slot"], entry["end_slot"] + 1):
            guid = generate_guid()
            item_entry = {
                "GUID": guid,
                "ItemData": entry["persistence_id"]
            }
            if entry["count"]:
                item_entry["Count"] = entry["count"]
            if entry["durability"]:
                item_entry["Durability"] = entry["durability"]
            if entry["vitalshield"] is not None:
                item_entry["VitalShield"] = entry["vitalshield"]
            new_items[str(slot)] = item_entry

    merged_inventory = OrderedDict()
    all_keys = list(inventory.keys()) + list(new_items.keys())
    numeric_keys = sorted({int(k) for k in all_keys if k.isdigit()})
    for k in numeric_keys:
        k_str = str(k)
        if k_str in new_items:
            merged_inventory[k_str] = new_items[k_str]
        elif k_str in inventory:
            merged_inventory[k_str] = inventory[k_str]
    max_existing = max([int(k) for k in merged_inventory.keys() if k.isdigit()], default=0)
    merged_inventory["MaxSlotIndex"] = max(inventory.get("MaxSlotIndex", 0), max_existing)
    save_data["Inventory"] = merged_inventory

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=4)

    messagebox.showinfo("Success", f"Injected {len(new_items)} items.")
    if injection_queue:
        injection_queue.clear()
        update_queue_display()
    refresh_inventory_icons(file_path, inventory_tab)

def add_to_queue():
    selected = selected_item.get().strip()
    item_data = item_lookup.get(selected)
    if not item_data:
        messagebox.showerror("Error", "Invalid item selection or missing entry.")
        return
    try:
        start_slot = int(entry_start.get())
        end_slot = int(entry_end.get())
        count = int(entry_count.get()) if entry_count.winfo_ismapped() else 1
        durability = int(entry_durability.get()) if entry_durability.winfo_ismapped() else None
    except ValueError:
        messagebox.showerror("Error", "Inputs must be valid numbers!")
        return
    entry = {
        "item_name": selected,
        "persistence_id": item_data["PersistenceID"],
        "count": count,
        "start_slot": start_slot,
        "end_slot": end_slot,
        "durability": durability,
        "vitalshield": item_data.get("VitalShield")
    }
    injection_queue.append(entry)
    update_queue_display()

def update_queue_display():
    queue_display.configure(state='normal')
    queue_display.delete("1.0", tk.END)
    lines = []
    for i, entry in enumerate(injection_queue):
        label = f"[{entry['start_slot']}]" if entry['start_slot'] == entry['end_slot'] else f"[{entry['start_slot']}-{entry['end_slot']}]"
        label += f" {entry['item_name']}"
        if entry['count']:
            label += f" ({entry['count']})"
        lines.append(label)
    output = ""
    for i in range(0, len(lines), 2):
        left = lines[i].ljust(35)
        right = lines[i+1] if i+1 < len(lines) else ""
        output += f"{left}{right}\n"
    queue_display.insert(tk.END, output)
    queue_display.configure(state='disabled')

def clear_queue():
    injection_queue.clear()
    update_queue_display()

def update_max_stack_display(*args):
    selected = selected_item.get().strip()
    item = item_lookup.get(selected)
    if not item:
        return

    is_stackable = "MaxStackSize" in item and item["MaxStackSize"] > 1
    is_durable   = "BaseDurability" in item

    if is_stackable:
        label_count.grid()
        entry_count.grid()
        label_durability.grid_remove()
        entry_durability.grid_remove()
        label_maxstack.config(text=f"Max: {item['MaxStackSize']}", foreground="red")
    elif is_durable:
        label_count.grid_remove()
        entry_count.grid_remove()
        label_maxstack.config(text="")
        label_durability.grid()
        entry_durability.grid()
        entry_durability.delete(0, tk.END)
        entry_durability.insert(0, str(item['BaseDurability']))
    else:
        label_count.grid_remove()
        entry_count.grid_remove()
        label_durability.grid_remove()
        entry_durability.grid_remove()
        label_maxstack.config(text="×1", foreground="gray")

def set_slot_range(start, end):
    entry_start.delete(0, tk.END)
    entry_end.delete(0, tk.END)
    entry_start.insert(0, str(start))
    entry_end.insert(0, str(end))

def bind_scroll_increment(entry_widget):
    def on_scroll(event):
        try:
            val = int(entry_widget.get())
            if event.delta > 0 or event.num == 4:
                val += 1
            elif event.delta < 0 or event.num == 5:
                val = max(0, val - 1)
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, str(val))
        except ValueError:
            pass
    entry_widget.bind("<MouseWheel>", on_scroll)
    entry_widget.bind("<Button-4>", on_scroll)
    entry_widget.bind("<Button-5>", on_scroll)

def create_item_box(parent, categorized_items, item_lookup):
    box_frame = tk.Frame(parent, bg="#1c1b18")
    box_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=5)

    canvas = tk.Canvas(box_frame, bg="#1c1b18", highlightthickness=0)

    # Add scrollbar
    scrollbar = ttk.Scrollbar(box_frame, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)

    scrollable_frame = tk.Frame(canvas, bg="#1c1b18")
    window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="n")

    def update_scrollregion(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas_width = canvas.winfo_width()
        frame_width = scrollable_frame.winfo_reqwidth()
        if canvas_width > frame_width:
            x_position = (canvas_width - frame_width) // 2
        else:
            x_position = 0
        canvas.coords(window_id, x_position, 0)

    scrollable_frame.bind("<Configure>", update_scrollregion)
    canvas.bind("<Configure>", update_scrollregion)

    # Mouse wheel scrolling (cross-platform)
    def on_mouse_wheel(event):
        canvas.yview_scroll(-1 * (event.delta // 120), "units")

    canvas.bind_all("<MouseWheel>", on_mouse_wheel)
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    items_per_row = 8
    category_frames = {}
    category_visible = {cat: True for cat in categorized_items.keys()}
    selected_label = None
    item_positions = {}
    widget_pools = {}
    last_render_time = 0
    render_cooldown = 0.05
    last_visible_top = None
    initial_render_done = {cat: False for cat in categorized_items.keys()}
    current_filtered_items = {}
    last_search_text = None
    search_debounce_id = None

    def initialize_widget_pools():
        canvas.update_idletasks()
        canvas_height = max(canvas.winfo_height(), 600)
        max_visible_rows = (canvas_height + 400) // (ITEM_ICON_SIZE + 10)
        max_widgets = max_visible_rows * items_per_row
        for category in categorized_items.keys():
            widget_pools[category] = []
            items_frame = category_frames.get(category, {}).get("frame")
            if not items_frame:
                continue
            for _ in range(max_widgets):
                lbl = tk.Label(
                    items_frame,
                    bg="#1c1b18",
                    bd=0,
                    highlightthickness=0
                )
                widget_pools[category].append(lbl)

    def toggle_category(category):
        category_visible[category] = not category_visible[category]
        items_frame = category_frames[category]["frame"]
        if category_visible[category]:
            category_frames[category]["toggle_btn"].config(text=f"{category_frames[category]['display_name']} ▼")
            render_visible_items(category, force_render=True)
        else:
            category_frames[category]["toggle_btn"].config(text=f"{category_frames[category]['display_name']} ►")
            for lbl in widget_pools.get(category, []):
                lbl.grid_remove()
        update_box(search_entry.get())

    def select_item(item_name, label):
        nonlocal selected_label
        if selected_label and selected_label.winfo_exists():
            try:
                prev_item_id = item_lookup.get(selected_label.item_name, {}).get("PersistenceID")
                prev_icon = get_box_icon_image(prev_item_id, size=ITEM_ICON_SIZE) if prev_item_id else PLACEHOLDER_ICON
                selected_label.configure(
                    image=prev_icon,
                    bd=0,
                    highlightthickness=0
                )
            except tk.TclError:
                pass
        item_id = item_lookup.get(item_name, {}).get("PersistenceID")
        icon = get_box_icon_image(item_id, size=SELECTED_ICON_SIZE) if item_id else PLACEHOLDER_ICON_SELECTED
        label.configure(
            image=icon,
            bd=2,
            highlightthickness=2,
            highlightbackground="gold"
        )
        label.image = icon
        selected_label = label
        selected_item.set(item_name)

    def get_visible_range():
        top = canvas.canvasy(0)
        bottom = top + canvas.winfo_height()
        buffer = 200
        return top - buffer, bottom + buffer

    def render_visible_items(category, force_render=False):
        if not category_visible[category]:
            return
        if category not in item_positions:
            return
        items = item_positions[category]["items"]
        items_frame = category_frames[category]["frame"]
        top, bottom = get_visible_range()
        num_items = len(items)
        num_rows = (num_items + items_per_row - 1) // items_per_row
        category_height = num_rows * (ITEM_ICON_SIZE + 10)
        category_start_y = item_positions[category]["y_position"]
        category_end_y = category_start_y + category_height
        if force_render or not initial_render_done[category] or (category_end_y >= top and category_start_y <= bottom):
            for lbl in widget_pools.get(category, []):
                lbl.grid_remove()
                for binding in lbl.bind():
                    lbl.unbind(binding)
                lbl._tooltip = None
            widget_index = 0
            for idx, (item, y_position, original_category) in enumerate(items):
                item_id = item_lookup.get(item, {}).get("PersistenceID")
                icon = get_box_icon_image(item_id, size=ITEM_ICON_SIZE) if item_id else PLACEHOLDER_ICON
                if widget_index >= len(widget_pools[category]):
                    lbl = tk.Label(
                        items_frame,
                        bg="#1c1b18",
                        bd=0,
                        highlightthickness=0
                    )
                    widget_pools[category].append(lbl)
                else:
                    lbl = widget_pools[category][widget_index]
                lbl.configure(
                    image=icon,
                    text="",
                    compound="center",
                    fg="white",
                    font=("Georgia", 8)
                )
                lbl.image = icon
                lbl.item_name = item
                col = idx % items_per_row
                row = idx // items_per_row
                lbl.grid(row=row, column=col, padx=5, pady=5)
                ToolTip(lbl, item)
                lbl.bind("<Button-1>", lambda e, i=item, l=lbl: select_item(i, l))
                widget_index += 1
        initial_render_done[category] = True

    def update_box(search_text=""):
        nonlocal selected_label, last_visible_top, current_filtered_items, last_search_text, search_debounce_id
        last_visible_top = None
        if search_text:
            new_filtered_items = {}
            for category, items in categorized_items.items():
                filtered = [(item, orig_cat) for item, orig_cat in items if search_text.lower() in item.lower()]
                if filtered:
                    new_filtered_items[category] = filtered
        else:
            new_filtered_items = categorized_items.copy()
        last_search_text = search_text
        current_filtered_items = new_filtered_items
        selected_label = None
        selected_item.set("")
        for category in initial_render_done:
            initial_render_done[category] = False
        if not category_frames:
            row = 0
            for category, items in sorted(current_filtered_items.items()):
                if not items:
                    continue
                cat_frame = tk.Frame(scrollable_frame, bg="#1c1b18")
                cat_frame.grid(row=row, column=0, sticky="w", pady=2)
                display_name = items[0][1] if items else category.capitalize()
                toggle_btn = tk.Button(
                    cat_frame,
                    text=f"{display_name} ▼",
                    command=lambda c=category: toggle_category(c),
                    bg="#2c2b27",
                    fg="gold",
                    font=("Georgia", 10, "bold"),
                    relief="flat"
                )
                toggle_btn.grid(row=0, column=0, sticky="w")
                row += 1
                items_frame = tk.Frame(scrollable_frame, bg="#1c1b18")
                items_frame.grid(row=row, column=0, sticky="w", pady=2)
                category_frames[category] = {"frame": items_frame, "toggle_btn": toggle_btn, "display_name": display_name}
                y_position = row * (ITEM_ICON_SIZE + 10)
                item_positions[category] = {"items": [(item, y_position, orig_cat) for item, orig_cat in items], "y_position": y_position}
                num_rows = (len(items) + items_per_row - 1) // items_per_row
                for r in range(num_rows):
                    items_frame.grid_rowconfigure(r, minsize=ITEM_ICON_SIZE + 10)
                row += num_rows
            initialize_widget_pools()
        row = 0
        for r in range(scrollable_frame.grid_size()[1]):
            scrollable_frame.grid_rowconfigure(r, minsize=0)
        for category in sorted(categorized_items.keys()):
            if category not in category_frames:
                continue
            cat_frame = category_frames[category]["toggle_btn"].master
            items_frame = category_frames[category]["frame"]
            if category not in current_filtered_items:
                cat_frame.grid_remove()
                items_frame.grid_remove()
                continue
            scrollable_frame.grid_rowconfigure(row, minsize=20)
            cat_frame.grid(row=row, column=0, sticky="w", pady=0)
            row += 1
            items = current_filtered_items[category]
            num_rows = (len(items) + items_per_row - 1) // items_per_row
            for r in range(items_frame.grid_size()[1]):
                items_frame.grid_rowconfigure(r, minsize=0)
            for r in range(num_rows):
                items_frame.grid_rowconfigure(r, minsize=ITEM_ICON_SIZE + 10)
            if category_visible[category]:
                scrollable_frame.grid_rowconfigure(row, minsize=(ITEM_ICON_SIZE + 10) * num_rows)
                items_frame.grid(row=row, column=0, sticky="w", pady=0)
            else:
                scrollable_frame.grid_rowconfigure(row, minsize=0)
                items_frame.grid_remove()
            y_position = row * (ITEM_ICON_SIZE + 10)
            item_positions[category] = {"items": [(item, y_position, orig_cat) for item, orig_cat in items], "y_position": y_position}
            row += 1 if category_visible[category] else 0
            if category_visible[category]:
                render_visible_items(category)
        update_scrollregion()

    def on_scroll(event):
        nonlocal last_render_time, last_visible_top
        current_time = time.time()
        if current_time - last_render_time < render_cooldown:
            return
        current_top, _ = get_visible_range()
        if last_visible_top != current_top:
            last_visible_top = current_top
            last_render_time = current_time
            for category in category_frames.keys():
                render_visible_items(category)

    def debounce_search(event):
        nonlocal search_debounce_id
        if search_debounce_id:
            parent.after_cancel(search_debounce_id)
        search_debounce_id = parent.after(300, lambda: update_box(search_entry.get()))

    canvas.bind("<Motion>", on_scroll)
    canvas.bind("<MouseWheel>", lambda e: on_scroll(e))
    canvas.bind("<Button-4>", lambda e: on_scroll(e))
    canvas.bind("<Button-5>", lambda e: on_scroll(e))

    update_box()

    return update_box, debounce_search

root = tk.Tk()
root.title("RuneScape Save Editor")
root.geometry("800x600")
root.configure(bg="#1c1b18")
root.withdraw()   # hide until first-run splash (if any) is done

# ---------------------------------------------------------------------------
# First-run check: if ItemID.json or icons are missing, run updater before
# the editor loads. Shows a blocking splash window with a live log.
# ---------------------------------------------------------------------------

def first_run_check():
    json_missing = not os.path.exists(os.path.join(DATA_DIR, "ItemID.json"))
    if os.path.exists(UI_DIR):
        try:
            icons_missing = not any(f.endswith(".png") for f in os.listdir(UI_DIR))
        except Exception:
            icons_missing = True
    else:
        icons_missing = True

    if not (json_missing or icons_missing):
        return  # All good

    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    updater_path = os.path.join(base, "DragonwildsUpdater.exe")

    if not os.path.exists(updater_path):
        messagebox.showwarning(
            "First Run Setup Required",
            "This appears to be your first time running the editor.\n\n"
            "Item data and icons are missing, but DragonwildsUpdater.exe "
            "was not found next to the editor.\n\n"
            "Please ensure DragonwildsUpdater.exe is in the same folder, "
            "then use Tools \u2192 Update Game Data."
        )
        return

    # ---------------------------------------------------------------------------
    # Splash window
    # ---------------------------------------------------------------------------
    splash = tk.Toplevel(root)
    splash.title("First Run Setup")
    splash.geometry("560x340")
    splash.configure(bg="#1c1b18")
    splash.resizable(False, False)
    splash.grab_set()
    splash.attributes("-topmost", True)
    splash.focus_force()

    tk.Label(splash, text="Aligning the Arcane Runes\u2026",
             bg="#1c1b18", fg="gold", font=("Georgia", 14, "bold")).pack(pady=(18, 2))
    tk.Label(splash,
             text="Extracting item data and icons from your game files.\n"
                  "The tome shall open when the ritual is complete.",
             bg="#1c1b18", fg="#c8c8b0", font=("Georgia", 9),
             wraplength=500, justify="center").pack(pady=(0, 10))

    # Progress bar
    progress_var = tk.DoubleVar(value=0.0)
    bar_frame = tk.Frame(splash, bg="#1c1b18")
    bar_frame.pack(fill="x", padx=24, pady=(0, 4))

    style_name = "Rune.Horizontal.TProgressbar"
    bar_style = ttk.Style()
    bar_style.theme_use("clam")
    bar_style.configure(style_name,
                        troughcolor="#0e0e0c",
                        background="gold",
                        bordercolor="#1c1b18",
                        lightcolor="gold",
                        darkcolor="#b8860b",
                        thickness=18)
    progress_bar = ttk.Progressbar(bar_frame, variable=progress_var,
                                   maximum=100, length=512,
                                   style=style_name)
    progress_bar.pack(fill="x")

    # Phase label (below bar)
    phase_var = tk.StringVar(value="Preparing\u2026")
    phase_label = tk.Label(splash, textvariable=phase_var,
                           bg="#1c1b18", fg="#c8c8b0", font=("Consolas", 9))
    phase_label.pack(pady=(2, 0))

    # Log text (scrolling, compact)
    log_text = tk.Text(splash, bg="#0e0e0c", fg="#7a7a60", font=("Consolas", 8),
                       relief="flat", bd=0, state="disabled", wrap="word", height=6)
    log_text.pack(expand=True, fill="both", padx=24, pady=(6, 0))

    # FINISHED label — hidden until success
    finished_var = tk.StringVar(value="")
    finished_label = tk.Label(splash, textvariable=finished_var,
                              bg="#1c1b18", fg="#00e676", font=("Georgia", 11, "bold"))
    finished_label.pack(pady=(4, 0))

    # Error close button — hidden until failure
    close_btn = tk.Button(splash, text="Continue Anyway", state="disabled",
                          bg="#2c2b27", fg="#c8c8b0", font=("Georgia", 9),
                          relief="flat",
                          command=lambda: [splash.grab_release(), splash.destroy()])
    close_btn.pack(pady=(4, 8))
    close_btn.pack_forget()  # hidden unless we hit an error

    # --- Progress bar: pure time-based, no keywords, no Tcl calls ---
    # The updater buffers all output so we can't stream it.
    # We start a repeating after() loop BEFORE launching the process.
    # It reads time.monotonic() directly. No threads touch it.

    _start_time = [None]   # list so closure can mutate it
    _ticker_id  = [None]
    _done       = [False]

    PHASE_TIMES  = [13.0, 35.0, 52.0, 62.0]
    PHASE_LABELS = [
        "1 / 4  —  Opening & mounting game files…",
        "2 / 4  —  Extracting 800+ item assets…",
        "3 / 4  —  Copying 1,157 icons…",
        "4 / 4  —  Writing ItemID.json & finalising…",
    ]

    def _tick():
        if _done[0]:
            return
        if _start_time[0] is None:
            _ticker_id[0] = splash.after(150, _tick)
            return
        elapsed = time.monotonic() - _start_time[0]
        # find current phase
        phase = 0
        for i, t in enumerate(PHASE_TIMES):
            if elapsed >= t:
                phase = i + 1
        phase = min(phase, len(PHASE_TIMES) - 1)
        # interpolate within phase band (each = 25%)
        t_lo = PHASE_TIMES[phase - 1] if phase > 0 else 0.0
        t_hi = PHASE_TIMES[phase]
        span = t_hi - t_lo
        alpha = max(0.0, min(1.0, (elapsed - t_lo) / span)) if span > 0 else 0.0
        pct = phase * 25.0 + alpha * 24.5   # max 24.5 per band, never hits 100 early
        progress_var.set(pct)
        phase_var.set(PHASE_LABELS[phase])
        _ticker_id[0] = splash.after(150, _tick)

    def _finish_ok():
        _done[0] = True
        if _ticker_id[0]:
            splash.after_cancel(_ticker_id[0])
        progress_var.set(100.0)
        phase_var.set("Complete.")
        finished_var.set("✔  FINISHED!  The runes are aligned.")
        # Auto-close after 1.5 s — no button needed on success
        splash.after(1500, lambda: [splash.grab_release(), splash.destroy()])

    def _finish_err(msg):
        _done[0] = True
        if _ticker_id[0]:
            splash.after_cancel(_ticker_id[0])
        phase_var.set(msg)
        close_btn.configure(text="Continue Anyway", state="normal")
        close_btn.pack(pady=(4, 10))

    def append(line):
        log_text.configure(state="normal")
        log_text.insert("end", line)
        log_text.see("end")
        log_text.configure(state="disabled")

    def worker():
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            # Do NOT capture stdout — just let it go to DEVNULL.
            # Trying to read stdout causes a permanent block because the updater
            # buffers all output and then calls Windows pause() which reads the
            # raw console handle, not stdin. No piping strategy can satisfy it.
            # Instead we poll for ItemID.json on disk — once that file exists,
            # the updater has finished all real work and we kill it outright.
            proc = subprocess.Popen(
                [updater_path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            itemid_path = os.path.join(DATA_DIR, "ItemID.json")
            while proc.poll() is None:
                if os.path.exists(itemid_path):
                    # File is written — work is done. Kill the hung process.
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    break
                time.sleep(0.5)

            splash.after(0, _finish_ok)
        except Exception as e:
            splash.after(0, _finish_err, f"✘ Error: {e}")

    # Start the ticker NOW, before the thread, so it's already running
    _start_time[0] = time.monotonic()
    _tick()

    threading.Thread(target=worker, daemon=True).start()
    splash.wait_window()


first_run_check()
root.deiconify()  # show the main window now that splash is done (or skipped)

placeholder_path = os.path.join(UI_DIR, "ICON PLACEHOLDER.png")
try:
    placeholder_img = Image.open(placeholder_path).convert("RGBA").resize(
        (ITEM_ICON_SIZE, ITEM_ICON_SIZE), Image.LANCZOS
    )
    PLACEHOLDER_ICON = ImageTk.PhotoImage(placeholder_img)
    placeholder_img_selected = placeholder_img.resize((SELECTED_ICON_SIZE, SELECTED_ICON_SIZE), Image.LANCZOS)
    PLACEHOLDER_ICON_SELECTED = ImageTk.PhotoImage(placeholder_img_selected)
except Exception as e:
    placeholder_img = Image.new("RGBA", (ITEM_ICON_SIZE, ITEM_ICON_SIZE), (255, 255, 255, 0))
    PLACEHOLDER_ICON = ImageTk.PhotoImage(placeholder_img)
    placeholder_img_selected = placeholder_img.resize((SELECTED_ICON_SIZE, SELECTED_ICON_SIZE), Image.LANCZOS)
    PLACEHOLDER_ICON_SELECTED = ImageTk.PhotoImage(placeholder_img_selected)

style = ttk.Style()
style.theme_use('clam')
style.configure("TLabel", background="#1c1b18", foreground="gold", font=("Georgia", 10, "bold"))
style.configure("TEntry", fieldbackground="#302f2c", foreground="white")
style.configure("TButton", background="#2c2b27", foreground="gold", font=("Georgia", 10, "bold"))

notebook = ttk.Notebook(root)
editor_tab = tk.Frame(notebook, bg="#1c1b18")
def adjust_size(event):
    tab = event.widget.tab(event.widget.select(), "text")
    root = event.widget.winfo_toplevel()
    root.geometry("800x600" if tab == "Inventory" else "800x600")

notebook.bind("<<NotebookTabChanged>>", adjust_size)
inventory_tab = tk.Frame(notebook, bg="#1c1b18")
notebook.add(editor_tab, text="Editor")
notebook.add(inventory_tab, text="Inventory")
notebook.pack(expand=True, fill='both')

def load_json():
    entry_file.delete(0, tk.END)
    reset_inventory_tab(inventory_tab)

    default = os.path.expandvars(r"%LOCALAPPDATA%\\RSDragonwilds\\Saved\\SaveCharacters")
    initdir = default if os.path.exists(default) else os.getcwd()
    fp = filedialog.askopenfilename(initialdir=initdir, title="Select Save File", filetypes=[("JSON","*.json")])
    if not fp:
        return
    entry_file.insert(0, fp)
    refresh_inventory_icons(fp, inventory_tab)

init_inventory_gui(inventory_tab)

item_list, display_lookup, item_lookup, categorized_items = load_item_list()
selected_item = tk.StringVar()
selected_item.set("")
selected_item.trace_add("write", update_max_stack_display)

label_file = ttk.Label(editor_tab, text="Save File:")
label_file.grid(row=0, column=0, sticky="e")
entry_file = ttk.Entry(editor_tab, width=60)
entry_file.grid(row=0, column=1, padx=5, pady=5)
ttk.Button(editor_tab, text="Browse", command=load_json).grid(row=0, column=2, padx=5, pady=5)

label_item = ttk.Label(editor_tab, text="Search Items:")
label_item.grid(row=1, column=0, sticky="e")
search_entry = ttk.Entry(editor_tab, width=48)
search_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
clear_search_btn = tk.Label(editor_tab, text="✖", fg="red", bg="#302f2c", font=("Arial", 8))
clear_search_btn.grid(row=1, column=2, padx=(2, 0), sticky="w")
clear_search_btn.bind("<Button-1>", lambda e: search_entry.delete(0, tk.END))

update_box_func, debounce_search = create_item_box(editor_tab, categorized_items, item_lookup)
update_box_func()
search_entry.bind("<KeyRelease>", debounce_search)
clear_search_btn.bind("<Button-1>", lambda e: [search_entry.delete(0, tk.END), update_box_func("")])

label_count = ttk.Label(editor_tab, text="Item Count:")
label_count.grid(row=3, column=0, sticky="e")
entry_count = ttk.Entry(editor_tab, width=10)
entry_count.insert(0, "1")
entry_count.grid(row=3, column=1, padx=5, pady=5, sticky="w")

label_durability = ttk.Label(editor_tab, text="Durability:")
label_durability.grid(row=3, column=0, sticky="e")
label_durability.grid_remove()
entry_durability = ttk.Entry(editor_tab, width=10)
entry_durability.grid(row=3, column=1, padx=5, pady=5, sticky="w")
entry_durability.grid_remove()

label_maxstack = ttk.Label(editor_tab, text="", font=("Georgia", 10, "bold"))
label_maxstack.grid(row=3, column=1, sticky="w", padx=(80, 0))

label_start = ttk.Label(editor_tab, text="Start Slot:")
label_start.grid(row=4, column=0, sticky="e")
entry_start = ttk.Entry(editor_tab, width=10)
entry_start.grid(row=4, column=1, padx=5, pady=5, sticky="w")
entry_start.insert(0, "8")

label_end = ttk.Label(editor_tab, text="End Slot:")
label_end.grid(row=5, column=0, sticky="e")
entry_end = ttk.Entry(editor_tab, width=10)
entry_end.grid(row=5, column=1, padx=5, pady=5, sticky="w")
entry_end.insert(0, "8")

try:
    icon_main   = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icons_Journal_Recipes_Resources_VaultCore.png")).resize((20, 20)))
    icon_rune   = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Rune_Law.png")).resize((20, 20)))
    icon_arrow  = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Arrows_Bone.png")).resize((20, 20)))
    icon_quest  = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icons_Journal_Imbued_Maul_Head.png")).resize((20, 20)))

    ttk.Button(editor_tab, image=icon_main,  text=" Main",  compound="left", command=lambda: set_slot_range(8,  31)).grid(row=3, column=2, padx=5, pady=2, sticky="w")
    ttk.Button(editor_tab, image=icon_rune,  text=" Rune",  compound="left", command=lambda: set_slot_range(32, 55)).grid(row=4, column=2, padx=5, pady=2, sticky="w")
    ttk.Button(editor_tab, image=icon_arrow, text=" Arrow", compound="left", command=lambda: set_slot_range(56, 79)).grid(row=5, column=2, padx=5, pady=2, sticky="w")
    ttk.Button(editor_tab, image=icon_quest, text=" Quest", compound="left", command=lambda: set_slot_range(80, 103)).grid(row=6, column=2, padx=5, pady=2, sticky="w")
except Exception as e:
    print("Preset icon loading failed:", e)

ttk.Button(editor_tab, text="Add to Queue", command=add_to_queue).grid(row=12, column=0, padx=(50, 5), pady=15, sticky="e")
ttk.Button(editor_tab, text="Inject Items", command=inject_items).grid(row=12, column=1, padx=(5, 0), pady=15, sticky="w")

queue_display = tk.Text(editor_tab, height=5, width=65, font=("Consolas", 10), background="#1c1b18", foreground="white", relief="flat", bd=0)
queue_display.grid(row=13, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")
clear_button = tk.Button(editor_tab, text="✖", command=clear_queue, font=("Arial", 10), fg="red", bg="#1c1b18", relief="flat", bd=0)
clear_button.grid(row=13, column=2, sticky="ne", padx=(0, 15), pady=(0, 10))

ToolTip(label_file, "Browse to your RuneScape save file.")
ToolTip(label_item, "Search for items to inject into the inventory.")
ToolTip(label_count, "How many of the item to inject.")
ToolTip(label_durability, "Durability value for the item. Default shown is MaxDurability.")
ToolTip(label_start,
    "Inventory slot to start injecting at:\n"
    "• 0–7   for Action Bar slots               \n"
    "• 8–31  for Main Inventory slots    \n"
    "• 32–55  for Rune Inventory slots  \n"
    "• 56–79  for Arrow Inventory slots  \n"
    "• 80-103 for Quest Inventory slots")
ToolTip(label_end,
    "Inventory slot to stop injecting at:\n"
    "• 0–7   for Action Bar slots               \n"
    "• 8–31  for Main Inventory slots    \n"
    "• 32–55  for Rune Inventory slots  \n"
    "• 56–79  for Arrow Inventory slots  \n"
    "• 80-103  for Quest Inventory slots")

def bind_scroll_increment(entry_widget):
    def on_scroll(event):
        try:
            val = int(entry_widget.get())
            if event.delta > 0 or event.num == 4:
                val += 1
            elif event.delta < 0 or event.num == 5:
                val = max(0, val - 1)
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, str(val))
        except ValueError:
            pass
    entry_widget.bind("<MouseWheel>", on_scroll)
    entry_widget.bind("<Button-4>", on_scroll)
    entry_widget.bind("<Button-5>", on_scroll)

bind_scroll_increment(entry_count)
bind_scroll_increment(entry_durability)
bind_scroll_increment(entry_start)
bind_scroll_increment(entry_end)

# ---------------------------------------------------------------------------
# Tools menu — Update Game Data
# ---------------------------------------------------------------------------

def run_updater():
    """
    Locates DragonwildsUpdater.exe next to the editor, runs it in a subprocess,
    and streams its output into a live log window. Reloads item data when done.
    """
    # Resolve updater path: same folder as the editor exe / script
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    updater_path = os.path.join(base, "DragonwildsUpdater.exe")

    if not os.path.exists(updater_path):
        messagebox.showerror(
            "Updater Not Found",
            f"DragonwildsUpdater.exe not found at:\n{updater_path}\n\n"
            "Make sure DragonwildsUpdater.exe is in the same folder as the editor."
        )
        return

    # Build the log window
    log_win = tk.Toplevel(root)
    log_win.title("Updating Game Data...")
    log_win.geometry("600x400")
    log_win.configure(bg="#1c1b18")
    log_win.resizable(False, False)

    tk.Label(log_win, text="Update Game Data", bg="#1c1b18", fg="gold",
             font=("Georgia", 12, "bold")).pack(pady=(12, 4))

    log_text = tk.Text(log_win, bg="#0e0e0c", fg="#c8c8b0", font=("Consolas", 9),
                       relief="flat", bd=0, state="disabled", wrap="word")
    log_text.pack(expand=True, fill="both", padx=12, pady=(4, 0))

    close_btn = tk.Button(log_win, text="Close", state="disabled",
                          bg="#2c2b27", fg="gold", font=("Georgia", 10, "bold"),
                          relief="flat", command=log_win.destroy)
    close_btn.pack(pady=10)

    def append(line):
        log_text.configure(state="normal")
        log_text.insert("end", line)
        log_text.see("end")
        log_text.configure(state="disabled")

    def worker():
        try:
            proc = subprocess.Popen(
                [updater_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in proc.stdout:
                log_win.after(0, append, line)
            proc.wait()

            if proc.returncode == 0:
                log_win.after(0, append, "\n✔ Update complete. Reloading item data...\n")
                log_win.after(0, reload_item_data)
                log_win.after(0, lambda: log_win.title("Update Complete"))
            else:
                log_win.after(0, append, f"\n✘ Updater exited with code {proc.returncode}.\n")
                log_win.after(0, lambda: log_win.title("Update Failed"))

        except Exception as e:
            log_win.after(0, append, f"\n✘ Error running updater:\n{e}\n")
            log_win.after(0, lambda: log_win.title("Update Failed"))
        finally:
            log_win.after(0, lambda: close_btn.configure(state="normal"))

    threading.Thread(target=worker, daemon=True).start()


def reload_item_data():
    """Hot-reload ItemID.json and refresh the item box without restarting."""
    global item_list, display_lookup, item_lookup, categorized_items
    item_list, display_lookup, item_lookup, categorized_items = load_item_list()
    update_box_func()


# Menu bar
menubar = tk.Menu(root, bg="#2c2b27", fg="gold", activebackground="#444",
                  activeforeground="white", bd=0)

tools_menu = tk.Menu(menubar, tearoff=0, bg="#2c2b27", fg="gold",
                     activebackground="#444", activeforeground="white")
tools_menu.add_command(label="Update Game Data", command=run_updater)
tools_menu.add_separator()
tools_menu.add_command(
    label="View on Nexusmods",
    command=lambda: webbrowser.open("https://www.nexusmods.com/runescapedragonwilds/mods/87")
)
tools_menu.add_command(
    label="View on GitHub",
    command=lambda: webbrowser.open("https://github.com/NYPD6/RS-Dragonwilds-Editor")
)

menubar.add_cascade(label="Tools", menu=tools_menu)
root.configure(menu=menubar)

root.mainloop()