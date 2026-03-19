from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Any

from src.tools.admin.shared.bonus_payloads import _achievement_object_to_entry


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _normalize_exclude_ids(exclude_ids) -> set[str]:
    return {str(entry or "").strip() for entry in (exclude_ids or []) if str(entry or "").strip()}


@dataclass(frozen=True)
class _PickerOption:
    payload: Any
    label: str
    search_text: str


class _SearchPickerDialog(tk.Toplevel):
    dialog_title = "Select"
    dialog_size = "760x500"
    confirm_label = "Select"
    missing_selection_message = "Select an option."

    def __init__(self, parent, on_select):
        super().__init__(parent)
        self.title(self.dialog_title)
        self.geometry(self.dialog_size)
        self.on_select = on_select
        self.filtered: list[_PickerOption] = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _event: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.listbox.bind("<Double-Button-1>", lambda _event: self._confirm_selection())

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text=self.confirm_label, command=self._confirm_selection).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _build_options(self) -> list[_PickerOption]:
        raise NotImplementedError

    def _deliver_selection(self, option: _PickerOption):
        self.on_select(option.payload)

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for option in self._build_options():
            haystack = option.search_text.lower() if option.search_text else option.label.lower()
            if query and query not in haystack and query not in option.label.lower():
                continue
            self.filtered.append(option)
            self.listbox.insert(tk.END, option.label)

    def _confirm_selection(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror(self.dialog_title, self.missing_selection_message)
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        self._deliver_selection(self.filtered[index])
        self.destroy()


class CharacterSelectDialog(_SearchPickerDialog):
    dialog_title = "Select Character"
    missing_selection_message = "Select a character."

    def __init__(self, parent, character_service, on_select):
        self.character_service = character_service
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        return [
            _PickerOption(
                payload=character_id,
                label=f"{getattr(character, 'name', '')} [{character_id}] (Lv {int(_safe_int(getattr(character, 'level', 0), 0))})",
                search_text=f"{getattr(character, 'name', '')} {character_id}",
            )
            for character_id, character in self.character_service.list_characters()
        ]


class SpellSelectDialog(_SearchPickerDialog):
    dialog_title = "Select Spell"
    missing_selection_message = "Select a spell."

    def __init__(self, parent, spell_service, on_select):
        self.spell_service = spell_service
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        options: list[_PickerOption] = []
        for spell in self.spell_service.list_spells():
            affinity = spell.affinity.value if hasattr(spell.affinity, "value") else spell.affinity
            label = f"{spell.name} (Lv {spell.level}, {affinity})"
            options.append(_PickerOption(payload=spell.name, label=label, search_text=label))
        return options


class ItemSelectDialog(_SearchPickerDialog):
    dialog_title = "Select Item"
    missing_selection_message = "Select an item."

    def __init__(self, parent, item_service, on_select, allowed_slots=None, item_filter=None):
        self.item_service = item_service
        self.allowed_slots = set(allowed_slots or []) if allowed_slots is not None else None
        self.item_filter = item_filter if callable(item_filter) else None
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        options: list[_PickerOption] = []
        for item in self.item_service.list_items():
            if self.allowed_slots is not None and not any(item.can_equip_in(slot) for slot in self.allowed_slots):
                continue
            if self.item_filter is not None and not self.item_filter(item):
                continue
            label = self.item_service.get_item_label(item)
            options.append(_PickerOption(payload=item.itemId, label=label, search_text=label))
        return options


class UnitSelectDialog(_SearchPickerDialog):
    dialog_title = "Select Unit"
    missing_selection_message = "Select a unit."

    def __init__(self, parent, unit_service, on_select, exclude_ids=None):
        self.unit_service = unit_service
        self.exclude_ids = _normalize_exclude_ids(exclude_ids)
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        return [
            _PickerOption(
                payload=unit.unitId,
                label=self.unit_service.get_unit_label(unit),
                search_text=self.unit_service.get_unit_label(unit),
            )
            for unit in self.unit_service.list_units()
            if unit.unitId not in self.exclude_ids
        ]


class AllegianceSelectDialog(_SearchPickerDialog):
    dialog_title = "Select Allegiance"
    missing_selection_message = "Select an allegiance."

    def __init__(self, parent, allegiance_service, on_select, exclude_ids=None):
        self.allegiance_service = allegiance_service
        self.exclude_ids = _normalize_exclude_ids(exclude_ids)
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        return [
            _PickerOption(
                payload=allegiance.allegianceId,
                label=self.allegiance_service.get_allegiance_label(allegiance),
                search_text=self.allegiance_service.get_allegiance_label(allegiance),
            )
            for allegiance in self.allegiance_service.list_allegiances()
            if allegiance.allegianceId not in self.exclude_ids
        ]


class MissionSelectDialog(_SearchPickerDialog):
    dialog_title = "Select Mission"
    missing_selection_message = "Select a mission."

    def __init__(self, parent, mission_service, on_select, exclude_ids=None):
        self.mission_service = mission_service
        self.exclude_ids = _normalize_exclude_ids(exclude_ids)
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        return [
            _PickerOption(
                payload=mission.missionId,
                label=self.mission_service.get_mission_label(mission),
                search_text=self.mission_service.get_mission_label(mission),
            )
            for mission in self.mission_service.list_missions()
            if mission.missionId not in self.exclude_ids
        ]


class EffectSelectDialog(_SearchPickerDialog):
    dialog_title = "Select Effect"
    missing_selection_message = "Select an effect."

    def __init__(self, parent, environment_service, on_select, exclude_ids=None):
        self.environment_service = environment_service
        self.exclude_ids = _normalize_exclude_ids(exclude_ids)
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        return [
            _PickerOption(
                payload=effect.effectId,
                label=self.environment_service.get_effect_label(effect),
                search_text=self.environment_service.get_effect_label(effect),
            )
            for effect in self.environment_service.list_effects()
            if effect.effectId not in self.exclude_ids
        ]


class TerrainSelectDialog(_SearchPickerDialog):
    dialog_title = "Select Terrain"
    missing_selection_message = "Select a terrain."

    def __init__(self, parent, environment_service, on_select, exclude_ids=None):
        self.environment_service = environment_service
        self.exclude_ids = _normalize_exclude_ids(exclude_ids)
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        return [
            _PickerOption(
                payload=terrain.terrainId,
                label=self.environment_service.get_terrain_label(terrain),
                search_text=self.environment_service.get_terrain_label(terrain),
            )
            for terrain in self.environment_service.list_terrains()
            if terrain.terrainId not in self.exclude_ids
        ]


class ClimateSelectDialog(_SearchPickerDialog):
    dialog_title = "Select Climate"
    missing_selection_message = "Select a climate."

    def __init__(self, parent, environment_service, on_select, exclude_ids=None):
        self.environment_service = environment_service
        self.exclude_ids = _normalize_exclude_ids(exclude_ids)
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        return [
            _PickerOption(
                payload=climate.climateId,
                label=self.environment_service.get_climate_label(climate),
                search_text=self.environment_service.get_climate_label(climate),
            )
            for climate in self.environment_service.list_climates()
            if climate.climateId not in self.exclude_ids
        ]


class AchievementPickerDialog(_SearchPickerDialog):
    dialog_title = "Add Achievement"
    confirm_label = "Add Selected"
    missing_selection_message = "Select an achievement to add."

    def __init__(self, parent, achievement_service, on_select):
        self.achievement_service = achievement_service
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        options: list[_PickerOption] = []
        for achievement in self.achievement_service.list_achievements():
            name = str(getattr(achievement, "name", "") or "")
            title = str(getattr(achievement, "title", "") or "")
            description = str(getattr(achievement, "description", "") or "")
            label = f"{name} ({title})" if title else name
            if description:
                label += f" - {description[:80]}"
            options.append(_PickerOption(payload=achievement, label=label, search_text=f"{name} {title} {description}"))
        return options

    def _deliver_selection(self, option: _PickerOption):
        self.on_select(_achievement_object_to_entry(option.payload))


class RacePickerDialog(_SearchPickerDialog):
    dialog_title = "Select Race"
    missing_selection_message = "Select a race."

    def __init__(self, parent, race_service, on_select):
        self.race_service = race_service
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        return [
            _PickerOption(
                payload=race.raceId,
                label=self.race_service.get_race_label(race),
                search_text=self.race_service.get_race_label(race),
            )
            for race in self.race_service.list_races()
        ]


class CharacterPickerDialog(CharacterSelectDialog):
    dialog_title = "Add Character"
    confirm_label = "Add Selected"
    missing_selection_message = "Select a character to add."


class ItemPickerDialog(_SearchPickerDialog):
    dialog_title = "Add Inventory Item"
    confirm_label = "Add Selected"
    missing_selection_message = "Select an item to add."

    def __init__(self, parent, item_service, on_select):
        self.item_service = item_service
        super().__init__(parent, on_select)

    def _build_options(self) -> list[_PickerOption]:
        return [
            _PickerOption(
                payload=item.itemId,
                label=self.item_service.get_item_label(item),
                search_text=self.item_service.get_item_label(item),
            )
            for item in self.item_service.list_items()
        ]
