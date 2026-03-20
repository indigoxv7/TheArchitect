import tkinter as tk
from tkinter import ttk

from src.domain.character_util import Attributes
from src.domain.Race import CreatureSize
from src.tools.admin.shared.gear_options import (
    build_gear_options_summary,
    default_gear_options_payload,
    normalize_gear_options_payload,
)


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


class UnitEditorFrameMixin:
    def _build_override_entry_row(self, field_name: str, label: str):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        override_var = tk.BooleanVar(value=False)
        self.simple_override_vars[field_name] = override_var
        ttk.Checkbutton(
            row,
            text="Override",
            variable=override_var,
            command=lambda name=field_name: self._on_simple_override_toggle(name),
        ).pack(side=tk.LEFT)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        value_var = tk.StringVar()
        self.simple_value_vars[field_name] = value_var
        entry = ttk.Entry(row, textvariable=value_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.simple_widgets[field_name] = entry

    def _build_override_combo_row(self, field_name: str, label: str, values: list[str], default_value: str):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        override_var = tk.BooleanVar(value=False)
        self.simple_override_vars[field_name] = override_var
        ttk.Checkbutton(
            row,
            text="Override",
            variable=override_var,
            command=lambda name=field_name: self._on_simple_override_toggle(name),
        ).pack(side=tk.LEFT)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        value_var = tk.StringVar(value=default_value)
        self.simple_value_vars[field_name] = value_var
        combo = ttk.Combobox(row, state="readonly", values=values, textvariable=value_var)
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.simple_widgets[field_name] = combo

    def _build_average_specimine_row(self):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        override_var = tk.BooleanVar(value=False)
        self.simple_override_vars["averageSpecimine"] = override_var
        ttk.Checkbutton(
            row,
            text="Override",
            variable=override_var,
            command=lambda: self._on_simple_override_toggle("averageSpecimine"),
        ).pack(side=tk.LEFT)
        ttk.Label(row, text="Average Specimine", width=18).pack(side=tk.LEFT)
        value_var = tk.StringVar(value="<None>")
        self.simple_value_vars["averageSpecimine"] = value_var
        entry = ttk.Entry(row, textvariable=value_var, state="readonly")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.simple_widgets["averageSpecimine"] = entry
        self.average_select_button = ttk.Button(row, text="Select", command=self._select_average_specimine)
        self.average_select_button.pack(side=tk.LEFT, padx=4)
        self.average_clear_button = ttk.Button(row, text="Clear", command=self._clear_average_specimine)
        self.average_clear_button.pack(side=tk.LEFT)

    def _build_complex_override_section(self, field_name: str, label: str, edit_command):
        frame = ttk.LabelFrame(self, text=label)
        frame.pack(fill=tk.X, pady=4)
        top = ttk.Frame(frame)
        top.pack(fill=tk.X, padx=6, pady=(6, 2))
        override_var = tk.BooleanVar(value=False)
        self.simple_override_vars[field_name] = override_var
        ttk.Checkbutton(
            top,
            text="Override",
            variable=override_var,
            command=lambda name=field_name: self._on_complex_override_toggle(name),
        ).pack(side=tk.LEFT)
        ttk.Button(top, text=f"Edit {label}", command=edit_command).pack(side=tk.LEFT, padx=6)
        summary_var = tk.StringVar(value="")
        self.summary_vars[field_name] = summary_var
        ttk.Label(frame, textvariable=summary_var, wraplength=820, justify=tk.LEFT).pack(fill=tk.X, padx=6, pady=(0, 6))

    def _get_selected_race(self):
        if not self.selected_race_id:
            return None
        return self.app.race_service.get_race_by_id(self.selected_race_id)

    def _race_label(self, race) -> str:
        return self.app.race_service.get_race_label(race)

    def refresh_race_list(self, reset_selection: bool):
        races = self.app.race_service.list_races()
        labels = [self._race_label(race) for race in races]
        self.race_pick["values"] = labels
        if not labels:
            self.race_var.set("")
            self.selected_race_id = ""
            self.refresh_unit_list(reset_form=True)
            return

        current_race = self._get_selected_race()
        current_label = self._race_label(current_race) if current_race is not None else ""
        if reset_selection or not self.selected_race_id or current_label not in labels:
            self.selected_race_id = races[0].raceId
            self.race_var.set(labels[0])
            self.refresh_unit_list(reset_form=True)
        else:
            self.race_var.set(current_label)
            self.refresh_unit_list(reset_form=False)

    def _on_race_changed(self, _evt=None):
        selected = self.race_var.get().strip()
        if not selected:
            return
        self.selected_race_id = self.app.race_service.parse_race_id_from_label(selected)
        self.refresh_unit_list(reset_form=True)

    def _filtered_units(self):
        query = self.search_var.get().strip().lower()
        results = []
        for unit in self.app.unit_service.list_units(race_id=self.selected_race_id):
            label = self.app.unit_service.get_unit_label(unit)
            if query and query not in label.lower():
                continue
            results.append(unit)
        return results

    def refresh_unit_list(self, reset_form: bool):
        labels = ["<New Unit>"] + [self.app.unit_service.get_unit_label(unit) for unit in self._filtered_units()]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<New Unit>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<New Unit>")

    def _base_simple_value(self, field_name: str):
        race = self._get_selected_race()
        if race is None:
            if field_name == "size":
                return CreatureSize.STANDARD.name
            if field_name == "averageSpecimine":
                return "<None>"
            return ""

        if field_name == "size":
            value = getattr(race, "size", CreatureSize.STANDARD)
            return value.name if hasattr(value, "name") else CreatureSize.STANDARD.name
        if field_name == "averageSpecimine":
            character_id = self.app.race_service.resolve_character_id(getattr(race, "averageSpecimine", None))
            return self._character_display_label(character_id) if character_id else "<None>"
        return str(getattr(race, field_name, "") or "")

    def _base_average_specimine_id(self) -> str:
        race = self._get_selected_race()
        if race is None:
            return ""
        return str(self.app.race_service.resolve_character_id(getattr(race, "averageSpecimine", None)) or "")

    def _base_attribute_bounds(self) -> dict:
        race = self._get_selected_race()
        if race is None:
            attrs = Attributes()
            min_attrs = max_attrs = attrs
        else:
            min_attrs = getattr(race, "minAverageAttributes", Attributes())
            max_attrs = getattr(race, "maxAverageAttributes", Attributes())
        return {
            "minAverageAttributes": {
                "physicalPower": float(getattr(min_attrs, "physicalPower", 5)),
                "physicalStamina": float(getattr(min_attrs, "physicalStamina", 5)),
                "physicalResistance": float(getattr(min_attrs, "physicalResistance", 5)),
                "magicPower": float(getattr(min_attrs, "magicPower", 5)),
                "magicStamina": float(getattr(min_attrs, "magicStamina", 5)),
                "magicResistance": float(getattr(min_attrs, "magicResistance", 5)),
            },
            "maxAverageAttributes": {
                "physicalPower": float(getattr(max_attrs, "physicalPower", 5)),
                "physicalStamina": float(getattr(max_attrs, "physicalStamina", 5)),
                "physicalResistance": float(getattr(max_attrs, "physicalResistance", 5)),
                "magicPower": float(getattr(max_attrs, "magicPower", 5)),
                "magicStamina": float(getattr(max_attrs, "magicStamina", 5)),
                "magicResistance": float(getattr(max_attrs, "magicResistance", 5)),
            },
        }

    def _base_spell_list(self):
        race = self._get_selected_race()
        spell_names_by_level = [[] for _ in range(21)]
        if race is None:
            return spell_names_by_level
        for level, entries in enumerate(getattr(race, "spellList", [])[:21]):
            if not isinstance(entries, list):
                continue
            spell_names_by_level[level] = [
                str(getattr(spell, "name", "") or "").strip()
                for spell in entries
                if str(getattr(spell, "name", "") or "").strip()
            ]
        return spell_names_by_level

    def _base_famed_enemy_ids(self):
        race = self._get_selected_race()
        if race is None:
            return []
        character_ids = []
        for character in getattr(race, "FamedEnemyList", []) or []:
            character_id = self.app.race_service.resolve_character_id(character)
            if character_id:
                character_ids.append(character_id)
        return character_ids

    def _base_gear_options(self):
        race = self._get_selected_race()
        if race is None or getattr(race, "gearOptions", None) is None:
            return default_gear_options_payload()
        return normalize_gear_options_payload(race.gearOptions.to_dict())

    def _clear_form(self):
        self.current_unit_id = None
        self.average_specimine_character_id_override = None
        self.attribute_bounds_override = None
        self.spell_names_by_level_override = None
        self.famed_enemy_character_ids_override = None
        self.gear_options_override = None

        for field_name, var in self.simple_override_vars.items():
            var.set(False)

        for field_name, var in self.simple_value_vars.items():
            var.set(self._base_simple_value(field_name))

        self._refresh_all_override_states()
        self._refresh_summary()

    def _character_display_label(self, character_id: str) -> str:
        if not character_id:
            return "<None>"
        character = self.app.character_service.get_character(character_id)
        if character is None:
            return f"Unknown [{character_id}]"
        name = str(getattr(character, "name", "") or "").strip() or "<Unnamed>"
        return f"{name} [{character_id}]"

    def _spell_summary_text(self, spell_names_by_level) -> str:
        parts = []
        for level, entries in enumerate(spell_names_by_level[:21]):
            if entries:
                parts.append(f"L{level}: {', '.join(entries)}")
        return "; ".join(parts) if parts else "No spells"

    def _famed_summary_text(self, character_ids: list[str]) -> str:
        if not character_ids:
            return "No famed enemies"
        return ", ".join(self._character_display_label(character_id) for character_id in character_ids)

    def _refresh_complex_summary(self, field_name: str):
        enabled = bool(self.simple_override_vars[field_name].get())
        if field_name == "attributeBounds":
            source = (
                self.attribute_bounds_override
                if enabled and self.attribute_bounds_override is not None
                else self._base_attribute_bounds()
            )
            min_attrs = source.get("minAverageAttributes", {})
            max_attrs = source.get("maxAverageAttributes", {})
            text = f"Min: {min_attrs} | Max: {max_attrs}"
        elif field_name == "spellList":
            source = (
                self.spell_names_by_level_override
                if enabled and self.spell_names_by_level_override is not None
                else self._base_spell_list()
            )
            text = self._spell_summary_text(source)
        elif field_name == "FamedEnemyList":
            source = (
                self.famed_enemy_character_ids_override
                if enabled and self.famed_enemy_character_ids_override is not None
                else self._base_famed_enemy_ids()
            )
            text = self._famed_summary_text(source)
        else:
            source = (
                self.gear_options_override
                if enabled and self.gear_options_override is not None
                else self._base_gear_options()
            )
            text = build_gear_options_summary(self.app.item_service, source)
        prefix = "Override" if enabled else "Using race default"
        self.summary_vars[field_name].set(f"{prefix}: {text}")

    def _refresh_summary(self):
        race = self._get_selected_race()
        base_name = str(getattr(race, "name", "<No Race Selected>") or "<No Race Selected>")
        effective_name = (
            self.simple_value_vars["name"].get().strip()
            if self.simple_override_vars["name"].get()
            else self._base_simple_value("name")
        )
        lines = [
            f"Base Race: {base_name} [{self.selected_race_id or 'None'}]",
            f"Effective Name: {effective_name or '<Unnamed Unit>'}",
            f"Unit ID: {self.current_unit_id or '<Unsaved>'}",
            f"Description: {self.simple_value_vars['detailedDescription'].get().strip() if self.simple_override_vars['detailedDescription'].get() else self._base_simple_value('detailedDescription')}",
            f"Brief Description: {self.simple_value_vars['beifDescription'].get().strip() if self.simple_override_vars['beifDescription'].get() else self._base_simple_value('beifDescription')}",
            f"Juvenile Nomenclature: {self.simple_value_vars['juvenileNomenclature'].get().strip() if self.simple_override_vars['juvenileNomenclature'].get() else self._base_simple_value('juvenileNomenclature')}",
            f"Size: {self.simple_value_vars['size'].get().strip() if self.simple_override_vars['size'].get() else self._base_simple_value('size')}",
            f"Average Specimine: {self.simple_value_vars['averageSpecimine'].get().strip() if self.simple_override_vars['averageSpecimine'].get() else self._base_simple_value('averageSpecimine')}",
            "",
            self.summary_vars["attributeBounds"].get(),
            "",
            self.summary_vars["spellList"].get(),
            "",
            self.summary_vars["FamedEnemyList"].get(),
            "",
            self.summary_vars["gearOptions"].get(),
        ]
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, "\n".join(lines))
