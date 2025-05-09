import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import json
import random
import string
import os
import sys
from collections import OrderedDict
from PIL import Image, ImageTk

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ASSETS_DIR = resource_path("assets")
DATA_DIR = resource_path("data")

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

def generate_guid():
    chars = string.ascii_letters + string.digits + "-_"
    return ''.join(random.choice(chars) for _ in range(22))

def load_json():
    default_path = os.path.expandvars(r"%LOCALAPPDATA%\\RSDragonwilds\\Saved\\SaveCharacters")
    initial_dir = default_path if os.path.exists(default_path) else os.getcwd()
    file_path = filedialog.askopenfilename(
        initialdir=initial_dir,
        title="Select Save File",
        filetypes=[("JSON Files", "*.json")]
    )
    if not file_path:
        return
    entry_file.delete(0, tk.END)
    entry_file.insert(0, file_path)

def create_tooltip(widget, text):
    tooltip = tk.Toplevel(widget)
    tooltip.withdraw()
    tooltip.overrideredirect(True)
    label = tk.Label(tooltip, text=text, background="lightyellow", relief="solid", borderwidth=1, font=("Arial", 8))
    label.pack()

    def enter(event):
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 20
        tooltip.geometry(f"+{x}+{y}")
        tooltip.deiconify()

    def leave(event):
        tooltip.withdraw()

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)

def load_item_list():
    items = []
    display_map = {}
    item_map = {}
    item_file_path = os.path.join(DATA_DIR, "ItemID.txt")
    try:
        with open(item_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                name = item.get("SourceString", "").strip()
                if name:
                    items.append(name)
                    display_map[name] = name
                    item_map[name] = item
    except FileNotFoundError:
        messagebox.showerror("Missing File", f"ItemID.txt not found in {DATA_DIR}.")
    return items, display_map, item_map

def inject_items():
    file_path = entry_file.get()
    selected = selected_item.get().strip()
    item_data = item_lookup.get(selected)

    if not item_data:
        messagebox.showerror("Error", "Invalid item selection or missing entry.")
        return

    try:
        count = int(entry_count.get()) if entry_count.winfo_ismapped() else 1
        durability = int(entry_durability.get()) if entry_durability.winfo_ismapped() else item_data.get("BaseDurability", 1)
        start_slot = int(entry_start.get())
        end_slot = int(entry_end.get())
    except ValueError:
        messagebox.showerror("Error", "Durability/Count/Slot inputs must be valid numbers!")
        return

    if not os.path.isfile(file_path):
        messagebox.showerror("Error", "File not found!")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        save_data = json.load(f)

    backup_path = file_path.replace(".json", "_backup.json")
    if not os.path.exists(backup_path):
        with open(backup_path, 'w', encoding='utf-8') as backup:
            json.dump(save_data, backup, indent=4)

    inventory = save_data.get("Inventory", {})
    conflicted_slots = [str(slot) for slot in range(start_slot, end_slot + 1) if str(slot) in inventory]
    if conflicted_slots:
        proceed = messagebox.askyesno("Confirm Overwrite", f"Slots occupied: {', '.join(conflicted_slots)}. Overwrite?")
        if not proceed:
            return
        for slot in conflicted_slots:
            del inventory[slot]

    new_items = {}
    for slot in range(start_slot, end_slot + 1):
        guid = generate_guid()
        item_entry = {
            "GUID": guid,
            "ItemData": item_data["PersistenceID"]
        }
        if "MaxStackSize" in item_data:
            item_entry["Count"] = count
        if "BaseDurability" in item_data:
            item_entry["Durability"] = durability
        if "VitalShield" in item_data:
            item_entry["VitalShield"] = item_data["VitalShield"]
        new_items[str(slot)] = item_entry

    merged_inventory = OrderedDict()
    for k in sorted(new_items.keys(), key=lambda x: int(x)):
        merged_inventory[k] = new_items[k]
    for k in sorted(inventory.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):
        if k not in new_items and k != "MaxSlotIndex":
            merged_inventory[k] = inventory[k]
    merged_inventory["MaxSlotIndex"] = max(inventory.get("MaxSlotIndex", 0), end_slot)
    save_data["Inventory"] = merged_inventory

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=4)

    messagebox.showinfo("Success", f"Injected {end_slot - start_slot + 1} items.")

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

root = tk.Tk()
root.title("RuneScape Save Editor")
root.geometry("650x250")
root.configure(bg="#1c1b18")

style = ttk.Style()
style.theme_use('clam')
style.configure("TLabel", background="#1c1b18", foreground="gold", font=("Georgia", 10, "bold"))
style.configure("TEntry", fieldbackground="#302f2c", foreground="white")
style.configure("TButton", background="#2c2b27", foreground="gold", font=("Georgia", 10, "bold"))
style.configure("TCombobox", fieldbackground="white", background="white", foreground="black")

item_list, display_lookup, item_lookup = load_item_list()
selected_item = tk.StringVar()
selected_item.set("")
selected_item.trace_add("write", update_max_stack_display)

ttk.Label(root, text="Save File:").grid(row=0, column=0, sticky="e")
entry_file = ttk.Entry(root, width=60)
entry_file.grid(row=0, column=1, padx=5, pady=5)
ttk.Button(root, text="Browse", command=load_json).grid(row=0, column=2, padx=5, pady=5)

ttk.Label(root, text="Item:").grid(row=1, column=0, sticky="e")
item_dropdown = AutocompleteCombobox(root, textvariable=selected_item, width=45)
item_dropdown.insert(0, "Search or use Dropdown to select item")
item_dropdown.configure(foreground="gray")

item_dropdown.bind("<FocusIn>", lambda e: (item_dropdown.delete(0, tk.END), item_dropdown.configure(foreground="black")) if item_dropdown.get() == "Search or use Dropdown to select item" else None)
item_dropdown.set_completion_list(item_list)
item_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")

label_count = ttk.Label(root, text="Item Count:")
label_count.grid(row=2, column=0, sticky="e")
entry_count = ttk.Entry(root, width=10)
entry_count.insert(0, "1")
entry_count.grid(row=2, column=1, padx=5, pady=5, sticky="w")

label_durability = ttk.Label(root, text="Durability:")
label_durability.grid(row=2, column=0, sticky="e")
label_durability.grid_remove()
entry_durability = ttk.Entry(root, width=10)
entry_durability.grid(row=2, column=1, padx=5, pady=5, sticky="w")
entry_durability.grid_remove()

label_maxstack = ttk.Label(root, text="", font=("Georgia", 10, "bold"))
label_maxstack.grid(row=2, column=1, sticky="w", padx=(80, 0))

ttk.Label(root, text="Start Slot:").grid(row=3, column=0, sticky="e")
entry_start = ttk.Entry(root, width=10)
entry_start.insert(0, "8")
entry_start.grid(row=3, column=1, padx=5, pady=5, sticky="w")

ttk.Label(root, text="End Slot:").grid(row=4, column=0, sticky="e")
entry_end = ttk.Entry(root, width=10)
entry_end.insert(0, "8")
entry_end.grid(row=4, column=1, padx=5, pady=5, sticky="w")

try:
    icon_main = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icons_Journal_Recipes_Resources_VaultCore.png")).resize((20, 20)))
    icon_rune = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Rune_Law.png")).resize((20, 20)))
    icon_quest = ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icons_Journal_Imbued_Maul_Head.png")).resize((20, 20)))

    ttk.Button(root, image=icon_main, text=" Main", compound="left", command=lambda: set_slot_range(8, 31)).grid(row=2, column=2)
    ttk.Button(root, image=icon_rune, text=" Rune", compound="left", command=lambda: set_slot_range(32, 55)).grid(row=3, column=2)
    ttk.Button(root, image=icon_quest, text=" Quest", compound="left", command=lambda: set_slot_range(56, 79)).grid(row=4, column=2)
except Exception as e:
    print("Icon loading failed:", e)

ttk.Button(root, text="Inject Items", command=inject_items).grid(row=11, column=0, columnspan=3, pady=15)

root.mainloop()
