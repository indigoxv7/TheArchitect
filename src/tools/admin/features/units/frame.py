import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.race import CreatureSize
from src.tools.admin.shared.pickers import CharacterSelectDialog, SpellSelectDialog
from src.tools.admin.shared.gear_options import GearOptionsEditorDialog, normalize_gear_options_payload
from .dialogs import AttributeBoundsEditorDialog
from .helpers import UnitEditorFrameMixin, _safe_int


class UnitEditorFrame(UnitEditorFrameMixin, ttk.Frame):
    SIMPLE_FIELD_SPECS = [
        ("name", "Name"),
        ("detailedDescription", "Detailed Description"),
        ("beifDescription", "Brief Description"),
        ("juvenileNomenclature", "Juvenile Nomenclature"),
    ]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_unit_id = None
        self.selected_race_id = ""
        self.average_specimine_character_id_override = None
        self.attribute_bounds_override = None
        self.spell_names_by_level_override = None
        self.famed_enemy_character_ids_override = None
        self.gear_options_override = None

        self.simple_override_vars = {}
        self.simple_value_vars = {}
        self.simple_widgets = {}
        self.summary_vars = {}

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Unit Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        race_row = ttk.Frame(self)
        race_row.pack(fill=tk.X, pady=4)
        ttk.Label(race_row, text="Base Race", width=18).pack(side=tk.LEFT)
        self.race_var = tk.StringVar(value="")
        self.race_pick = ttk.Combobox(race_row, state="readonly", textvariable=self.race_var)
        self.race_pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.race_pick.bind("<<ComboboxSelected>>", self._on_race_changed)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search Units", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_unit_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Unit", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Unit>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        for field_name, label in self.SIMPLE_FIELD_SPECS:
            self._build_override_entry_row(field_name, label)

        self._build_override_combo_row(
            "size", "Size", [entry.name for entry in CreatureSize], default_value=CreatureSize.STANDARD.name
        )
        self._build_average_specimine_row()
        self._build_complex_override_section("attributeBounds", "Attribute Bounds", self._edit_attribute_bounds)
        self._build_complex_override_section("spellList", "Spell List", self._edit_spell_list)
        self._build_complex_override_section("FamedEnemyList", "Famed Enemies", self._edit_famed_enemies)
        self._build_complex_override_section("gearOptions", "Gear Options", self._edit_gear_options)

        self.summary = tk.Text(self, height=12, wrap=tk.WORD)
        self.summary.pack(fill=tk.BOTH, expand=True, pady=6)

        ttk.Button(self, text="Save Unit", command=self._save).pack(fill=tk.X, pady=8)

        self.refresh_race_list(reset_selection=True)
        self._clear_form()

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Unit>":
            self._clear_form()
            return

        unit_id = self.app.unit_service.parse_unit_id_from_label(selected)
        unit = self.app.unit_service.get_unit(unit_id)
        if unit is None:
            return
        self._load_unit(unit)

    def _load_unit(self, unit):
        self.current_unit_id = unit.unitId
        self.selected_race_id = unit.baseRaceId
        race = self._get_selected_race()
        if race is not None:
            self.race_var.set(self._race_label(race))
        self.average_specimine_character_id_override = (
            self.app.unit_service._resolve_character_id(unit.averageSpecimine)
            if unit.averageSpecimine is not None
            else None
        )
        self.attribute_bounds_override = None
        if unit.minAverageAttributes is not None or unit.maxAverageAttributes is not None:
            self.attribute_bounds_override = {
                "minAverageAttributes": self._base_attribute_bounds()["minAverageAttributes"]
                if unit.minAverageAttributes is None
                else {
                    "physicalPower": float(getattr(unit.minAverageAttributes, "physicalPower", 5)),
                    "physicalStamina": float(getattr(unit.minAverageAttributes, "physicalStamina", 5)),
                    "physicalResistance": float(getattr(unit.minAverageAttributes, "physicalResistance", 5)),
                    "magicPower": float(getattr(unit.minAverageAttributes, "magicPower", 5)),
                    "magicStamina": float(getattr(unit.minAverageAttributes, "magicStamina", 5)),
                    "magicResistance": float(getattr(unit.minAverageAttributes, "magicResistance", 5)),
                },
                "maxAverageAttributes": self._base_attribute_bounds()["maxAverageAttributes"]
                if unit.maxAverageAttributes is None
                else {
                    "physicalPower": float(getattr(unit.maxAverageAttributes, "physicalPower", 5)),
                    "physicalStamina": float(getattr(unit.maxAverageAttributes, "physicalStamina", 5)),
                    "physicalResistance": float(getattr(unit.maxAverageAttributes, "physicalResistance", 5)),
                    "magicPower": float(getattr(unit.maxAverageAttributes, "magicPower", 5)),
                    "magicStamina": float(getattr(unit.maxAverageAttributes, "magicStamina", 5)),
                    "magicResistance": float(getattr(unit.maxAverageAttributes, "magicResistance", 5)),
                },
            }
        self.spell_names_by_level_override = (
            None
            if unit.spellList is None
            else [list(level_entries) for level_entries in unit.to_dict().get("spellList", [[] for _ in range(21)])]
        )
        self.famed_enemy_character_ids_override = None
        if unit.FamedEnemyList is not None:
            self.famed_enemy_character_ids_override = []
            for character in unit.FamedEnemyList:
                character_id = self.app.unit_service._resolve_character_id(character)
                if character_id:
                    self.famed_enemy_character_ids_override.append(character_id)
        self.gear_options_override = (
            None if unit.gearOptions is None else normalize_gear_options_payload(unit.gearOptions.to_dict())
        )

        simple_values = {
            "name": unit.name,
            "detailedDescription": unit.detailedDescription,
            "beifDescription": unit.beifDescription,
            "juvenileNomenclature": unit.juvenileNomenclature,
            "size": unit.size.name if unit.size is not None else None,
            "averageSpecimine": self._character_display_label(self.average_specimine_character_id_override)
            if self.average_specimine_character_id_override is not None
            else None,
        }

        for field_name, var in self.simple_override_vars.items():
            if field_name in {"attributeBounds", "spellList", "FamedEnemyList", "gearOptions"}:
                continue
            override_enabled = simple_values.get(field_name) is not None
            var.set(override_enabled)
            self.simple_value_vars[field_name].set(
                simple_values[field_name] if override_enabled else self._base_simple_value(field_name)
            )

        self.simple_override_vars["attributeBounds"].set(self.attribute_bounds_override is not None)
        self.simple_override_vars["spellList"].set(self.spell_names_by_level_override is not None)
        self.simple_override_vars["FamedEnemyList"].set(self.famed_enemy_character_ids_override is not None)
        self.simple_override_vars["gearOptions"].set(self.gear_options_override is not None)

        self._refresh_all_override_states()
        self._refresh_summary()

    def _refresh_all_override_states(self):
        for field_name in [
            "name",
            "detailedDescription",
            "beifDescription",
            "juvenileNomenclature",
            "size",
            "averageSpecimine",
        ]:
            self._refresh_simple_field_state(field_name)
        self._refresh_average_buttons()
        self._refresh_complex_summary("attributeBounds")
        self._refresh_complex_summary("spellList")
        self._refresh_complex_summary("FamedEnemyList")
        self._refresh_complex_summary("gearOptions")

    def _refresh_simple_field_state(self, field_name: str):
        widget = self.simple_widgets[field_name]
        enabled = bool(self.simple_override_vars[field_name].get())
        desired_state = "readonly" if isinstance(widget, ttk.Combobox) else "normal"
        if field_name == "averageSpecimine":
            widget.configure(state="readonly")
        else:
            widget.configure(state=desired_state if enabled else "disabled")
        if not enabled:
            self.simple_value_vars[field_name].set(self._base_simple_value(field_name))

    def _refresh_average_buttons(self):
        state = "normal" if self.simple_override_vars["averageSpecimine"].get() else "disabled"
        self.average_select_button.configure(state=state)
        self.average_clear_button.configure(state=state)

    def _on_simple_override_toggle(self, field_name: str):
        enabled = bool(self.simple_override_vars[field_name].get())
        if field_name == "averageSpecimine":
            if enabled and self.average_specimine_character_id_override is None:
                self.average_specimine_character_id_override = self._base_average_specimine_id()
                self.simple_value_vars[field_name].set(
                    self._character_display_label(self.average_specimine_character_id_override)
                    if self.average_specimine_character_id_override
                    else "<None>"
                )
            elif not enabled:
                self.average_specimine_character_id_override = None
        elif enabled:
            self.simple_value_vars[field_name].set(self._base_simple_value(field_name))
        self._refresh_simple_field_state(field_name)
        self._refresh_average_buttons()
        self._refresh_summary()

    def _on_complex_override_toggle(self, field_name: str):
        enabled = bool(self.simple_override_vars[field_name].get())
        if enabled:
            if field_name == "attributeBounds" and self.attribute_bounds_override is None:
                self.attribute_bounds_override = self._base_attribute_bounds()
            elif field_name == "spellList" and self.spell_names_by_level_override is None:
                self.spell_names_by_level_override = [list(level_entries) for level_entries in self._base_spell_list()]
            elif field_name == "FamedEnemyList" and self.famed_enemy_character_ids_override is None:
                self.famed_enemy_character_ids_override = list(self._base_famed_enemy_ids())
            elif field_name == "gearOptions" and self.gear_options_override is None:
                self.gear_options_override = normalize_gear_options_payload(self._base_gear_options())
        else:
            if field_name == "attributeBounds":
                self.attribute_bounds_override = None
            elif field_name == "spellList":
                self.spell_names_by_level_override = None
            elif field_name == "FamedEnemyList":
                self.famed_enemy_character_ids_override = None
            elif field_name == "gearOptions":
                self.gear_options_override = None
        self._refresh_complex_summary(field_name)
        self._refresh_summary()

    def _select_average_specimine(self):
        if not self.simple_override_vars["averageSpecimine"].get():
            self.simple_override_vars["averageSpecimine"].set(True)
            self._on_simple_override_toggle("averageSpecimine")

        def _on_select(character_id: str):
            self.average_specimine_character_id_override = character_id
            self.simple_value_vars["averageSpecimine"].set(self._character_display_label(character_id))
            self._refresh_summary()

        CharacterSelectDialog(self, self.app.character_service, _on_select)

    def _clear_average_specimine(self):
        if not self.simple_override_vars["averageSpecimine"].get():
            return
        self.average_specimine_character_id_override = ""
        self.simple_value_vars["averageSpecimine"].set("<None>")
        self._refresh_summary()

    def _edit_attribute_bounds(self):
        if not self.simple_override_vars["attributeBounds"].get():
            self.simple_override_vars["attributeBounds"].set(True)
            self._on_complex_override_toggle("attributeBounds")
        AttributeBoundsEditorDialog(self, self.attribute_bounds_override, self._on_attribute_bounds_saved)

    def _on_attribute_bounds_saved(self, payload):
        self.attribute_bounds_override = payload
        self._refresh_complex_summary("attributeBounds")
        self._refresh_summary()

    def _edit_spell_list(self):
        if not self.simple_override_vars["spellList"].get():
            self.simple_override_vars["spellList"].set(True)
            self._on_complex_override_toggle("spellList")
        dialog = tk.Toplevel(self)
        dialog.title("Edit Spell List")
        dialog.geometry("720x440")
        spell_level_var = tk.StringVar(value="0")
        spell_listbox = tk.Listbox(dialog, height=10)
        spell_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        def refresh_listbox():
            level = max(0, min(20, _safe_int(spell_level_var.get(), 0)))
            spell_listbox.delete(0, tk.END)
            for spell_name in self.spell_names_by_level_override[level]:
                spell_listbox.insert(tk.END, spell_name)

        top = ttk.Frame(dialog)
        top.pack(fill=tk.X, padx=10, pady=(10, 0))
        ttk.Label(top, text="Editing Level", width=16).pack(side=tk.LEFT)
        combo = ttk.Combobox(top, state="readonly", values=[str(i) for i in range(21)], textvariable=spell_level_var)
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        combo.bind("<<ComboboxSelected>>", lambda _e: refresh_listbox())

        actions = ttk.Frame(dialog)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))

        def add_spell():
            level = max(0, min(20, _safe_int(spell_level_var.get(), 0)))

            def _on_select(spell_name: str):
                if spell_name not in self.spell_names_by_level_override[level]:
                    self.spell_names_by_level_override[level].append(spell_name)
                    refresh_listbox()
                    self._refresh_complex_summary("spellList")
                    self._refresh_summary()

            SpellSelectDialog(dialog, self.app.spell_service, _on_select)

        def remove_spell():
            level = max(0, min(20, _safe_int(spell_level_var.get(), 0)))
            selection = spell_listbox.curselection()
            if not selection:
                return
            index = int(selection[0])
            if 0 <= index < len(self.spell_names_by_level_override[level]):
                self.spell_names_by_level_override[level].pop(index)
                refresh_listbox()
                self._refresh_complex_summary("spellList")
                self._refresh_summary()

        def clear_level():
            level = max(0, min(20, _safe_int(spell_level_var.get(), 0)))
            self.spell_names_by_level_override[level] = []
            refresh_listbox()
            self._refresh_complex_summary("spellList")
            self._refresh_summary()

        ttk.Button(actions, text="Add Spell", command=add_spell).pack(side=tk.LEFT)
        ttk.Button(actions, text="Remove Selected", command=remove_spell).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Clear Level", command=clear_level).pack(side=tk.LEFT)
        ttk.Button(actions, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
        refresh_listbox()

    def _edit_famed_enemies(self):
        if not self.simple_override_vars["FamedEnemyList"].get():
            self.simple_override_vars["FamedEnemyList"].set(True)
            self._on_complex_override_toggle("FamedEnemyList")
        dialog = tk.Toplevel(self)
        dialog.title("Edit Famed Enemies")
        dialog.geometry("720x420")
        listbox = tk.Listbox(dialog, height=12)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        def refresh_listbox():
            listbox.delete(0, tk.END)
            for character_id in self.famed_enemy_character_ids_override:
                listbox.insert(tk.END, self._character_display_label(character_id))

        actions = ttk.Frame(dialog)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))

        def add_enemy():
            def _on_select(character_id: str):
                if character_id not in self.famed_enemy_character_ids_override:
                    self.famed_enemy_character_ids_override.append(character_id)
                    refresh_listbox()
                    self._refresh_complex_summary("FamedEnemyList")
                    self._refresh_summary()

            CharacterSelectDialog(dialog, self.app.character_service, _on_select)

        def remove_enemy():
            selection = listbox.curselection()
            if not selection:
                return
            index = int(selection[0])
            if 0 <= index < len(self.famed_enemy_character_ids_override):
                self.famed_enemy_character_ids_override.pop(index)
                refresh_listbox()
                self._refresh_complex_summary("FamedEnemyList")
                self._refresh_summary()

        ttk.Button(actions, text="Add Enemy", command=add_enemy).pack(side=tk.LEFT)
        ttk.Button(actions, text="Remove Selected", command=remove_enemy).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
        refresh_listbox()

    def _edit_gear_options(self):
        if not self.simple_override_vars["gearOptions"].get():
            self.simple_override_vars["gearOptions"].set(True)
            self._on_complex_override_toggle("gearOptions")
        GearOptionsEditorDialog(self, self.app.item_service, self.gear_options_override, self._on_gear_options_saved)

    def _on_gear_options_saved(self, payload):
        self.gear_options_override = normalize_gear_options_payload(payload)
        self._refresh_complex_summary("gearOptions")
        self._refresh_summary()

    def _build_payload(self) -> dict:
        payload = {"baseRaceId": self.selected_race_id}
        for field_name in ["name", "detailedDescription", "beifDescription", "juvenileNomenclature", "size"]:
            if self.simple_override_vars[field_name].get():
                payload[field_name] = str(self.simple_value_vars[field_name].get() or "").strip()
        if self.simple_override_vars["averageSpecimine"].get():
            payload["averageSpecimineCharacterId"] = str(self.average_specimine_character_id_override or "")
        if self.simple_override_vars["attributeBounds"].get() and self.attribute_bounds_override is not None:
            payload.update(self.attribute_bounds_override)
        if self.simple_override_vars["spellList"].get() and self.spell_names_by_level_override is not None:
            payload["spellList"] = [list(level_entries) for level_entries in self.spell_names_by_level_override]
        if self.simple_override_vars["FamedEnemyList"].get() and self.famed_enemy_character_ids_override is not None:
            payload["famedEnemyCharacterIds"] = list(self.famed_enemy_character_ids_override)
        if self.simple_override_vars["gearOptions"].get() and self.gear_options_override is not None:
            payload["gearOptions"] = normalize_gear_options_payload(self.gear_options_override)
        return payload

    def _save(self):
        if not self.selected_race_id:
            messagebox.showerror("Unit Editor", "Select a base race before saving a unit.")
            return

        payload = self._build_payload()

        try:
            if self.current_unit_id:
                unit = self.app.unit_service.edit_unit_from_patch(self.current_unit_id, payload)
                messagebox.showinfo("Unit Editor", "Unit saved.")
                self.refresh_unit_list(reset_form=False)
                self.pick_var.set(self.app.unit_service.get_unit_label(unit))
                self._load_unit(unit)
            else:
                unit = self.app.unit_service.create_unit_from_dict(payload)
                messagebox.showinfo("Unit Editor", "Unit saved.")
                self.refresh_unit_list(reset_form=False)
                self.pick_var.set(self.app.unit_service.get_unit_label(unit))
                self._load_unit(unit)
        except Exception as exc:
            messagebox.showerror("Unit Editor", f"Failed to save unit: {exc}")
