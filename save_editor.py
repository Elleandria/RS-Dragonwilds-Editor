import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import json
import random
import string
import os
from collections import OrderedDict

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
    default_path = os.path.expandvars(r"%LOCALAPPDATA%\RSDragonwilds\Saved\SaveCharacters")
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

def load_item_list():
    items = []
    item_map = {}
    vitalshield_items = set()

    try:
        with open("ItemID.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                has_shield = line.endswith("*")
                line = line.rstrip("*").strip()

                if "(" in line and ")" in line:
                    item_id = line[line.find("(")+1:line.find(")")]
                    items.append(line)
                    item_map[line] = item_id
                    if has_shield:
                        vitalshield_items.add(item_id)
    except FileNotFoundError:
        messagebox.showerror("Missing File", "ItemID.txt not found in the same folder.")
    return items, item_map, vitalshield_items


def inject_items():
    file_path = entry_file.get()
    selected = selected_item.get().strip()
    item_data = item_lookup.get(selected, "")
    if not item_data:
        if len(selected) >= 20:
            item_data = selected
        else:
            messagebox.showerror("Error", "Invalid ItemData entry.")
            return
    try:
        count = int(entry_count.get())
        start_slot = int(entry_start.get())
        end_slot = int(entry_end.get())
    except ValueError:
        messagebox.showerror("Error", "Count, Start, and End must be numbers!")
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

    if "Inventory" not in save_data:
        messagebox.showerror("Error", "No 'Inventory' section found in save file!")
        return

    inventory = save_data["Inventory"]
    new_items = {}
    for slot in range(start_slot, end_slot + 1):
        guid = generate_guid()
        item_entry = {
            "GUID": guid,
            "ItemData": item_data,
            "Count": count
        }
        if item_data in vitalshield_set:
            item_entry["VitalShield"] = 0
        new_items[str(slot)] = item_entry

    max_slot_index = inventory.get("MaxSlotIndex", 0)
    if "MaxSlotIndex" in inventory:
        del inventory["MaxSlotIndex"]

    merged_inventory = OrderedDict()
    for k in sorted(new_items.keys(), key=lambda x: int(x)):
        merged_inventory[k] = new_items[k]
    for k in sorted(inventory.keys(), key=lambda x: int(x)):
        merged_inventory[k] = inventory[k]

    merged_inventory["MaxSlotIndex"] = max(max_slot_index, end_slot)
    save_data["Inventory"] = merged_inventory

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=4)

    messagebox.showinfo("Success", f"Injected {end_slot - start_slot + 1} items into inventory at correct position!")

root = tk.Tk()
root.title("RuneScape Save Editor")
root.geometry("700x350")
root.configure(bg="#1c1b18")

style = ttk.Style()
style.theme_use('clam')
style.configure("TLabel", background="#1c1b18", foreground="gold", font=("Georgia", 10, "bold"))
style.configure("TEntry", fieldbackground="#302f2c", foreground="white")
style.configure("TButton", background="#2c2b27", foreground="gold", font=("Georgia", 10, "bold"))
style.configure("TCombobox", fieldbackground="white", background="white", foreground="black")

item_list, item_lookup, vitalshield_set = load_item_list()
selected_item = tk.StringVar()
selected_item.set(item_list[0] if item_list else "")

ttk.Label(root, text="Save File:").grid(row=0, column=0, sticky="e")
entry_file = ttk.Entry(root, width=60)
entry_file.grid(row=0, column=1, padx=5, pady=5)
ttk.Button(root, text="Browse", command=load_json).grid(row=0, column=2, padx=5, pady=5)

ttk.Label(root, text="Item:").grid(row=1, column=0, sticky="e")
item_dropdown = AutocompleteCombobox(root, textvariable=selected_item, width=45)
item_dropdown.set_completion_list(item_list)
item_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")

ttk.Label(root, text="Item Count:").grid(row=2, column=0, sticky="e")
entry_count = ttk.Entry(root, width=10)
entry_count.insert(0, "1")
entry_count.grid(row=2, column=1, padx=5, pady=5, sticky="w")

ttk.Label(root, text="Start Slot:").grid(row=3, column=0, sticky="e")
entry_start = ttk.Entry(root, width=10)
entry_start.insert(0, "8")
entry_start.grid(row=3, column=1, padx=5, pady=5, sticky="w")

ttk.Label(root, text="End Slot:").grid(row=4, column=0, sticky="e")
entry_end = ttk.Entry(root, width=10)
entry_end.insert(0, "8")
entry_end.grid(row=4, column=1, padx=5, pady=5, sticky="w")

readonly_notes = [
    "• Item Count can be larger than max stack size but you must split in-game to move.",
    "• Slots 0–7 are your Action Bar slots.",
    "• Slots 8–31 are your Main Inventory slots.",
    "• Slots 32–55 are your Rune Inventory slots.",
    "• Slots 56–79 are your Quest Inventory slots."
]

ttk.Label(root, text="Notes:").grid(row=5, column=0, sticky="ne", padx=5, pady=5)
for idx, note in enumerate(readonly_notes):
    ttk.Label(root, text=note, foreground="gold", background="#1c1b18", font=("Georgia", 9)).grid(
        row=5 + idx, column=1, columnspan=2, sticky="w", padx=5
    )

ttk.Button(root, text="Inject Items", command=inject_items).grid(row=10, column=0, columnspan=3, pady=15)

root.mainloop()
