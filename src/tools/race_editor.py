import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.CharacterUtil import Attributes
from src.domain.Race import CreatureSize
from src.tools.catalog_selectors import CharacterSelectDialog, SpellSelectDialog
from src.tools.gear_options_editor import (
    build_gear_options_summary,
    default_gear_options_payload,
    normalize_gear_options_payload,
    GearOptionsEditorDialog,
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


class RaceEditorFrame(ttk.Frame):
    ATTRIBUTE_FIELDS = [
        ("physicalPower", "Physical Power"),
        ("physicalStamina", "Physical Stamina"),
        ("physicalResistance", "Physical Resistance"),
        ("magicPower", "Magic Power"),
        ("magicStamina", "Magic Stamina"),
        ("magicResistance", "Magic Resistance"),
    ]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_race_id = None
        self.average_specimine_character_id = ""
        self.famed_enemy_character_ids = []
        self.spell_names_by_level = [[] for _ in range(21)]
        self.gear_options_draft = default_gear_options_payload()

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Race Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=20).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_race_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Race", width=20).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Race>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.vars = {
            "name": tk.StringVar(),
            "detailedDescription": tk.StringVar(),
            "beifDescription": tk.StringVar(),
            "juvenileNomenclature": tk.StringVar(value="young"),
            "size": tk.StringVar(value=CreatureSize.STANDARD.name),
            "averageSpecimine": tk.StringVar(value="<None>"),
            "spellLevel": tk.StringVar(value="0"),
        }

        self._row_entry("Name", self.vars["name"])
        self._row_entry("Detailed Description", self.vars["detailedDescription"])
        self._row_entry("Brief Description", self.vars["beifDescription"])
        self._row_entry("Juvenile Nomenclature", self.vars["juvenileNomenclature"])
        self._row_combo("Size", self.vars["size"], [entry.name for entry in CreatureSize])

        avg_row = ttk.Frame(self)
        avg_row.pack(fill=tk.X, pady=2)
        ttk.Label(avg_row, text="Average Specimine", width=20).pack(side=tk.LEFT)
        ttk.Entry(avg_row, textvariable=self.vars["averageSpecimine"], state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(avg_row, text="Select", command=self._select_average_specimine).pack(side=tk.LEFT, padx=4)
        ttk.Button(avg_row, text="Clear", command=self._clear_average_specimine).pack(side=tk.LEFT)

        attr_frame = ttk.Frame(self)
        attr_frame.pack(fill=tk.BOTH, expand=False, pady=6)

        min_frame = ttk.LabelFrame(attr_frame, text="Min Average Attributes")
        min_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        max_frame = ttk.LabelFrame(attr_frame, text="Max Average Attributes")
        max_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        self.min_attr_vars = {}
        self.max_attr_vars = {}
        for key, label in self.ATTRIBUTE_FIELDS:
            min_row = ttk.Frame(min_frame)
            min_row.pack(fill=tk.X, padx=6, pady=2)
            ttk.Label(min_row, text=label, width=18).pack(side=tk.LEFT)
            min_var = tk.StringVar(value="5")
            self.min_attr_vars[key] = min_var
            ttk.Entry(min_row, textvariable=min_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

            max_row = ttk.Frame(max_frame)
            max_row.pack(fill=tk.X, padx=6, pady=2)
            ttk.Label(max_row, text=label, width=18).pack(side=tk.LEFT)
            max_var = tk.StringVar(value="5")
            self.max_attr_vars[key] = max_var
            ttk.Entry(max_row, textvariable=max_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        gear_frame = ttk.LabelFrame(self, text="Gear Options")
        gear_frame.pack(fill=tk.BOTH, expand=False, pady=6)
        self.gear_summary = tk.Text(gear_frame, height=10, wrap=tk.WORD)
        self.gear_summary.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        gear_actions = ttk.Frame(gear_frame)
        gear_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(gear_actions, text="Edit Gear Options", command=self._edit_gear_options).pack(side=tk.LEFT)

        spell_frame = ttk.LabelFrame(self, text="Spell List By Level")
        spell_frame.pack(fill=tk.BOTH, expand=False, pady=6)

        spell_level_row = ttk.Frame(spell_frame)
        spell_level_row.pack(fill=tk.X, padx=6, pady=(6, 2))
        ttk.Label(spell_level_row, text="Editing Level", width=16).pack(side=tk.LEFT)
        level_values = [str(i) for i in range(21)]
        spell_level_combo = ttk.Combobox(
            spell_level_row,
            state="readonly",
            values=level_values,
            textvariable=self.vars["spellLevel"],
        )
        spell_level_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        spell_level_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_spell_level_listbox())

        self.spell_listbox = tk.Listbox(spell_frame, height=7)
        self.spell_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        spell_actions = ttk.Frame(spell_frame)
        spell_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(spell_actions, text="Add Spell", command=self._add_spell_to_level).pack(side=tk.LEFT)
        ttk.Button(spell_actions, text="Remove Selected", command=self._remove_selected_spell_from_level).pack(side=tk.LEFT, padx=6)
        ttk.Button(spell_actions, text="Clear Level", command=self._clear_current_spell_level).pack(side=tk.LEFT)

        famed_frame = ttk.LabelFrame(self, text="Famed Enemy List")
        famed_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.famed_listbox = tk.Listbox(famed_frame, height=7)
        self.famed_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        famed_actions = ttk.Frame(famed_frame)
        famed_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(famed_actions, text="Add Enemy", command=self._add_famed_enemy).pack(side=tk.LEFT)
        ttk.Button(famed_actions, text="Remove Selected", command=self._remove_selected_famed_enemy).pack(side=tk.LEFT, padx=6)

        ttk.Button(self, text="Save Race", command=self._save).pack(fill=tk.X, pady=8)

        self._clear_form()

    def _row_entry(self, label, var):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _row_combo(self, label, var, values):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
        ttk.Combobox(row, state="readonly", values=values, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _clear_form(self):
        self.current_race_id = None
        self.average_specimine_character_id = ""
        self.famed_enemy_character_ids = []
        self.spell_names_by_level = [[] for _ in range(21)]
        self.gear_options_draft = default_gear_options_payload()

        self.vars["name"].set("")
        self.vars["detailedDescription"].set("")
        self.vars["beifDescription"].set("")
        self.vars["juvenileNomenclature"].set("young")
        self.vars["size"].set(CreatureSize.STANDARD.name)
        self.vars["averageSpecimine"].set("<None>")
        self.vars["spellLevel"].set("0")

        for key, _ in self.ATTRIBUTE_FIELDS:
            self.min_attr_vars[key].set("5")
            self.max_attr_vars[key].set("5")

        self._refresh_spell_level_listbox()
        self._refresh_famed_enemy_listbox()
        self._refresh_gear_summary()

    def _filtered_races(self):
        query = self.search_var.get().strip().lower()
        results = []
        for race in self.app.race_service.list_races():
            label = self.app.race_service.get_race_label(race)
            if query and query not in label.lower():
                continue
            results.append(race)
        return results

    def refresh_race_list(self, reset_form: bool):
        labels = ["<New Race>"] + [self.app.race_service.get_race_label(race) for race in self._filtered_races()]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<New Race>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<New Race>")

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Race>":
            self._clear_form()
            return

        race_id = self.app.race_service.parse_race_id_from_label(selected)
        race = self.app.race_service.get_race_by_id(race_id)
        if race is None:
            return

        self.current_race_id = race.raceId
        self.vars["name"].set(str(race.name or ""))
        self.vars["detailedDescription"].set(str(race.detailedDescription or ""))
        self.vars["beifDescription"].set(str(race.beifDescription or ""))
        self.vars["juvenileNomenclature"].set(str(race.juvenileNomenclature or "young"))
        self.vars["size"].set(race.size.name if hasattr(race.size, "name") else CreatureSize.STANDARD.name)

        average_id = self.app.race_service.resolve_character_id(getattr(race, "averageSpecimine", None))
        self.average_specimine_character_id = str(average_id or "")
        self.vars["averageSpecimine"].set(self._character_display_label(self.average_specimine_character_id) if self.average_specimine_character_id else "<None>")

        min_attrs = getattr(race, "minAverageAttributes", Attributes())
        max_attrs = getattr(race, "maxAverageAttributes", Attributes())
        for key, _label in self.ATTRIBUTE_FIELDS:
            self.min_attr_vars[key].set(str(getattr(min_attrs, key, 5)))
            self.max_attr_vars[key].set(str(getattr(max_attrs, key, 5)))

        self.spell_names_by_level = [[] for _ in range(21)]
        for level, entries in enumerate(getattr(race, "spellList", [])[:21]):
            if not isinstance(entries, list):
                continue
            names = []
            for spell in entries:
                name = str(getattr(spell, "name", "") or "").strip()
                if name:
                    names.append(name)
            self.spell_names_by_level[level] = names

        self.famed_enemy_character_ids = []
        for character in getattr(race, "FamedEnemyList", []) or []:
            character_id = self.app.race_service.resolve_character_id(character)
            if character_id:
                self.famed_enemy_character_ids.append(character_id)

        gear_options = getattr(race, "gearOptions", None)
        if gear_options is not None:
            self.gear_options_draft = normalize_gear_options_payload(gear_options.to_dict())
        else:
            self.gear_options_draft = default_gear_options_payload()

        self._refresh_spell_level_listbox()
        self._refresh_famed_enemy_listbox()
        self._refresh_gear_summary()

    def _character_display_label(self, character_id: str) -> str:
        character = self.app.character_service.get_character(character_id)
        if character is None:
            return f"Unknown [{character_id}]"
        name = str(getattr(character, "name", "") or "").strip() or "<Unnamed>"
        return f"{name} [{character_id}]"

    def _select_average_specimine(self):
        def _on_select(character_id: str):
            self.average_specimine_character_id = character_id
            self.vars["averageSpecimine"].set(self._character_display_label(character_id))

        CharacterSelectDialog(self, self.app.character_service, _on_select)

    def _clear_average_specimine(self):
        self.average_specimine_character_id = ""
        self.vars["averageSpecimine"].set("<None>")

    def _edit_gear_options(self):
        GearOptionsEditorDialog(self, self.app.item_service, self.gear_options_draft, self._on_gear_options_saved)

    def _on_gear_options_saved(self, payload):
        self.gear_options_draft = normalize_gear_options_payload(payload)
        self._refresh_gear_summary()

    def _refresh_gear_summary(self):
        self.gear_summary.delete("1.0", tk.END)
        self.gear_summary.insert(tk.END, build_gear_options_summary(self.app.item_service, self.gear_options_draft))

    def _current_spell_level_index(self) -> int:
        return max(0, min(20, _safe_int(self.vars["spellLevel"].get(), 0)))

    def _refresh_spell_level_listbox(self):
        level = self._current_spell_level_index()
        self.spell_listbox.delete(0, tk.END)
        for spell_name in self.spell_names_by_level[level]:
            self.spell_listbox.insert(tk.END, spell_name)

    def _add_spell_to_level(self):
        level = self._current_spell_level_index()

        def _on_select(spell_name: str):
            if spell_name in self.spell_names_by_level[level]:
                messagebox.showinfo("Race Editor", f"Spell '{spell_name}' already exists at level {level}.")
                return
            self.spell_names_by_level[level].append(spell_name)
            self._refresh_spell_level_listbox()

        SpellSelectDialog(self, self.app.spell_service, _on_select)

    def _remove_selected_spell_from_level(self):
        level = self._current_spell_level_index()
        selection = self.spell_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.spell_names_by_level[level]):
            return
        self.spell_names_by_level[level].pop(index)
        self._refresh_spell_level_listbox()

    def _clear_current_spell_level(self):
        level = self._current_spell_level_index()
        self.spell_names_by_level[level] = []
        self._refresh_spell_level_listbox()

    def _refresh_famed_enemy_listbox(self):
        self.famed_listbox.delete(0, tk.END)
        for character_id in self.famed_enemy_character_ids:
            self.famed_listbox.insert(tk.END, self._character_display_label(character_id))

    def _add_famed_enemy(self):
        def _on_select(character_id: str):
            if character_id in self.famed_enemy_character_ids:
                messagebox.showinfo("Race Editor", "That character is already in Famed Enemies.")
                return
            self.famed_enemy_character_ids.append(character_id)
            self._refresh_famed_enemy_listbox()

        CharacterSelectDialog(self, self.app.character_service, _on_select)

    def _remove_selected_famed_enemy(self):
        selection = self.famed_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.famed_enemy_character_ids):
            return
        self.famed_enemy_character_ids.pop(index)
        self._refresh_famed_enemy_listbox()

    def _collect_attributes(self, vars_by_key: dict) -> dict:
        return {
            "physicalPower": _safe_float(vars_by_key["physicalPower"].get(), 5.0),
            "physicalStamina": _safe_float(vars_by_key["physicalStamina"].get(), 5.0),
            "physicalResistance": _safe_float(vars_by_key["physicalResistance"].get(), 5.0),
            "magicPower": _safe_float(vars_by_key["magicPower"].get(), 5.0),
            "magicStamina": _safe_float(vars_by_key["magicStamina"].get(), 5.0),
            "magicResistance": _safe_float(vars_by_key["magicResistance"].get(), 5.0),
        }

    def _build_payload(self) -> dict:
        spell_list_payload = [list(level_entries) for level_entries in self.spell_names_by_level]

        return {
            "name": str(self.vars["name"].get() or "").strip(),
            "detailedDescription": str(self.vars["detailedDescription"].get() or "").strip(),
            "beifDescription": str(self.vars["beifDescription"].get() or "").strip(),
            "juvenileNomenclature": str(self.vars["juvenileNomenclature"].get() or "young").strip() or "young",
            "size": str(self.vars["size"].get() or CreatureSize.STANDARD.name).strip() or CreatureSize.STANDARD.name,
            "averageSpecimineCharacterId": self.average_specimine_character_id,
            "maxAverageAttributes": self._collect_attributes(self.max_attr_vars),
            "minAverageAttributes": self._collect_attributes(self.min_attr_vars),
            "spellList": spell_list_payload,
            "famedEnemyCharacterIds": list(self.famed_enemy_character_ids),
            "gearOptions": normalize_gear_options_payload(self.gear_options_draft),
        }

    def _save(self):
        payload = self._build_payload()
        if not payload["name"]:
            messagebox.showerror("Race Editor", "Race name is required.")
            return

        try:
            if self.current_race_id:
                self.app.race_service.edit_race_from_patch(self.current_race_id, payload)
            else:
                self.app.race_service.create_race_from_dict(payload)
            messagebox.showinfo("Race Editor", "Race saved.")
            self.refresh_race_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Race Editor", f"Failed to save race: {exc}")
