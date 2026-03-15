import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Environment import CompatibilitySelectionMode, IncompatibilityMode
from src.tools.catalog_selectors import ClimateSelectDialog, EffectSelectDialog, TerrainSelectDialog


class _EditorTabBase(ttk.Frame):
    def __init__(self, parent, select_label: str, blank_label: str):
        super().__init__(parent)
        self.select_label = select_label
        self.blank_label = blank_label
        self.current_id = None

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=16).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text=select_label, width=16).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value=blank_label)
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

    def _row_entry(self, label, var):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=16).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _row_text(self, label, widget):
        row = ttk.Frame(self)
        row.pack(fill=tk.BOTH, expand=False, pady=2)
        ttk.Label(row, text=label, width=16).pack(side=tk.LEFT, anchor="n")
        widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _filtered_entries(self):
        raise NotImplementedError

    def _load_existing(self, identifier: str):
        raise NotImplementedError

    def _clear_form(self):
        raise NotImplementedError

    def refresh_list(self, reset_form: bool):
        labels = [self.blank_label] + [label for _identifier, label in self._filtered_entries()]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set(self.blank_label)
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set(self.blank_label)

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == self.blank_label:
            self._clear_form()
            return
        for identifier, label in self._filtered_entries():
            if label == selected:
                self._load_existing(identifier)
                return


class EffectEditorTab(_EditorTabBase):
    def __init__(self, parent, app):
        self.app = app
        super().__init__(parent, select_label="Select Effect", blank_label="<New Effect>")
        self.vars = {"name": tk.StringVar()}
        self._row_entry("Name", self.vars["name"])
        self.description_text = tk.Text(self, height=6, wrap=tk.WORD)
        self._row_text("Description", self.description_text)
        self.counterplay_text = tk.Text(self, height=5, wrap=tk.WORD)
        self._row_text("Counterplay", self.counterplay_text)
        ttk.Button(self, text="Save Effect", command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _filtered_entries(self):
        query = self.search_var.get().strip().lower()
        result = []
        for effect in self.app.environment_service.list_effects():
            label = self.app.environment_service.get_effect_label(effect)
            if query and query not in label.lower():
                continue
            result.append((effect.effectId, label))
        return result

    def _clear_form(self):
        self.current_id = None
        self.vars["name"].set("")
        self.description_text.delete("1.0", tk.END)
        self.counterplay_text.delete("1.0", tk.END)

    def _load_existing(self, identifier: str):
        effect = self.app.environment_service.get_effect_by_id(identifier)
        if effect is None:
            return
        self.current_id = effect.effectId
        self.vars["name"].set(effect.name)
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert(tk.END, effect.description)
        self.counterplay_text.delete("1.0", tk.END)
        self.counterplay_text.insert(tk.END, effect.counterplay)

    def _save(self):
        payload = {
            "name": self.vars["name"].get().strip(),
            "description": self.description_text.get("1.0", tk.END).strip(),
            "counterplay": self.counterplay_text.get("1.0", tk.END).strip(),
        }
        if not payload["name"]:
            messagebox.showerror("Effect Editor", "Effect name is required.")
            return
        try:
            if self.current_id:
                effect = self.app.environment_service.edit_effect_from_patch(self.current_id, payload)
                self.current_id = effect.effectId
            else:
                effect = self.app.environment_service.create_effect_from_dict(payload)
                self.current_id = effect.effectId
            messagebox.showinfo("Effect Editor", "Effect saved.")
            self.refresh_list(reset_form=False)
            self.pick_var.set(self.app.environment_service.get_effect_label(effect))
        except Exception as exc:
            messagebox.showerror("Effect Editor", f"Failed to save effect: {exc}")


class TerrainEditorTab(_EditorTabBase):
    def __init__(self, parent, app):
        self.app = app
        self.effect_ids = []
        super().__init__(parent, select_label="Select Terrain", blank_label="<New Terrain>")
        self.vars = {"name": tk.StringVar()}
        self._row_entry("Name", self.vars["name"])
        self.description_text = tk.Text(self, height=6, wrap=tk.WORD)
        self._row_text("Description", self.description_text)

        effect_panel = ttk.LabelFrame(self, text="Effects")
        effect_panel.pack(fill=tk.BOTH, expand=False, pady=6)
        self.effect_listbox = tk.Listbox(effect_panel, height=5)
        self.effect_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        actions = ttk.Frame(effect_panel)
        actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(actions, text="Add Effect", command=self._add_effect).pack(side=tk.LEFT)
        ttk.Button(actions, text="Remove Selected", command=self._remove_selected_effect).pack(side=tk.LEFT, padx=6)

        ttk.Button(self, text="Save Terrain", command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _filtered_entries(self):
        query = self.search_var.get().strip().lower()
        result = []
        for terrain in self.app.environment_service.list_terrains():
            label = self.app.environment_service.get_terrain_label(terrain)
            if query and query not in label.lower():
                continue
            result.append((terrain.terrainId, label))
        return result

    def _refresh_effect_list(self):
        self.effect_listbox.delete(0, tk.END)
        for effect_id in self.effect_ids:
            effect = self.app.environment_service.get_effect_by_id(effect_id)
            label = self.app.environment_service.get_effect_label(effect) if effect is not None else f"Unknown [{effect_id}]"
            self.effect_listbox.insert(tk.END, label)

    def _clear_form(self):
        self.current_id = None
        self.vars["name"].set("")
        self.description_text.delete("1.0", tk.END)
        self.effect_ids = []
        self._refresh_effect_list()

    def _load_existing(self, identifier: str):
        terrain = self.app.environment_service.get_terrain_by_id(identifier)
        if terrain is None:
            return
        self.current_id = terrain.terrainId
        self.vars["name"].set(terrain.name)
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert(tk.END, terrain.description)
        self.effect_ids = list(terrain.effectIds)
        self._refresh_effect_list()

    def _add_effect(self):
        def _on_select(effect_id):
            if effect_id and effect_id not in self.effect_ids:
                self.effect_ids.append(effect_id)
                self._refresh_effect_list()

        EffectSelectDialog(self, self.app.environment_service, _on_select, exclude_ids=self.effect_ids)

    def _remove_selected_effect(self):
        selection = self.effect_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.effect_ids):
            self.effect_ids.pop(index)
            self._refresh_effect_list()

    def _save(self):
        payload = {
            "name": self.vars["name"].get().strip(),
            "description": self.description_text.get("1.0", tk.END).strip(),
            "effectIds": list(self.effect_ids),
        }
        if not payload["name"]:
            messagebox.showerror("Terrain Editor", "Terrain name is required.")
            return
        try:
            if self.current_id:
                terrain = self.app.environment_service.edit_terrain_from_patch(self.current_id, payload)
                self.current_id = terrain.terrainId
            else:
                terrain = self.app.environment_service.create_terrain_from_dict(payload)
                self.current_id = terrain.terrainId
            messagebox.showinfo("Terrain Editor", "Terrain saved.")
            self.refresh_list(reset_form=False)
            self.pick_var.set(self.app.environment_service.get_terrain_label(terrain))
        except Exception as exc:
            messagebox.showerror("Terrain Editor", f"Failed to save terrain: {exc}")


class ClimateEditorTab(_EditorTabBase):
    def __init__(self, parent, app):
        self.app = app
        self.effect_ids = []
        super().__init__(parent, select_label="Select Climate", blank_label="<New Climate>")
        self.vars = {
            "name": tk.StringVar(),
            "temperature": tk.StringVar(),
            "humidity": tk.StringVar(),
        }
        self._row_entry("Name", self.vars["name"])
        self._row_entry("Temperature", self.vars["temperature"])
        self._row_entry("Humidity", self.vars["humidity"])
        self.description_text = tk.Text(self, height=6, wrap=tk.WORD)
        self._row_text("Description", self.description_text)

        effect_panel = ttk.LabelFrame(self, text="Effects")
        effect_panel.pack(fill=tk.BOTH, expand=False, pady=6)
        self.effect_listbox = tk.Listbox(effect_panel, height=5)
        self.effect_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        actions = ttk.Frame(effect_panel)
        actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(actions, text="Add Effect", command=self._add_effect).pack(side=tk.LEFT)
        ttk.Button(actions, text="Remove Selected", command=self._remove_selected_effect).pack(side=tk.LEFT, padx=6)

        ttk.Button(self, text="Save Climate", command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _filtered_entries(self):
        query = self.search_var.get().strip().lower()
        result = []
        for climate in self.app.environment_service.list_climates():
            label = self.app.environment_service.get_climate_label(climate)
            if query and query not in label.lower():
                continue
            result.append((climate.climateId, label))
        return result

    def _refresh_effect_list(self):
        self.effect_listbox.delete(0, tk.END)
        for effect_id in self.effect_ids:
            effect = self.app.environment_service.get_effect_by_id(effect_id)
            label = self.app.environment_service.get_effect_label(effect) if effect is not None else f"Unknown [{effect_id}]"
            self.effect_listbox.insert(tk.END, label)

    def _clear_form(self):
        self.current_id = None
        self.vars["name"].set("")
        self.vars["temperature"].set("")
        self.vars["humidity"].set("")
        self.description_text.delete("1.0", tk.END)
        self.effect_ids = []
        self._refresh_effect_list()

    def _load_existing(self, identifier: str):
        climate = self.app.environment_service.get_climate_by_id(identifier)
        if climate is None:
            return
        self.current_id = climate.climateId
        self.vars["name"].set(climate.name)
        self.vars["temperature"].set(climate.temperature)
        self.vars["humidity"].set(climate.humidity)
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert(tk.END, climate.description)
        self.effect_ids = list(climate.effectIds)
        self._refresh_effect_list()

    def _add_effect(self):
        def _on_select(effect_id):
            if effect_id and effect_id not in self.effect_ids:
                self.effect_ids.append(effect_id)
                self._refresh_effect_list()

        EffectSelectDialog(self, self.app.environment_service, _on_select, exclude_ids=self.effect_ids)

    def _remove_selected_effect(self):
        selection = self.effect_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.effect_ids):
            self.effect_ids.pop(index)
            self._refresh_effect_list()

    def _save(self):
        payload = {
            "name": self.vars["name"].get().strip(),
            "temperature": self.vars["temperature"].get().strip(),
            "humidity": self.vars["humidity"].get().strip(),
            "description": self.description_text.get("1.0", tk.END).strip(),
            "effectIds": list(self.effect_ids),
        }
        if not payload["name"]:
            messagebox.showerror("Climate Editor", "Climate name is required.")
            return
        try:
            if self.current_id:
                climate = self.app.environment_service.edit_climate_from_patch(self.current_id, payload)
                self.current_id = climate.climateId
            else:
                climate = self.app.environment_service.create_climate_from_dict(payload)
                self.current_id = climate.climateId
            messagebox.showinfo("Climate Editor", "Climate saved.")
            self.refresh_list(reset_form=False)
            self.pick_var.set(self.app.environment_service.get_climate_label(climate))
        except Exception as exc:
            messagebox.showerror("Climate Editor", f"Failed to save climate: {exc}")

class BiomeEditorTab(_EditorTabBase):
    def __init__(self, parent, app):
        self.app = app
        self.effect_ids = []
        self.compatible_terrain_ids = []
        self.incompatible_terrain_ids = []
        self.compatible_climate_ids = []
        self.incompatible_climate_ids = []
        super().__init__(parent, select_label="Select Biome", blank_label="<New Biome>")
        self.vars = {
            "name": tk.StringVar(),
            "terrainCompatibilityMode": tk.StringVar(value=CompatibilitySelectionMode.ANY.value),
            "terrainIncompatibilityMode": tk.StringVar(value=IncompatibilityMode.EXPLICIT.value),
            "climateCompatibilityMode": tk.StringVar(value=CompatibilitySelectionMode.ANY.value),
            "climateIncompatibilityMode": tk.StringVar(value=IncompatibilityMode.EXPLICIT.value),
        }
        self._row_entry("Name", self.vars["name"])
        self.description_text = tk.Text(self, height=5, wrap=tk.WORD)
        self._row_text("Description", self.description_text)

        effect_panel = ttk.LabelFrame(self, text="Effects")
        effect_panel.pack(fill=tk.BOTH, expand=False, pady=6)
        self.effect_listbox = tk.Listbox(effect_panel, height=4)
        self.effect_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        effect_actions = ttk.Frame(effect_panel)
        effect_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(effect_actions, text="Add Effect", command=self._add_effect).pack(side=tk.LEFT)
        ttk.Button(effect_actions, text="Remove Selected", command=self._remove_selected_effect).pack(side=tk.LEFT, padx=6)

        terrain_mode_row = ttk.Frame(self)
        terrain_mode_row.pack(fill=tk.X, pady=2)
        ttk.Label(terrain_mode_row, text="Terrain Mode", width=16).pack(side=tk.LEFT)
        ttk.Combobox(
            terrain_mode_row,
            state="readonly",
            values=[entry.value for entry in CompatibilitySelectionMode],
            textvariable=self.vars["terrainCompatibilityMode"],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        terrain_incompat_row = ttk.Frame(self)
        terrain_incompat_row.pack(fill=tk.X, pady=2)
        ttk.Label(terrain_incompat_row, text="Terrain Exclusions", width=16).pack(side=tk.LEFT)
        ttk.Combobox(
            terrain_incompat_row,
            state="readonly",
            values=[entry.value for entry in IncompatibilityMode],
            textvariable=self.vars["terrainIncompatibilityMode"],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        terrain_lists = ttk.Frame(self)
        terrain_lists.pack(fill=tk.BOTH, expand=False, pady=6)
        compatible_terrain_panel = ttk.LabelFrame(terrain_lists, text="Compatible Terrains")
        compatible_terrain_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        self.compatible_terrain_listbox = tk.Listbox(compatible_terrain_panel, height=5)
        self.compatible_terrain_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        compatible_terrain_actions = ttk.Frame(compatible_terrain_panel)
        compatible_terrain_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.compatible_terrain_add_button = ttk.Button(compatible_terrain_actions, text="Add", command=self._add_compatible_terrain)
        self.compatible_terrain_add_button.pack(side=tk.LEFT)
        self.compatible_terrain_remove_button = ttk.Button(compatible_terrain_actions, text="Remove", command=self._remove_selected_compatible_terrain)
        self.compatible_terrain_remove_button.pack(side=tk.LEFT, padx=6)

        incompatible_terrain_panel = ttk.LabelFrame(terrain_lists, text="Incompatible Terrains")
        incompatible_terrain_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        self.incompatible_terrain_listbox = tk.Listbox(incompatible_terrain_panel, height=5)
        self.incompatible_terrain_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        incompatible_terrain_actions = ttk.Frame(incompatible_terrain_panel)
        incompatible_terrain_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.incompatible_terrain_add_button = ttk.Button(incompatible_terrain_actions, text="Add", command=self._add_incompatible_terrain)
        self.incompatible_terrain_add_button.pack(side=tk.LEFT)
        self.incompatible_terrain_remove_button = ttk.Button(incompatible_terrain_actions, text="Remove", command=self._remove_selected_incompatible_terrain)
        self.incompatible_terrain_remove_button.pack(side=tk.LEFT, padx=6)

        climate_mode_row = ttk.Frame(self)
        climate_mode_row.pack(fill=tk.X, pady=2)
        ttk.Label(climate_mode_row, text="Climate Mode", width=16).pack(side=tk.LEFT)
        ttk.Combobox(
            climate_mode_row,
            state="readonly",
            values=[entry.value for entry in CompatibilitySelectionMode],
            textvariable=self.vars["climateCompatibilityMode"],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        climate_incompat_row = ttk.Frame(self)
        climate_incompat_row.pack(fill=tk.X, pady=2)
        ttk.Label(climate_incompat_row, text="Climate Exclusions", width=16).pack(side=tk.LEFT)
        ttk.Combobox(
            climate_incompat_row,
            state="readonly",
            values=[entry.value for entry in IncompatibilityMode],
            textvariable=self.vars["climateIncompatibilityMode"],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        climate_lists = ttk.Frame(self)
        climate_lists.pack(fill=tk.BOTH, expand=False, pady=6)
        compatible_climate_panel = ttk.LabelFrame(climate_lists, text="Compatible Climates")
        compatible_climate_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        self.compatible_climate_listbox = tk.Listbox(compatible_climate_panel, height=5)
        self.compatible_climate_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        compatible_climate_actions = ttk.Frame(compatible_climate_panel)
        compatible_climate_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.compatible_climate_add_button = ttk.Button(compatible_climate_actions, text="Add", command=self._add_compatible_climate)
        self.compatible_climate_add_button.pack(side=tk.LEFT)
        self.compatible_climate_remove_button = ttk.Button(compatible_climate_actions, text="Remove", command=self._remove_selected_compatible_climate)
        self.compatible_climate_remove_button.pack(side=tk.LEFT, padx=6)

        incompatible_climate_panel = ttk.LabelFrame(climate_lists, text="Incompatible Climates")
        incompatible_climate_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        self.incompatible_climate_listbox = tk.Listbox(incompatible_climate_panel, height=5)
        self.incompatible_climate_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        incompatible_climate_actions = ttk.Frame(incompatible_climate_panel)
        incompatible_climate_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.incompatible_climate_add_button = ttk.Button(incompatible_climate_actions, text="Add", command=self._add_incompatible_climate)
        self.incompatible_climate_add_button.pack(side=tk.LEFT)
        self.incompatible_climate_remove_button = ttk.Button(incompatible_climate_actions, text="Remove", command=self._remove_selected_incompatible_climate)
        self.incompatible_climate_remove_button.pack(side=tk.LEFT, padx=6)

        ttk.Button(self, text="Save Biome", command=self._save).pack(fill=tk.X, pady=8)
        self.vars["terrainCompatibilityMode"].trace_add("write", self._refresh_mode_state)
        self.vars["terrainIncompatibilityMode"].trace_add("write", self._refresh_mode_state)
        self.vars["climateCompatibilityMode"].trace_add("write", self._refresh_mode_state)
        self.vars["climateIncompatibilityMode"].trace_add("write", self._refresh_mode_state)
        self._clear_form()

    def _filtered_entries(self):
        query = self.search_var.get().strip().lower()
        result = []
        for biome in self.app.environment_service.list_biomes():
            label = self.app.environment_service.get_biome_label(biome)
            if query and query not in label.lower():
                continue
            result.append((biome.biomeId, label))
        return result

    def _labels_for_ids(self, ids, getter, labeler):
        labels = []
        for identifier in ids:
            entry = getter(identifier)
            labels.append(labeler(entry) if entry is not None else f"Unknown [{identifier}]")
        return labels

    def _refresh_listbox(self, listbox, labels):
        listbox.delete(0, tk.END)
        for label in labels:
            listbox.insert(tk.END, label)

    def _refresh_all_lists(self):
        service = self.app.environment_service
        self._refresh_listbox(self.effect_listbox, self._labels_for_ids(self.effect_ids, service.get_effect_by_id, service.get_effect_label))
        self._refresh_listbox(self.compatible_terrain_listbox, self._labels_for_ids(self.compatible_terrain_ids, service.get_terrain_by_id, service.get_terrain_label))
        self._refresh_listbox(self.incompatible_terrain_listbox, self._labels_for_ids(self.incompatible_terrain_ids, service.get_terrain_by_id, service.get_terrain_label))
        self._refresh_listbox(self.compatible_climate_listbox, self._labels_for_ids(self.compatible_climate_ids, service.get_climate_by_id, service.get_climate_label))
        self._refresh_listbox(self.incompatible_climate_listbox, self._labels_for_ids(self.incompatible_climate_ids, service.get_climate_by_id, service.get_climate_label))

    def _clear_form(self):
        self.current_id = None
        self.vars["name"].set("")
        self.vars["terrainCompatibilityMode"].set(CompatibilitySelectionMode.ANY.value)
        self.vars["terrainIncompatibilityMode"].set(IncompatibilityMode.EXPLICIT.value)
        self.vars["climateCompatibilityMode"].set(CompatibilitySelectionMode.ANY.value)
        self.vars["climateIncompatibilityMode"].set(IncompatibilityMode.EXPLICIT.value)
        self.description_text.delete("1.0", tk.END)
        self.effect_ids = []
        self.compatible_terrain_ids = []
        self.incompatible_terrain_ids = []
        self.compatible_climate_ids = []
        self.incompatible_climate_ids = []
        self._refresh_all_lists()
        self._refresh_mode_state()

    def _load_existing(self, identifier: str):
        biome = self.app.environment_service.get_biome_by_id(identifier)
        if biome is None:
            return
        self.current_id = biome.biomeId
        self.vars["name"].set(biome.name)
        self.vars["terrainCompatibilityMode"].set(biome.terrainCompatibilityMode.value)
        self.vars["terrainIncompatibilityMode"].set(biome.terrainIncompatibilityMode.value)
        self.vars["climateCompatibilityMode"].set(biome.climateCompatibilityMode.value)
        self.vars["climateIncompatibilityMode"].set(biome.climateIncompatibilityMode.value)
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert(tk.END, biome.description)
        self.effect_ids = list(biome.effectIds)
        self.compatible_terrain_ids = list(biome.compatibleTerrainIds)
        self.incompatible_terrain_ids = list(biome.incompatibleTerrainIds)
        self.compatible_climate_ids = list(biome.compatibleClimateIds)
        self.incompatible_climate_ids = list(biome.incompatibleClimateIds)
        self._refresh_all_lists()
        self._refresh_mode_state()
    def _refresh_mode_state(self, *_args):
        terrain_any = self.vars["terrainCompatibilityMode"].get() == CompatibilitySelectionMode.ANY.value
        terrain_all_except = self.vars["terrainIncompatibilityMode"].get() == IncompatibilityMode.ALL_EXCEPT_COMPATIBLE.value
        climate_any = self.vars["climateCompatibilityMode"].get() == CompatibilitySelectionMode.ANY.value
        climate_all_except = self.vars["climateIncompatibilityMode"].get() == IncompatibilityMode.ALL_EXCEPT_COMPATIBLE.value

        self.compatible_terrain_listbox.configure(state=(tk.DISABLED if terrain_any else tk.NORMAL))
        self.compatible_terrain_add_button.configure(state=(tk.DISABLED if terrain_any else tk.NORMAL))
        self.compatible_terrain_remove_button.configure(state=(tk.DISABLED if terrain_any else tk.NORMAL))
        self.incompatible_terrain_listbox.configure(state=(tk.DISABLED if terrain_all_except else tk.NORMAL))
        self.incompatible_terrain_add_button.configure(state=(tk.DISABLED if terrain_all_except else tk.NORMAL))
        self.incompatible_terrain_remove_button.configure(state=(tk.DISABLED if terrain_all_except else tk.NORMAL))

        self.compatible_climate_listbox.configure(state=(tk.DISABLED if climate_any else tk.NORMAL))
        self.compatible_climate_add_button.configure(state=(tk.DISABLED if climate_any else tk.NORMAL))
        self.compatible_climate_remove_button.configure(state=(tk.DISABLED if climate_any else tk.NORMAL))
        self.incompatible_climate_listbox.configure(state=(tk.DISABLED if climate_all_except else tk.NORMAL))
        self.incompatible_climate_add_button.configure(state=(tk.DISABLED if climate_all_except else tk.NORMAL))
        self.incompatible_climate_remove_button.configure(state=(tk.DISABLED if climate_all_except else tk.NORMAL))

    def _add_effect(self):
        def _on_select(effect_id):
            if effect_id and effect_id not in self.effect_ids:
                self.effect_ids.append(effect_id)
                self._refresh_all_lists()

        EffectSelectDialog(self, self.app.environment_service, _on_select, exclude_ids=self.effect_ids)

    def _remove_selected_effect(self):
        selection = self.effect_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.effect_ids):
            self.effect_ids.pop(index)
            self._refresh_all_lists()

    def _add_compatible_terrain(self):
        def _on_select(terrain_id):
            if terrain_id and terrain_id not in self.compatible_terrain_ids:
                self.compatible_terrain_ids.append(terrain_id)
                self._refresh_all_lists()

        exclude = list(set(self.compatible_terrain_ids + self.incompatible_terrain_ids))
        TerrainSelectDialog(self, self.app.environment_service, _on_select, exclude_ids=exclude)

    def _remove_selected_compatible_terrain(self):
        selection = self.compatible_terrain_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.compatible_terrain_ids):
            self.compatible_terrain_ids.pop(index)
            self._refresh_all_lists()

    def _add_incompatible_terrain(self):
        def _on_select(terrain_id):
            if terrain_id and terrain_id not in self.incompatible_terrain_ids:
                self.incompatible_terrain_ids.append(terrain_id)
                self._refresh_all_lists()

        exclude = list(set(self.compatible_terrain_ids + self.incompatible_terrain_ids))
        TerrainSelectDialog(self, self.app.environment_service, _on_select, exclude_ids=exclude)

    def _remove_selected_incompatible_terrain(self):
        selection = self.incompatible_terrain_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.incompatible_terrain_ids):
            self.incompatible_terrain_ids.pop(index)
            self._refresh_all_lists()

    def _add_compatible_climate(self):
        def _on_select(climate_id):
            if climate_id and climate_id not in self.compatible_climate_ids:
                self.compatible_climate_ids.append(climate_id)
                self._refresh_all_lists()

        exclude = list(set(self.compatible_climate_ids + self.incompatible_climate_ids))
        ClimateSelectDialog(self, self.app.environment_service, _on_select, exclude_ids=exclude)

    def _remove_selected_compatible_climate(self):
        selection = self.compatible_climate_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.compatible_climate_ids):
            self.compatible_climate_ids.pop(index)
            self._refresh_all_lists()

    def _add_incompatible_climate(self):
        def _on_select(climate_id):
            if climate_id and climate_id not in self.incompatible_climate_ids:
                self.incompatible_climate_ids.append(climate_id)
                self._refresh_all_lists()

        exclude = list(set(self.compatible_climate_ids + self.incompatible_climate_ids))
        ClimateSelectDialog(self, self.app.environment_service, _on_select, exclude_ids=exclude)

    def _remove_selected_incompatible_climate(self):
        selection = self.incompatible_climate_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.incompatible_climate_ids):
            self.incompatible_climate_ids.pop(index)
            self._refresh_all_lists()

    def _save(self):
        payload = {
            "name": self.vars["name"].get().strip(),
            "description": self.description_text.get("1.0", tk.END).strip(),
            "effectIds": list(self.effect_ids),
            "terrainCompatibilityMode": self.vars["terrainCompatibilityMode"].get(),
            "compatibleTerrainIds": list(self.compatible_terrain_ids),
            "terrainIncompatibilityMode": self.vars["terrainIncompatibilityMode"].get(),
            "incompatibleTerrainIds": list(self.incompatible_terrain_ids),
            "climateCompatibilityMode": self.vars["climateCompatibilityMode"].get(),
            "compatibleClimateIds": list(self.compatible_climate_ids),
            "climateIncompatibilityMode": self.vars["climateIncompatibilityMode"].get(),
            "incompatibleClimateIds": list(self.incompatible_climate_ids),
        }
        if not payload["name"]:
            messagebox.showerror("Biome Editor", "Biome name is required.")
            return
        try:
            if self.current_id:
                biome = self.app.environment_service.edit_biome_from_patch(self.current_id, payload)
                self.current_id = biome.biomeId
            else:
                biome = self.app.environment_service.create_biome_from_dict(payload)
                self.current_id = biome.biomeId
            messagebox.showinfo("Biome Editor", "Biome saved.")
            self.refresh_list(reset_form=False)
            self.pick_var.set(self.app.environment_service.get_biome_label(biome))
        except Exception as exc:
            messagebox.showerror("Biome Editor", f"Failed to save biome: {exc}")


class EnvironmentEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Environment Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)
        self.effect_tab = EffectEditorTab(notebook, app)
        self.terrain_tab = TerrainEditorTab(notebook, app)
        self.climate_tab = ClimateEditorTab(notebook, app)
        self.biome_tab = BiomeEditorTab(notebook, app)
        notebook.add(self.effect_tab, text="Effects")
        notebook.add(self.terrain_tab, text="Terrains")
        notebook.add(self.climate_tab, text="Climates")
        notebook.add(self.biome_tab, text="Biomes")

    def refresh_all(self, reset_forms: bool):
        self.effect_tab.refresh_list(reset_form=reset_forms)
        self.terrain_tab.refresh_list(reset_form=reset_forms)
        self.climate_tab.refresh_list(reset_form=reset_forms)
        self.biome_tab.refresh_list(reset_form=reset_forms)
