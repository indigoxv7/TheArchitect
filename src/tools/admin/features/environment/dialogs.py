import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Environment import CompatibilitySelectionMode, IncompatibilityMode
from src.tools.admin.shared.pickers import ClimateSelectDialog, EffectSelectDialog, TerrainSelectDialog


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
