import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import json
import uuid
import os
import sys
from collections import OrderedDict
from PIL import Image, ImageTk

class AutocompleteCombobox(ttk.Combobox):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._completion_list = []
        self.bind('<KeyRelease>', self._on_keyrelease)

    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list, key=str.lower)
        self.configure(values=self._completion_list)

    def _on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        typed = self.get()
        if not typed:
            self.configure(values=self._completion_list)
            return
        filtered = [item for item in self._completion_list if typed.lower() in item.lower()]
        self.configure(values=filtered)

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
    return os.path.join(getattr(sys, '_MEIPASS', os.getcwd()), relative_path)

ASSETS_DIR = resource_path("assets")
UI_DIR     = os.path.join(ASSETS_DIR, "UI")
DATA_DIR   = resource_path("data")
SLOT_ICON_SIZE = 58
ICON_MAP, POWER_MAP   = {}, {}
POWER_BADGES = {}
ICON_CACHE = {}

injection_queue = []

def generate_guid():
    return uuid.uuid4().hex[:22]


def init_inventory_gui(parent):
    try:
        icons = {
            "tab": {
                "main" : ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Items_Normal.png" )) .resize((96,48))),
                "rune" : ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Runes_Normal.png" )) .resize((96,48))),
                "quest": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Quests_Normal.png")).resize((96,48)))
            },
            "tab_selected": {
                "main" : ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Items_Highlight.png" )) .resize((96,48))),
                "rune" : ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Runes_Highlight.png" )) .resize((96,48))),
                "quest": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Quests_Highlight.png")).resize((96,48)))
            },
            "loadout": [
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentHelmet.png" )) .resize((48,48))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentBody.png"   )) .resize((48,48))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentLegs.png"   )) .resize((48,48))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentCape.png"   )) .resize((48,48))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentTrinket.png")) .resize((32,32)))
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

    for t in ("main","rune","quest"):
        img = icons["tab_selected"][t] if t==current_tab else icons["tab"][t]
        lbl = tk.Label(tab_switch, image=img, bg="#1c1b18")
        lbl.pack(side=tk.LEFT, padx=10)
        lbl.bind("<Button-1>", lambda e,n=t: switch(n))
        tab_buttons[t] = lbl

    tab_start = {"main":8, "rune":32, "quest":56}
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



def refresh_inventory_icons(file_path: str, inv_frame: tk.Frame) -> None:
    if not os.path.isfile(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            save = json.load(fh)
    except Exception as exc:
        print("Save parse error:", exc)
        return

    root_inv = save.get("Inventory", {})
    inv_dict = root_inv.get("Inventory") or {k: v for k, v in root_inv.items() if k.isdigit()}
    loadout_dict = (
    save.get("Loadout") or
    root_inv.get("Loadout") or
    save.get("PersonalInventory", {}).get("Loadout", {}))

    widgets        = getattr(inv_frame, "_inventory_widgets", {})
    slot_labels    = widgets.get("slot_labels", {})
    loadout_labels = widgets.get("loadout_labels", [])

    for idx, lbl in slot_labels.items():
        lbl.configure(image="", text=str(idx))
        lbl.image = None

    ph_imgs = getattr(inv_frame, "_icon_refs", {}).get("loadout", [])
    for lbl, ph in zip(loadout_labels, ph_imgs):
        lbl.configure(image=ph)
        lbl.image = ph

    for idx_str, entry in inv_dict.items():
        if not idx_str.isdigit():
            continue
        item_id  = entry.get("ItemData")
        icon_img = get_icon_image(item_id)
        if not icon_img:
            continue

        lbl = slot_labels.get(int(idx_str))
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


    missing_report = []
    for idx_str, entry in loadout_dict.items():
        if not idx_str.isdigit():
            continue
        idx = int(idx_str)
        if idx >= len(loadout_labels):
            continue


        item_id = entry.get("ItemData")

        if not item_id and "PlayerInventoryItemIndex" in entry:
            ref     = str(entry["PlayerInventoryItemIndex"])
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

    if missing_report:
        print("Load‑out slots left on mask (no mapping):")
        for idx, iid in missing_report:
            print(f"  slot {idx}: ItemData {iid!r} not found in ItemID.txt or assets/UI/")

def _set_count_badge(parent_lbl: tk.Label, count: int | None) -> None:
    badge = getattr(parent_lbl, "_badge", None)
    if badge is None:
        badge = tk.Label(
            parent_lbl,  text="", fg="white", bg="#444",
            font=("Consolas", 10, "bold"), padx=2, pady=0
        )
        badge.place(relx=1.0, rely=1.0, anchor="se")
        parent_lbl._badge = badge

    if count is None:
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
    items, display_map, lookup = [], {}, {}
    path = os.path.join(DATA_DIR, "ItemID.txt")
    if not os.path.exists(path):
        messagebox.showerror("Missing File", f"ItemID.txt not found in {DATA_DIR}.")
        return items, display_map, lookup

    try:
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                txt = f.read() if f.closed else f""
                if not txt:
                    txt = open(path, "r", encoding="utf-8").read()
                txt = txt.strip()
                if not txt.startswith('['):
                    txt = '[' + txt.rstrip(',\n') + ']'
                data = json.loads(txt)
    except Exception as e:
        messagebox.showerror("Parse Error", f"Cannot read ItemID.txt: {e}")
        return items, display_map, lookup

    for entry in data:
        name = entry.get("SourceString", "").strip()
        if name:
            items.append(name)
            display_map[name] = name
            lookup[name] = entry
        pid  = entry.get("PersistenceID")
        icon = entry.get("IconFile")
        pwr   = entry.get("PowerLevel")
        if pid and icon:
            ICON_MAP[pid] = icon
        if pid and pwr is not None:
            POWER_MAP[pid] = pwr    
    return items, display_map, lookup


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
        img = Image.open(p).convert("RGBA").resize(
            (SLOT_ICON_SIZE, SLOT_ICON_SIZE),
            Image.LANCZOS
        )
        tk_img = ImageTk.PhotoImage(img)
        ICON_CACHE[cache_key] = tk_img
        return tk_img
    except Exception as e:
        print("could not load", icon_name, "->", e)
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
    backup_path = file_path.replace(".json", "_backup.json")
    if not os.path.exists(backup_path):
        with open(backup_path, 'w', encoding='utf-8') as backup:
            json.dump(save_data, backup, indent=4)
    inventory = save_data.get("Inventory", {})
    new_items = {}
    for entry in sorted(injection_queue, key=lambda e: e["start_slot"]):
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
    injection_queue.clear()
    update_queue_display()

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
    if item:
        if "MaxStackSize" in item:
            label_count.grid()
            entry_count.grid()
            label_durability.grid_remove()
            entry_durability.grid_remove()
            label_maxstack.config(text=f"MaxStackSize: {item['MaxStackSize']}", foreground="red")
        elif "BaseDurability" in item:
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
            label_maxstack.config(text="")
            label_durability.grid_remove()
            entry_durability.grid_remove()

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

root = tk.Tk()
root.title("RuneScape Save Editor")
root.geometry("800x400")
root.configure(bg="#1c1b18")

style = ttk.Style()
style.theme_use('clam')
style.configure("TLabel", background="#1c1b18", foreground="gold", font=("Georgia", 10, "bold"))
style.configure("TEntry", fieldbackground="#302f2c", foreground="white")
style.configure("TButton", background="#2c2b27", foreground="gold", font=("Georgia", 10, "bold"))
style.configure("TCombobox", fieldbackground="white", background="white", foreground="black")

notebook = ttk.Notebook(root)
editor_tab = tk.Frame(notebook, bg="#1c1b18")
def adjust_size(event):
    tab = event.widget.tab(event.widget.select(), "text")
    root = event.widget.winfo_toplevel()
    root.geometry("800x550" if tab == "Inventory" else "800x400")

notebook.bind("<<NotebookTabChanged>>", adjust_size)
inventory_tab = tk.Frame(notebook, bg="#1c1b18")
notebook.add(editor_tab, text="Editor")
notebook.add(inventory_tab, text="Inventory")
notebook.pack(expand=True, fill='both')

def load_json():
    default = os.path.expandvars(r"%LOCALAPPDATA%\\RSDragonwilds\\Saved\\SaveCharacters")
    initdir = default if os.path.exists(default) else os.getcwd()
    fp = filedialog.askopenfilename(initialdir=initdir, title="Select Save File", filetypes=[("JSON","*.json")])
    if not fp:
        return
    entry_file.delete(0,tk.END); entry_file.insert(0, fp)
    refresh_inventory_icons(fp, inventory_tab)

init_inventory_gui(inventory_tab)

item_list, display_lookup, item_lookup = load_item_list()
selected_item = tk.StringVar()
selected_item.set("")
selected_item.trace_add("write", update_max_stack_display)

label_file = ttk.Label(editor_tab, text="Save File:")
label_file.grid(row=0, column=0, sticky="e")
entry_file = ttk.Entry(editor_tab, width=60)
entry_file.grid(row=0, column=1, padx=5, pady=5)
ttk.Button(editor_tab, text="Browse", command=load_json).grid(row=0, column=2, padx=5, pady=5)

label_item = ttk.Label(editor_tab, text="Item:")
label_item.grid(row=1, column=0, sticky="e")
item_dropdown = AutocompleteCombobox(editor_tab, textvariable=selected_item, width=45)
item_dropdown.set_completion_list(item_list)
item_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
item_dropdown.insert(0, "Search or use Dropdown to select item")
item_dropdown.configure(foreground="gray")
item_dropdown.bind("<FocusIn>", lambda e: (item_dropdown.delete(0, tk.END), item_dropdown.configure(foreground="black")) if item_dropdown.get() == "Search or use Dropdown to select item" else None)

label_count = ttk.Label(editor_tab, text="Item Count:")
label_count.grid(row=2, column=0, sticky="e")
entry_count = ttk.Entry(editor_tab, width=10)
entry_count.insert(0, "1")
entry_count.grid(row=2, column=1, padx=5, pady=5, sticky="w")

label_durability = ttk.Label(editor_tab, text="Durability:")
label_durability.grid(row=2, column=0, sticky="e")
label_durability.grid_remove()
entry_durability = ttk.Entry(editor_tab, width=10)
entry_durability.grid(row=2, column=1, padx=5, pady=5, sticky="w")
entry_durability.grid_remove()

label_maxstack = ttk.Label(editor_tab, text="", font=("Georgia", 10, "bold"))
label_maxstack.grid(row=2, column=1, sticky="w", padx=(80, 0))

label_start = ttk.Label(editor_tab, text="Start Slot:")
label_start.grid(row=3, column=0, sticky="e")
entry_start = ttk.Entry(editor_tab, width=10)
entry_start.grid(row=3, column=1, padx=5, pady=5, sticky="w")
entry_start.insert(0, "8")

label_end = ttk.Label(editor_tab, text="End Slot:")
label_end.grid(row=4, column=0, sticky="e")
entry_end = ttk.Entry(editor_tab, width=10)
entry_end.grid(row=4, column=1, padx=5, pady=5, sticky="w")
entry_end.insert(0, "8")

try:
    icon_main = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icons_Journal_Recipes_Resources_VaultCore.png")).resize((20, 20)))
    icon_rune = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Rune_Law.png")).resize((20, 20)))
    icon_quest = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icons_Journal_Imbued_Maul_Head.png")).resize((20, 20)))

    ttk.Button(editor_tab, image=icon_main, text=" Main", compound="left", command=lambda: set_slot_range(8, 31)).grid(row=2, column=2)
    ttk.Button(editor_tab, image=icon_rune, text=" Rune", compound="left", command=lambda: set_slot_range(32, 55)).grid(row=3, column=2)
    ttk.Button(editor_tab, image=icon_quest, text=" Quest", compound="left", command=lambda: set_slot_range(56, 79)).grid(row=4, column=2)
except Exception as e:
    print("Icon loading failed:", e)

ttk.Button(editor_tab, text="Add to Queue", command=add_to_queue).grid(row=11, column=0, padx=(50, 5), pady=15, sticky="e")
ttk.Button(editor_tab, text="Inject Items", command=inject_items).grid(row=11, column=1, padx=(5, 0), pady=15, sticky="w")

queue_display = tk.Text(editor_tab, height=5, width=65, font=("Consolas", 10), background="#1c1b18", foreground="white", relief="flat", bd=0)
queue_display.grid(row=12, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")
clear_button = tk.Button(editor_tab, text="✖", command=clear_queue, font=("Arial", 10), fg="red", bg="#1c1b18", relief="flat", bd=0)
clear_button.grid(row=12, column=2, sticky="ne", padx=(0, 15), pady=(0, 10))

ToolTip(label_file, "Browse to your RuneScape save file.")
ToolTip(label_item, "Select the item to inject into the inventory.")
ToolTip(label_count, "How many of the item to inject.")
ToolTip(label_durability, "Durability value for the item. Default shown is MaxDurability.")
ToolTip(label_start,
    "Inventory slot to start injecting at:\n"
    "• 0–7   for Action Bar slots               \n"
    "• 8–31  for Main Inventory slots    \n"
    "• 32–55  for Rune Inventory slots  \n"
    "• 56–79  for Quest Inventory slots")
ToolTip(label_end,
    "Inventory slot to stop injecting at:\n"
    "• 0–7   for Action Bar slots               \n"
    "• 8–31  for Main Inventory slots    \n"
    "• 32–55  for Rune Inventory slots  \n"
    "• 56–79  for Quest Inventory slots")

bind_scroll_increment(entry_count)
bind_scroll_increment(entry_durability)
bind_scroll_increment(entry_start)
bind_scroll_increment(entry_end)

root.mainloop()
