import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Mission import MissionObjective, MissionObjectiveType
from src.tools.admin.shared.pickers import AllegianceSelectDialog, ItemSelectDialog, UnitSelectDialog


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
