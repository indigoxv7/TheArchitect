import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Mission import MissionObjective, MissionObjectiveType
from src.tools.catalog_selectors import AllegianceSelectDialog, ItemSelectDialog, UnitSelectDialog


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


def _objective_description(payload):
    if not isinstance(payload, dict) or not payload:
        return "<No Objective>"
    try:
        return MissionObjective.from_dict(payload).describe()
    except Exception:
        return "<Invalid Objective>"


class MissionUnitOptionDialog(tk.Toplevel):
    def __init__(self, parent, app, initial_payload, on_save, exclude_unit_ids=None):
        super().__init__(parent)
        self.title("Mission Unit Option")
        self.resizable(False, False)
        self.app = app
        self.on_save = on_save
        self.exclude_unit_ids = {
            str(entry or "").strip() for entry in (exclude_unit_ids or []) if str(entry or "").strip()
        }
        initial = initial_payload or {}
        self.unit_id = str(initial.get("unitId", "") or "").strip()
        self.unit_label_var = tk.StringVar(value=self._unit_label(self.unit_id))
        self.capacity_min_var = tk.StringVar(value="" if initial.get("capacityMin") is None else str(initial.get("capacityMin")))
        self.capacity_max_var = tk.StringVar(value="" if initial.get("capacityMax") is None else str(initial.get("capacityMax")))
        self.elite_chance_var = tk.StringVar(value=str(float(initial.get("eliteChance", 0.0) or 0.0)))
        self.is_boss_var = tk.BooleanVar(value=bool(initial.get("isBoss", False)))

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)
        self._selector_row(container, "Unit", self.unit_label_var, self._select_unit)
        self._entry_row(container, "Capacity Min", self.capacity_min_var)
        self._entry_row(container, "Capacity Max", self.capacity_max_var)
        self._entry_row(container, "Elite Chance", self.elite_chance_var)

        boss_row = ttk.Frame(container)
        boss_row.pack(fill=tk.X, pady=2)
        ttk.Label(boss_row, text="Is Boss", width=18).pack(side=tk.LEFT)
        ttk.Checkbutton(boss_row, variable=self.is_boss_var).pack(side=tk.LEFT)

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self.transient(parent)
        self.grab_set()

    def _entry_row(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _selector_row(self, parent, label, var, callback):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Select", command=callback).pack(side=tk.LEFT, padx=(6, 0))

    def _unit_label(self, unit_id):
        if not unit_id:
            return "<None>"
        unit = self.app.unit_service.get_unit_by_id(unit_id)
        if unit is None:
            return f"Unknown [{unit_id}]"
        return self.app.unit_service.get_unit_label(unit)

    def _select_unit(self):
        exclude_ids = set(self.exclude_unit_ids)
        if self.unit_id:
            exclude_ids.discard(self.unit_id)

        def _on_select(unit_id):
            self.unit_id = unit_id
            self.unit_label_var.set(self._unit_label(unit_id))

        UnitSelectDialog(self, self.app.unit_service, _on_select, exclude_ids=exclude_ids)

    def _save(self):
        if not self.unit_id:
            messagebox.showerror("Mission Unit Option", "Select a unit.")
            return
        capacity_min = self.capacity_min_var.get().strip()
        capacity_max = self.capacity_max_var.get().strip()
        try:
            capacity_min_value = None if capacity_min == "" else int(capacity_min)
            capacity_max_value = None if capacity_max == "" else int(capacity_max)
        except Exception:
            messagebox.showerror("Mission Unit Option", "Capacity min/max must be integers or blank.")
            return
        elite_chance = _safe_float(self.elite_chance_var.get().strip() or 0.0, 0.0)
        if capacity_min_value is not None and capacity_min_value < 0:
            messagebox.showerror("Mission Unit Option", "Capacity Min cannot be negative.")
            return
        if capacity_max_value is not None and capacity_max_value < 0:
            messagebox.showerror("Mission Unit Option", "Capacity Max cannot be negative.")
            return
        if capacity_min_value is not None and capacity_max_value is not None and capacity_min_value > capacity_max_value:
            messagebox.showerror("Mission Unit Option", "Capacity Min cannot exceed Capacity Max.")
            return
        if elite_chance < 0.0 or elite_chance > 1.0:
            messagebox.showerror("Mission Unit Option", "Elite Chance must be between 0.0 and 1.0.")
            return
        self.on_save(
            {
                "unitId": self.unit_id,
                "capacityMin": capacity_min_value,
                "capacityMax": capacity_max_value,
                "eliteChance": elite_chance,
                "isBoss": bool(self.is_boss_var.get()),
            }
        )
        self.destroy()

class MissionObjectiveDialog(tk.Toplevel):
    TYPE_VALUES = [entry.value for entry in MissionObjectiveType]

    def __init__(self, parent, app, initial_payload, on_save):
        super().__init__(parent)
        self.title("Mission Objective")
        self.resizable(False, False)
        self.app = app
        self.on_save = on_save
        initial = initial_payload or {"objectiveType": MissionObjectiveType.ELIMINATION.name}

        self.required_item_id = str(initial.get("requiredItemId", "") or "").strip()
        self.target_allegiance_id = str(initial.get("targetAllegianceId", "") or "").strip()
        self.escort_unit_id = str(initial.get("escortUnitId", "") or "").strip()

        objective_type_name = str(initial.get("objectiveType", MissionObjectiveType.ELIMINATION.name) or MissionObjectiveType.ELIMINATION.name)
        objective_type = MissionObjectiveType[objective_type_name] if objective_type_name in MissionObjectiveType.__members__ else MissionObjectiveType.ELIMINATION
        self.objective_type_var = tk.StringVar(value=objective_type.value)
        self.elimination_fraction_var = tk.StringVar(value=str(float(initial.get("requiredEliminationFraction", 1.0) or 1.0)))
        self.bosses_defeated_var = tk.StringVar(value=str(_safe_int(initial.get("requiredBossesDefeated", 1), 1)))
        self.allies_remaining_fraction_var = tk.StringVar(value=str(float(initial.get("requiredAlliesRemainingFraction", 1.0) or 1.0)))
        self.required_packages_var = tk.StringVar(value=str(_safe_int(initial.get("requiredPackagesDelivered", 1), 1)))
        self.survival_hours_var = tk.StringVar(value=str(float(initial.get("requiredHoursSurvived", 1.0) or 1.0)))
        self.rescue_allies_var = tk.StringVar(value=str(_safe_int(initial.get("requiredAlliesEscaped", 1), 1)))
        self.rescue_distance_var = tk.StringVar(value=str(float(initial.get("requiredEscapeDistance", 0.0) or 0.0)))
        self.scavenge_resources_var = tk.StringVar(value=str(_safe_int(initial.get("requiredBasicResources", 1), 1)))
        self.recruit_units_var = tk.StringVar(value=str(_safe_int(initial.get("requiredUnitsRecruited", 1), 1)))
        self.item_label_var = tk.StringVar(value=self._item_label(self.required_item_id))
        self.allegiance_label_var = tk.StringVar(value=self._allegiance_label(self.target_allegiance_id))
        self.escort_label_var = tk.StringVar(value=self._unit_label(self.escort_unit_id))

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)
        type_row = ttk.Frame(container)
        type_row.pack(fill=tk.X, pady=2)
        ttk.Label(type_row, text="Objective Type", width=18).pack(side=tk.LEFT)
        ttk.Combobox(type_row, state="readonly", textvariable=self.objective_type_var, values=self.TYPE_VALUES).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.frames = {}
        for objective_type in MissionObjectiveType:
            frame = ttk.LabelFrame(container, text=objective_type.value)
            self.frames[objective_type.value] = frame
        self._entry_row(self.frames[MissionObjectiveType.ELIMINATION.value], "Enemy Fraction", self.elimination_fraction_var)
        self._entry_row(self.frames[MissionObjectiveType.ASSASSINATION.value], "Bosses Required", self.bosses_defeated_var)
        self._entry_row(self.frames[MissionObjectiveType.DEFENSE.value], "Allies Remaining Fraction", self.allies_remaining_fraction_var)
        self._selector_row(self.frames[MissionObjectiveType.DELIVERY.value], "Required Item", self.item_label_var, self._select_item)
        self._selector_row(self.frames[MissionObjectiveType.DELIVERY.value], "Target Faction", self.allegiance_label_var, self._select_target_allegiance)
        self._entry_row(self.frames[MissionObjectiveType.DELIVERY.value], "Packages Required", self.required_packages_var)
        self._selector_row(self.frames[MissionObjectiveType.ESCORT.value], "Escort Unit", self.escort_label_var, self._select_escort_unit)
        self._entry_row(self.frames[MissionObjectiveType.SURVIVAL.value], "Hours Required", self.survival_hours_var)
        self._entry_row(self.frames[MissionObjectiveType.RESCUE.value], "Allies Escaped", self.rescue_allies_var)
        self._entry_row(self.frames[MissionObjectiveType.RESCUE.value], "Escape Distance", self.rescue_distance_var)
        self._entry_row(self.frames[MissionObjectiveType.SCAVENGE.value], "Resources Required", self.scavenge_resources_var)
        self._entry_row(self.frames[MissionObjectiveType.RECRUIT.value], "Units Required", self.recruit_units_var)

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self.objective_type_var.trace_add("write", self._refresh_type_ui)
        self._refresh_type_ui()
        self.transient(parent)
        self.grab_set()

    def _entry_row(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _selector_row(self, parent, label, var, callback):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Select", command=callback).pack(side=tk.LEFT, padx=(6, 0))

    def _item_label(self, item_id):
        if not item_id:
            return "<None>"
        item = self.app.item_service.get_item(item_id)
        return self.app.item_service.get_item_label(item) if item is not None else f"Unknown [{item_id}]"

    def _allegiance_label(self, allegiance_id):
        if not allegiance_id:
            return "<None>"
        allegiance = self.app.allegiance_service.get_allegiance_by_id(allegiance_id)
        return self.app.allegiance_service.get_allegiance_label(allegiance) if allegiance is not None else f"Unknown [{allegiance_id}]"

    def _unit_label(self, unit_id):
        if not unit_id:
            return "<None>"
        unit = self.app.unit_service.get_unit_by_id(unit_id)
        return self.app.unit_service.get_unit_label(unit) if unit is not None else f"Unknown [{unit_id}]"

    def _select_item(self):
        ItemSelectDialog(self, self.app.item_service, lambda item_id: (setattr(self, "required_item_id", item_id), self.item_label_var.set(self._item_label(item_id))))

    def _select_target_allegiance(self):
        AllegianceSelectDialog(self, self.app.allegiance_service, lambda allegiance_id: (setattr(self, "target_allegiance_id", allegiance_id), self.allegiance_label_var.set(self._allegiance_label(allegiance_id))))

    def _select_escort_unit(self):
        UnitSelectDialog(self, self.app.unit_service, lambda unit_id: (setattr(self, "escort_unit_id", unit_id), self.escort_label_var.set(self._unit_label(unit_id))))

    def _refresh_type_ui(self, *_args):
        selected = self.objective_type_var.get()
        for objective_type, frame in self.frames.items():
            frame.pack_forget()
            if objective_type == selected:
                frame.pack(fill=tk.X, pady=6)

    def _save(self):
        objective_type = next((entry for entry in MissionObjectiveType if entry.value == self.objective_type_var.get()), MissionObjectiveType.ELIMINATION)
        payload = {"objectiveType": objective_type.name}
        if objective_type == MissionObjectiveType.ELIMINATION:
            payload["requiredEliminationFraction"] = _safe_float(self.elimination_fraction_var.get(), 1.0)
            if not 0.0 <= payload["requiredEliminationFraction"] <= 1.0:
                messagebox.showerror("Mission Objective", "Enemy Fraction must be between 0.0 and 1.0.")
                return
        elif objective_type == MissionObjectiveType.ASSASSINATION:
            payload["requiredBossesDefeated"] = _safe_int(self.bosses_defeated_var.get(), 1)
        elif objective_type == MissionObjectiveType.DEFENSE:
            payload["requiredAlliesRemainingFraction"] = _safe_float(self.allies_remaining_fraction_var.get(), 1.0)
            if not 0.0 <= payload["requiredAlliesRemainingFraction"] <= 1.0:
                messagebox.showerror("Mission Objective", "Allies Remaining Fraction must be between 0.0 and 1.0.")
                return
        elif objective_type == MissionObjectiveType.DELIVERY:
            if not self.required_item_id or not self.target_allegiance_id:
                messagebox.showerror("Mission Objective", "Select both the delivery item and target faction.")
                return
            payload.update({"requiredItemId": self.required_item_id, "targetAllegianceId": self.target_allegiance_id, "requiredPackagesDelivered": _safe_int(self.required_packages_var.get(), 1)})
        elif objective_type == MissionObjectiveType.ESCORT:
            if not self.escort_unit_id:
                messagebox.showerror("Mission Objective", "Select the unit to escort.")
                return
            payload["escortUnitId"] = self.escort_unit_id
        elif objective_type == MissionObjectiveType.SURVIVAL:
            payload["requiredHoursSurvived"] = _safe_float(self.survival_hours_var.get(), 1.0)
        elif objective_type == MissionObjectiveType.RESCUE:
            payload.update({"requiredAlliesEscaped": _safe_int(self.rescue_allies_var.get(), 1), "requiredEscapeDistance": _safe_float(self.rescue_distance_var.get(), 0.0)})
        elif objective_type == MissionObjectiveType.SCAVENGE:
            payload["requiredBasicResources"] = _safe_int(self.scavenge_resources_var.get(), 1)
        elif objective_type == MissionObjectiveType.RECRUIT:
            payload["requiredUnitsRecruited"] = _safe_int(self.recruit_units_var.get(), 1)
        self.on_save(payload)
        self.destroy()


class MissionAllegianceConfigDialog(tk.Toplevel):
    def __init__(self, parent, app, initial_payload, on_save, exclude_allegiance_ids=None):
        super().__init__(parent)
        self.title("Mission Allegiance")
        self.geometry("840x620")
        self.app = app
        self.on_save = on_save
        self.exclude_allegiance_ids = {
            str(entry or "").strip() for entry in (exclude_allegiance_ids or []) if str(entry or "").strip()
        }
        initial = initial_payload or {}
        self.allegiance_id = str(initial.get("allegianceId", "") or "").strip()
        self.unit_options_draft = [dict(entry) for entry in (initial.get("unitOptions", []) or []) if isinstance(entry, dict)]
        self.allegiance_label_var = tk.StringVar(value=self._allegiance_label(self.allegiance_id))
        self.power_point_cap_var = tk.StringVar(value=str(_safe_int(initial.get("powerPointCap", 0), 0)))
        self.cluster_probability_var = tk.StringVar(value=str(float(initial.get("clusterProbability", 0.0) or 0.0)))
        self.cluster_probability_variance_var = tk.StringVar(value=str(float(initial.get("clusterProbabilityVariance", 0.0) or 0.0)))
        self.level_min_var = tk.StringVar(value=str(_safe_int(initial.get("levelMin", 0), 0)))
        self.level_max_var = tk.StringVar(value=str(_safe_int(initial.get("levelMax", 0), 0)))
        self.summary_var = tk.StringVar(value="")

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)
        self._selector_row(container, "Allegiance", self.allegiance_label_var, self._select_allegiance)
        self._entry_row(container, "Power Point Cap", self.power_point_cap_var)
        self._entry_row(container, "Cluster Probability", self.cluster_probability_var)
        self._entry_row(container, "Cluster Variance", self.cluster_probability_variance_var)
        self._entry_row(container, "Level Min", self.level_min_var)
        self._entry_row(container, "Level Max", self.level_max_var)

        unit_frame = ttk.LabelFrame(container, text="Possible Units")
        unit_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.unit_listbox = tk.Listbox(unit_frame, height=12)
        self.unit_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        unit_actions = ttk.Frame(unit_frame)
        unit_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(unit_actions, text="Add Unit", command=self._add_unit_option).pack(side=tk.LEFT)
        ttk.Button(unit_actions, text="Edit Selected", command=self._edit_selected_unit_option).pack(side=tk.LEFT, padx=6)
        ttk.Button(unit_actions, text="Remove Selected", command=self._remove_selected_unit_option).pack(side=tk.LEFT)

        ttk.Label(container, textvariable=self.summary_var, wraplength=760, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 6))
        actions = ttk.Frame(container)
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)
        self._refresh_unit_listbox()
        self._refresh_summary()
        self.transient(parent)
        self.grab_set()

    def _entry_row(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _selector_row(self, parent, label, var, callback):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Select", command=callback).pack(side=tk.LEFT, padx=(6, 0))

    def _allegiance_label(self, allegiance_id):
        if not allegiance_id:
            return "<None>"
        allegiance = self.app.allegiance_service.get_allegiance_by_id(allegiance_id)
        return self.app.allegiance_service.get_allegiance_label(allegiance) if allegiance is not None else f"Unknown [{allegiance_id}]"

    def _unit_option_label(self, payload):
        unit_id = str(payload.get("unitId", "") or "").strip()
        unit = self.app.unit_service.get_unit_by_id(unit_id)
        unit_label = self.app.unit_service.get_unit_label(unit) if unit is not None else f"Unknown [{unit_id}]"
        capacity_min = payload.get("capacityMin")
        capacity_max = payload.get("capacityMax")
        if capacity_min is None and capacity_max is None:
            capacity_text = "No cap"
        else:
            capacity_text = f"Min {'None' if capacity_min is None else capacity_min} / Max {'None' if capacity_max is None else capacity_max}"
        elite_text = f"Elite {float(payload.get('eliteChance', 0.0) or 0.0) * 100.0:.0f}%"
        return f"{unit_label} | {capacity_text} | {elite_text} | {'Boss' if payload.get('isBoss') else 'Regular'}"

    def _refresh_unit_listbox(self):
        self.unit_listbox.delete(0, tk.END)
        for payload in self.unit_options_draft:
            self.unit_listbox.insert(tk.END, self._unit_option_label(payload))

    def _refresh_summary(self):
        self.summary_var.set(f"Selected allegiance: {self.allegiance_label_var.get()} | {len(self.unit_options_draft)} unit options")

    def _select_allegiance(self):
        exclude_ids = set(self.exclude_allegiance_ids)
        if self.allegiance_id:
            exclude_ids.discard(self.allegiance_id)
        AllegianceSelectDialog(self, self.app.allegiance_service, lambda allegiance_id: (setattr(self, 'allegiance_id', allegiance_id), self.allegiance_label_var.set(self._allegiance_label(allegiance_id)), self._refresh_summary()), exclude_ids=exclude_ids)

    def _selected_unit_index(self):
        selection = self.unit_listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        return index if 0 <= index < len(self.unit_options_draft) else None

    def _add_unit_option(self):
        exclude_ids = [entry.get("unitId") for entry in self.unit_options_draft]
        MissionUnitOptionDialog(self, self.app, None, self._append_unit_option, exclude_unit_ids=exclude_ids)

    def _append_unit_option(self, payload):
        unit_id = str(payload.get("unitId", "") or "").strip()
        if unit_id in {str(entry.get("unitId", "") or "").strip() for entry in self.unit_options_draft}:
            messagebox.showerror("Mission Allegiance", "That unit is already listed for this allegiance.")
            return
        self.unit_options_draft.append(payload)
        self._refresh_unit_listbox()
        self._refresh_summary()

    def _edit_selected_unit_option(self):
        index = self._selected_unit_index()
        if index is None:
            messagebox.showerror("Mission Allegiance", "Select a unit option to edit.")
            return
        exclude_ids = [entry.get("unitId") for position, entry in enumerate(self.unit_options_draft) if position != index]
        MissionUnitOptionDialog(self, self.app, dict(self.unit_options_draft[index]), lambda payload: self._replace_unit_option(index, payload), exclude_unit_ids=exclude_ids)

    def _replace_unit_option(self, index, payload):
        unit_id = str(payload.get("unitId", "") or "").strip()
        other_ids = {str(entry.get("unitId", "") or "").strip() for position, entry in enumerate(self.unit_options_draft) if position != index}
        if unit_id in other_ids:
            messagebox.showerror("Mission Allegiance", "That unit is already listed for this allegiance.")
            return
        self.unit_options_draft[index] = payload
        self._refresh_unit_listbox()
        self._refresh_summary()

    def _remove_selected_unit_option(self):
        index = self._selected_unit_index()
        if index is None:
            return
        self.unit_options_draft.pop(index)
        self._refresh_unit_listbox()
        self._refresh_summary()

    def _save(self):
        try:
            power_point_cap = int(self.power_point_cap_var.get().strip() or 0)
            level_min = int(self.level_min_var.get().strip() or 0)
            level_max = int(self.level_max_var.get().strip() or 0)
            cluster_probability = float(self.cluster_probability_var.get().strip() or 0.0)
            cluster_probability_variance = float(self.cluster_probability_variance_var.get().strip() or 0.0)
        except Exception:
            messagebox.showerror("Mission Allegiance", "Power points, levels, and cluster values must be numeric.")
            return
        if not self.allegiance_id:
            messagebox.showerror("Mission Allegiance", "Select an allegiance.")
            return
        if power_point_cap < 0 or level_min < 0 or level_max < 0 or level_max < level_min:
            messagebox.showerror("Mission Allegiance", "Invalid power point or level range values.")
            return
        if not 0.0 <= cluster_probability <= 1.0 or not 0.0 <= cluster_probability_variance <= 1.0:
            messagebox.showerror("Mission Allegiance", "Cluster values must be between 0.0 and 1.0.")
            return
        self.on_save({"allegianceId": self.allegiance_id, "powerPointCap": power_point_cap, "unitOptions": list(self.unit_options_draft), "clusterProbability": cluster_probability, "clusterProbabilityVariance": cluster_probability_variance, "levelMin": level_min, "levelMax": level_max})
        self.destroy()

class MissionEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_mission_id = None
        self.allegiance_configs_draft = []
        self.objective_draft = {}

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Mission Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_mission_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Mission", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Mission>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.name_var = tk.StringVar()
        self.portal_mission_var = tk.BooleanVar(value=True)
        name_row = ttk.Frame(self)
        name_row.pack(fill=tk.X, pady=2)
        ttk.Label(name_row, text="Name", width=18).pack(side=tk.LEFT)
        ttk.Entry(name_row, textvariable=self.name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        portal_row = ttk.Frame(self)
        portal_row.pack(fill=tk.X, pady=2)
        ttk.Label(portal_row, text="Portal Mission", width=18).pack(side=tk.LEFT)
        ttk.Checkbutton(portal_row, variable=self.portal_mission_var).pack(side=tk.LEFT)

        objective_row = ttk.Frame(self)
        objective_row.pack(fill=tk.X, pady=4)
        ttk.Label(objective_row, text="Objective", width=18).pack(side=tk.LEFT)
        self.objective_label_var = tk.StringVar(value="<No Objective>")
        ttk.Entry(objective_row, textvariable=self.objective_label_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(objective_row, text="Edit Objective", command=self._edit_objective).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(objective_row, text="Clear", command=self._clear_objective).pack(side=tk.LEFT, padx=(6, 0))

        allegiance_frame = ttk.LabelFrame(self, text="Mission Allegiances")
        allegiance_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.allegiance_listbox = tk.Listbox(allegiance_frame, height=12)
        self.allegiance_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        actions = ttk.Frame(allegiance_frame)
        actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(actions, text="Add Allegiance", command=self._add_allegiance_config).pack(side=tk.LEFT)
        ttk.Button(actions, text="Edit Selected", command=self._edit_selected_allegiance_config).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Remove Selected", command=self._remove_selected_allegiance_config).pack(side=tk.LEFT)

        self.summary = tk.Text(self, height=14, wrap=tk.WORD)
        self.summary.pack(fill=tk.BOTH, expand=False, pady=6)
        ttk.Button(self, text="Save Mission", command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _clear_form(self):
        self.current_mission_id = None
        self.name_var.set("")
        self.objective_draft = {}
        self.portal_mission_var.set(True)
        self.objective_label_var.set("<No Objective>")
        self.allegiance_configs_draft = []
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _filtered_missions(self):
        query = self.search_var.get().strip().lower()
        return [mission for mission in self.app.mission_service.list_missions() if not query or query in self.app.mission_service.get_mission_label(mission).lower()]

    def refresh_mission_list(self, reset_form):
        labels = ["<New Mission>"] + [self.app.mission_service.get_mission_label(mission) for mission in self._filtered_missions()]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<New Mission>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<New Mission>")

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Mission>":
            self._clear_form()
            return
        mission_id = self.app.mission_service.parse_mission_id_from_label(selected)
        mission = self.app.mission_service.get_mission_by_id(mission_id)
        if mission is None:
            return
        mission_data = mission.to_dict()
        self.current_mission_id = mission.missionId
        self.name_var.set(str(mission.name or ""))
        self.portal_mission_var.set(bool(mission_data.get("portalMission", True)))
        self.objective_draft = dict(mission_data.get("objective", {}) or {})
        self.objective_label_var.set(_objective_description(self.objective_draft))
        self.allegiance_configs_draft = [dict(entry) for entry in mission_data.get("allegianceConfigs", [])]
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _edit_objective(self):
        MissionObjectiveDialog(self, self.app, self.objective_draft, self._set_objective)

    def _set_objective(self, payload):
        self.objective_draft = dict(payload or {})
        self.objective_label_var.set(_objective_description(self.objective_draft))
        self._refresh_summary()

    def _clear_objective(self):
        self._set_objective({})

    def _allegiance_config_label(self, payload):
        allegiance_id = str(payload.get("allegianceId", "") or "").strip()
        allegiance = self.app.allegiance_service.get_allegiance_by_id(allegiance_id)
        allegiance_label = self.app.allegiance_service.get_allegiance_label(allegiance) if allegiance is not None else f"Unknown [{allegiance_id}]"
        unit_count = len(payload.get("unitOptions", []) or [])
        return f"{allegiance_label} | PP {int(payload.get('powerPointCap', 0) or 0)} | Lv {int(payload.get('levelMin', 0) or 0)}-{int(payload.get('levelMax', 0) or 0)} | Cluster {float(payload.get('clusterProbability', 0.0) or 0.0):.2f} +/- {float(payload.get('clusterProbabilityVariance', 0.0) or 0.0):.2f} | {unit_count} units"

    def _unit_option_summary(self, payload):
        unit_id = str(payload.get("unitId", "") or "").strip()
        unit = self.app.unit_service.get_unit_by_id(unit_id)
        unit_label = self.app.unit_service.get_unit_label(unit) if unit is not None else f"Unknown [{unit_id}]"
        capacity_min = payload.get("capacityMin")
        capacity_max = payload.get("capacityMax")
        if capacity_min is None and capacity_max is None:
            capacity_text = "No min/max"
        else:
            capacity_text = f"Min {'None' if capacity_min is None else capacity_min} / Max {'None' if capacity_max is None else capacity_max}"
        elite_text = f"Elite {float(payload.get('eliteChance', 0.0) or 0.0) * 100.0:.0f}%"
        return f"{unit_label} | {capacity_text} | {elite_text} | {'Boss' if payload.get('isBoss') else 'Regular'}"

    def _refresh_allegiance_listbox(self):
        self.allegiance_listbox.delete(0, tk.END)
        for payload in self.allegiance_configs_draft:
            self.allegiance_listbox.insert(tk.END, self._allegiance_config_label(payload))

    def _refresh_summary(self):
        lines = [f"Mission: {self.name_var.get().strip() or '<Unnamed Mission>'}", f"Mission ID: {self.current_mission_id or '<Unsaved>'}", f"Portal Mission: {'Yes' if self.portal_mission_var.get() else 'No'}", f"Objective: {_objective_description(self.objective_draft)}", "", "Mission Allegiances:"]
        if not self.allegiance_configs_draft:
            lines.append("<None>")
        else:
            for index, payload in enumerate(self.allegiance_configs_draft, start=1):
                lines.append(f"{index}. {self._allegiance_config_label(payload)}")
                for unit_payload in payload.get("unitOptions", []) or []:
                    lines.append(f"   - {self._unit_option_summary(unit_payload)}")
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, "\n".join(lines))

    def _selected_allegiance_index(self):
        selection = self.allegiance_listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        return index if 0 <= index < len(self.allegiance_configs_draft) else None

    def _add_allegiance_config(self):
        exclude_ids = [entry.get("allegianceId") for entry in self.allegiance_configs_draft]
        MissionAllegianceConfigDialog(self, self.app, None, self._append_allegiance_config, exclude_allegiance_ids=exclude_ids)

    def _append_allegiance_config(self, payload):
        allegiance_id = str(payload.get("allegianceId", "") or "").strip()
        if allegiance_id in {str(entry.get("allegianceId", "") or "").strip() for entry in self.allegiance_configs_draft}:
            messagebox.showerror("Mission Editor", "That allegiance is already included in this mission.")
            return
        self.allegiance_configs_draft.append(payload)
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _edit_selected_allegiance_config(self):
        index = self._selected_allegiance_index()
        if index is None:
            messagebox.showerror("Mission Editor", "Select a mission allegiance to edit.")
            return
        exclude_ids = [entry.get("allegianceId") for position, entry in enumerate(self.allegiance_configs_draft) if position != index]
        MissionAllegianceConfigDialog(self, self.app, dict(self.allegiance_configs_draft[index]), lambda payload: self._replace_allegiance_config(index, payload), exclude_allegiance_ids=exclude_ids)

    def _replace_allegiance_config(self, index, payload):
        allegiance_id = str(payload.get("allegianceId", "") or "").strip()
        other_ids = {str(entry.get("allegianceId", "") or "").strip() for position, entry in enumerate(self.allegiance_configs_draft) if position != index}
        if allegiance_id in other_ids:
            messagebox.showerror("Mission Editor", "That allegiance is already included in this mission.")
            return
        self.allegiance_configs_draft[index] = payload
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _remove_selected_allegiance_config(self):
        index = self._selected_allegiance_index()
        if index is None:
            return
        self.allegiance_configs_draft.pop(index)
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _save(self):
        payload = {"name": str(self.name_var.get() or "").strip(), "portalMission": bool(self.portal_mission_var.get()), "objective": dict(self.objective_draft), "allegianceConfigs": list(self.allegiance_configs_draft)}
        if not payload["name"]:
            messagebox.showerror("Mission Editor", "Mission name is required.")
            return
        if not payload["objective"]:
            messagebox.showerror("Mission Editor", "Mission objective is required.")
            return
        try:
            mission = self.app.mission_service.edit_mission_from_patch(self.current_mission_id, payload) if self.current_mission_id else self.app.mission_service.create_mission_from_dict(payload)
            messagebox.showinfo("Mission Editor", "Mission saved.")
            self.refresh_mission_list(reset_form=False)
            self.pick_var.set(self.app.mission_service.get_mission_label(mission))
            self.current_mission_id = mission.missionId
            mission_data = mission.to_dict()
            self.portal_mission_var.set(bool(mission_data.get("portalMission", True)))
            self.objective_draft = dict(mission_data.get("objective", {}) or {})
            self.objective_label_var.set(_objective_description(self.objective_draft))
            self.allegiance_configs_draft = [dict(entry) for entry in mission_data.get("allegianceConfigs", [])]
            self._refresh_allegiance_listbox()
            self._refresh_summary()
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to save mission: {exc}")
