import tkinter as tk
from tkinter import messagebox, ttk


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


class CharacterSelectDialog(tk.Toplevel):
    def __init__(self, parent, character_service, on_select):
        super().__init__(parent)
        self.title("Select Character")
        self.geometry("760x500")
        self.character_service = character_service
        self.on_select = on_select
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Select", command=self._select).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for character_id, character in self.character_service.list_characters():
            name = str(getattr(character, "name", "") or "")
            level = int(_safe_int(getattr(character, "level", 0), 0))
            display = f"{name} [{character_id}] (Lv {level})"
            if query and query not in display.lower():
                continue
            self.filtered.append((character_id, character))
            self.listbox.insert(tk.END, display)

    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Select Character", "Select a character.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        character_id, _ = self.filtered[index]
        self.on_select(character_id)
        self.destroy()


class SpellSelectDialog(tk.Toplevel):
    def __init__(self, parent, spell_service, on_select):
        super().__init__(parent)
        self.title("Select Spell")
        self.geometry("760x500")
        self.spell_service = spell_service
        self.on_select = on_select
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Select", command=self._select).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for spell in self.spell_service.list_spells():
            affinity = spell.affinity.value if hasattr(spell.affinity, "value") else spell.affinity
            label = f"{spell.name} (Lv {spell.level}, {affinity})"
            if query and query not in label.lower():
                continue
            self.filtered.append(spell)
            self.listbox.insert(tk.END, label)

    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Select Spell", "Select a spell.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        spell = self.filtered[index]
        self.on_select(spell.name)
        self.destroy()


class ItemSelectDialog(tk.Toplevel):
    def __init__(self, parent, item_service, on_select, allowed_slots=None):
        super().__init__(parent)
        self.title("Select Item")
        self.geometry("760x500")
        self.item_service = item_service
        self.on_select = on_select
        self.allowed_slots = set(allowed_slots or []) if allowed_slots is not None else None
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Select", command=self._select).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for item in self.item_service.list_items():
            if self.allowed_slots is not None and not any(item.can_equip_in(slot) for slot in self.allowed_slots):
                continue
            label = self.item_service.get_item_label(item)
            if query and query not in label.lower():
                continue
            self.filtered.append(item)
            self.listbox.insert(tk.END, label)

    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Select Item", "Select an item.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        item = self.filtered[index]
        self.on_select(item.itemId)
        self.destroy()



class UnitSelectDialog(tk.Toplevel):
    def __init__(self, parent, unit_service, on_select, exclude_ids=None):
        super().__init__(parent)
        self.title("Select Unit")
        self.geometry("760x500")
        self.unit_service = unit_service
        self.on_select = on_select
        self.exclude_ids = {str(entry or "").strip() for entry in (exclude_ids or []) if str(entry or "").strip()}
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Select", command=self._select).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for unit in self.unit_service.list_units():
            if unit.unitId in self.exclude_ids:
                continue
            label = self.unit_service.get_unit_label(unit)
            if query and query not in label.lower():
                continue
            self.filtered.append(unit)
            self.listbox.insert(tk.END, label)

    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Select Unit", "Select a unit.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        unit = self.filtered[index]
        self.on_select(unit.unitId)
        self.destroy()

class AllegianceSelectDialog(tk.Toplevel):
    def __init__(self, parent, allegiance_service, on_select, exclude_ids=None):
        super().__init__(parent)
        self.title("Select Allegiance")
        self.geometry("760x500")
        self.allegiance_service = allegiance_service
        self.on_select = on_select
        self.exclude_ids = {str(entry or "").strip() for entry in (exclude_ids or []) if str(entry or "").strip()}
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Select", command=self._select).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for allegiance in self.allegiance_service.list_allegiances():
            if allegiance.allegianceId in self.exclude_ids:
                continue
            label = self.allegiance_service.get_allegiance_label(allegiance)
            if query and query not in label.lower():
                continue
            self.filtered.append(allegiance)
            self.listbox.insert(tk.END, label)

    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Select Allegiance", "Select an allegiance.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        allegiance = self.filtered[index]
        self.on_select(allegiance.allegianceId)
        self.destroy()


class EffectSelectDialog(tk.Toplevel):
    def __init__(self, parent, environment_service, on_select, exclude_ids=None):
        super().__init__(parent)
        self.title("Select Effect")
        self.geometry("760x500")
        self.environment_service = environment_service
        self.on_select = on_select
        self.exclude_ids = {str(entry or "").strip() for entry in (exclude_ids or []) if str(entry or "").strip()}
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Select", command=self._select).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for effect in self.environment_service.list_effects():
            if effect.effectId in self.exclude_ids:
                continue
            label = self.environment_service.get_effect_label(effect)
            if query and query not in label.lower():
                continue
            self.filtered.append(effect)
            self.listbox.insert(tk.END, label)

    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Select Effect", "Select an effect.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        effect = self.filtered[index]
        self.on_select(effect.effectId)
        self.destroy()


class TerrainSelectDialog(tk.Toplevel):
    def __init__(self, parent, environment_service, on_select, exclude_ids=None):
        super().__init__(parent)
        self.title("Select Terrain")
        self.geometry("760x500")
        self.environment_service = environment_service
        self.on_select = on_select
        self.exclude_ids = {str(entry or "").strip() for entry in (exclude_ids or []) if str(entry or "").strip()}
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Select", command=self._select).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for terrain in self.environment_service.list_terrains():
            if terrain.terrainId in self.exclude_ids:
                continue
            label = self.environment_service.get_terrain_label(terrain)
            if query and query not in label.lower():
                continue
            self.filtered.append(terrain)
            self.listbox.insert(tk.END, label)

    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Select Terrain", "Select a terrain.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        terrain = self.filtered[index]
        self.on_select(terrain.terrainId)
        self.destroy()


class ClimateSelectDialog(tk.Toplevel):
    def __init__(self, parent, environment_service, on_select, exclude_ids=None):
        super().__init__(parent)
        self.title("Select Climate")
        self.geometry("760x500")
        self.environment_service = environment_service
        self.on_select = on_select
        self.exclude_ids = {str(entry or "").strip() for entry in (exclude_ids or []) if str(entry or "").strip()}
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Select", command=self._select).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for climate in self.environment_service.list_climates():
            if climate.climateId in self.exclude_ids:
                continue
            label = self.environment_service.get_climate_label(climate)
            if query and query not in label.lower():
                continue
            self.filtered.append(climate)
            self.listbox.insert(tk.END, label)

    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Select Climate", "Select a climate.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        climate = self.filtered[index]
        self.on_select(climate.climateId)
        self.destroy()
