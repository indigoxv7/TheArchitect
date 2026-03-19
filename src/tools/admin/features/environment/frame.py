import tkinter as tk
from tkinter import ttk

from .dialogs import ClimateEditorTab, EffectEditorTab, TerrainEditorTab, _EditorTabBase
from src.domain.environment import CompatibilitySelectionMode, IncompatibilityMode
from src.tools.admin.shared.pickers import ClimateSelectDialog, EffectSelectDialog, TerrainSelectDialog


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
