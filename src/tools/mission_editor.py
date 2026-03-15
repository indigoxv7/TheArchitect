import tkinter as tk
from tkinter import messagebox, ttk

from src.tools.catalog_selectors import AllegianceSelectDialog, UnitSelectDialog


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


class MissionUnitOptionDialog(tk.Toplevel):
    def __init__(self, parent, app, initial_payload: dict | None, on_save, exclude_unit_ids=None):
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
        self.capacity_min_var = tk.StringVar(
            value="" if initial.get("capacityMin") is None else str(initial.get("capacityMin"))
        )
        self.capacity_max_var = tk.StringVar(
            value="" if initial.get("capacityMax") is None else str(initial.get("capacityMax"))
        )
        self.can_be_elite_var = tk.BooleanVar(value=bool(initial.get("canBeElite", False)))

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        unit_row = ttk.Frame(container)
        unit_row.pack(fill=tk.X, pady=2)
        ttk.Label(unit_row, text="Unit", width=18).pack(side=tk.LEFT)
        ttk.Entry(unit_row, textvariable=self.unit_label_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(unit_row, text="Select", command=self._select_unit).pack(side=tk.LEFT, padx=(6, 0))

        self._row_entry(container, "Capacity Min", self.capacity_min_var)
        self._row_entry(container, "Capacity Max", self.capacity_max_var)

        elite_row = ttk.Frame(container)
        elite_row.pack(fill=tk.X, pady=2)
        ttk.Label(elite_row, text="Can Be Elite", width=18).pack(side=tk.LEFT)
        ttk.Checkbutton(elite_row, variable=self.can_be_elite_var).pack(side=tk.LEFT)

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self.transient(parent)
        self.grab_set()

    def _row_entry(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _unit_label(self, unit_id: str) -> str:
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

        def _on_select(unit_id: str):
            self.unit_id = unit_id
            self.unit_label_var.set(self._unit_label(unit_id))

        UnitSelectDialog(self, self.app.unit_service, _on_select, exclude_ids=exclude_ids)

    def _save(self):
        if not self.unit_id:
            messagebox.showerror("Mission Unit Option", "Select a unit.")
            return

        capacity_min = self.capacity_min_var.get().strip()
        capacity_max = self.capacity_max_var.get().strip()
        if capacity_min:
            try:
                capacity_min_value = int(capacity_min)
            except Exception:
                messagebox.showerror("Mission Unit Option", "Capacity Min must be an integer or blank.")
                return
        else:
            capacity_min_value = None

        if capacity_max:
            try:
                capacity_max_value = int(capacity_max)
            except Exception:
                messagebox.showerror("Mission Unit Option", "Capacity Max must be an integer or blank.")
                return
        else:
            capacity_max_value = None

        if capacity_min_value is not None and capacity_min_value < 0:
            messagebox.showerror("Mission Unit Option", "Capacity Min cannot be negative.")
            return
        if capacity_max_value is not None and capacity_max_value < 0:
            messagebox.showerror("Mission Unit Option", "Capacity Max cannot be negative.")
            return
        if (
            capacity_min_value is not None
            and capacity_max_value is not None
            and capacity_min_value > capacity_max_value
        ):
            messagebox.showerror("Mission Unit Option", "Capacity Min cannot be greater than Capacity Max.")
            return

        self.on_save(
            {
                "unitId": self.unit_id,
                "capacityMin": capacity_min_value,
                "capacityMax": capacity_max_value,
                "canBeElite": bool(self.can_be_elite_var.get()),
            }
        )
        self.destroy()

class MissionAllegianceConfigDialog(tk.Toplevel):
    def __init__(self, parent, app, initial_payload: dict | None, on_save, exclude_allegiance_ids=None):
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
        self.unit_options_draft = []
        for entry in initial.get("unitOptions", []) or []:
            if not isinstance(entry, dict):
                continue
            self.unit_options_draft.append(
                {
                    "unitId": str(entry.get("unitId", "") or "").strip(),
                    "capacityMin": entry.get("capacityMin"),
                    "capacityMax": entry.get("capacityMax"),
                    "canBeElite": bool(entry.get("canBeElite", False)),
                }
            )

        self.allegiance_label_var = tk.StringVar(value=self._allegiance_label(self.allegiance_id))
        self.power_point_cap_var = tk.StringVar(value=str(_safe_int(initial.get("powerPointCap", 0), 0)))
        self.cluster_probability_var = tk.StringVar(value=str(float(initial.get("clusterProbability", 0.0))))
        self.cluster_probability_variance_var = tk.StringVar(
            value=str(float(initial.get("clusterProbabilityVariance", 0.0)))
        )
        self.level_min_var = tk.StringVar(value=str(_safe_int(initial.get("levelMin", 0), 0)))
        self.level_max_var = tk.StringVar(value=str(_safe_int(initial.get("levelMax", 0), 0)))
        self.summary_var = tk.StringVar(value="")

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        allegiance_row = ttk.Frame(container)
        allegiance_row.pack(fill=tk.X, pady=2)
        ttk.Label(allegiance_row, text="Allegiance", width=18).pack(side=tk.LEFT)
        ttk.Entry(allegiance_row, textvariable=self.allegiance_label_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(allegiance_row, text="Select", command=self._select_allegiance).pack(side=tk.LEFT, padx=(6, 0))

        self._row_entry(container, "Power Point Cap", self.power_point_cap_var)
        self._row_entry(container, "Cluster Probability", self.cluster_probability_var)
        self._row_entry(container, "Cluster Variance", self.cluster_probability_variance_var)
        self._row_entry(container, "Level Min", self.level_min_var)
        self._row_entry(container, "Level Max", self.level_max_var)

        unit_frame = ttk.LabelFrame(container, text="Possible Units")
        unit_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.unit_listbox = tk.Listbox(unit_frame, height=12)
        self.unit_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        unit_actions = ttk.Frame(unit_frame)
        unit_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(unit_actions, text="Add Unit", command=self._add_unit_option).pack(side=tk.LEFT)
        ttk.Button(unit_actions, text="Edit Selected", command=self._edit_selected_unit_option).pack(side=tk.LEFT, padx=6)
        ttk.Button(unit_actions, text="Remove Selected", command=self._remove_selected_unit_option).pack(side=tk.LEFT)

        ttk.Label(container, textvariable=self.summary_var, wraplength=760, justify=tk.LEFT).pack(
            fill=tk.X, pady=(0, 6)
        )

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_unit_listbox()
        self._refresh_summary()
        self.transient(parent)
        self.grab_set()

    def _row_entry(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _allegiance_label(self, allegiance_id: str) -> str:
        if not allegiance_id:
            return "<None>"
        allegiance = self.app.allegiance_service.get_allegiance_by_id(allegiance_id)
        if allegiance is None:
            return f"Unknown [{allegiance_id}]"
        return self.app.allegiance_service.get_allegiance_label(allegiance)

    def _unit_option_label(self, payload: dict) -> str:
        unit_id = str(payload.get("unitId", "") or "").strip()
        unit = self.app.unit_service.get_unit_by_id(unit_id)
        unit_label = self.app.unit_service.get_unit_label(unit) if unit is not None else f"Unknown [{unit_id}]"
        capacity_min = payload.get("capacityMin")
        capacity_max = payload.get("capacityMax")
        if capacity_min is None and capacity_max is None:
            capacity_text = "No cap"
        else:
            min_text = "None" if capacity_min is None else str(capacity_min)
            max_text = "None" if capacity_max is None else str(capacity_max)
            capacity_text = f"Min {min_text} / Max {max_text}"
        elite_text = "Elite OK" if payload.get("canBeElite") else "Not Elite"
        return f"{unit_label} | {capacity_text} | {elite_text}"

    def _refresh_unit_listbox(self):
        self.unit_listbox.delete(0, tk.END)
        for payload in self.unit_options_draft:
            self.unit_listbox.insert(tk.END, self._unit_option_label(payload))

    def _refresh_summary(self):
        self.summary_var.set(
            f"Selected allegiance: {self.allegiance_label_var.get()} | "
            f"{len(self.unit_options_draft)} unit options"
        )

    def _select_allegiance(self):
        exclude_ids = set(self.exclude_allegiance_ids)
        if self.allegiance_id:
            exclude_ids.discard(self.allegiance_id)

        def _on_select(allegiance_id: str):
            self.allegiance_id = allegiance_id
            self.allegiance_label_var.set(self._allegiance_label(allegiance_id))
            self._refresh_summary()

        AllegianceSelectDialog(self, self.app.allegiance_service, _on_select, exclude_ids=exclude_ids)

    def _add_unit_option(self):
        exclude_ids = [entry.get("unitId") for entry in self.unit_options_draft]

        def _on_save(payload: dict):
            unit_id = str(payload.get("unitId", "") or "").strip()
            if unit_id in {str(entry.get("unitId", "") or "").strip() for entry in self.unit_options_draft}:
                messagebox.showerror("Mission Allegiance", "That unit is already listed for this allegiance.")
                return
            self.unit_options_draft.append(payload)
            self._refresh_unit_listbox()
            self._refresh_summary()

        MissionUnitOptionDialog(self, self.app, None, _on_save, exclude_unit_ids=exclude_ids)

    def _selected_unit_index(self) -> int | None:
        selection = self.unit_listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        if index < 0 or index >= len(self.unit_options_draft):
            return None
        return index

    def _edit_selected_unit_option(self):
        index = self._selected_unit_index()
        if index is None:
            messagebox.showerror("Mission Allegiance", "Select a unit option to edit.")
            return

        current = dict(self.unit_options_draft[index])
        exclude_ids = [
            entry.get("unitId")
            for position, entry in enumerate(self.unit_options_draft)
            if position != index
        ]

        def _on_save(payload: dict):
            unit_id = str(payload.get("unitId", "") or "").strip()
            other_ids = {
                str(entry.get("unitId", "") or "").strip()
                for position, entry in enumerate(self.unit_options_draft)
                if position != index
            }
            if unit_id in other_ids:
                messagebox.showerror("Mission Allegiance", "That unit is already listed for this allegiance.")
                return
            self.unit_options_draft[index] = payload
            self._refresh_unit_listbox()
            self._refresh_summary()

        MissionUnitOptionDialog(self, self.app, current, _on_save, exclude_unit_ids=exclude_ids)

    def _remove_selected_unit_option(self):
        index = self._selected_unit_index()
        if index is None:
            return
        self.unit_options_draft.pop(index)
        self._refresh_unit_listbox()
        self._refresh_summary()

    def _save(self):
        if not self.allegiance_id:
            messagebox.showerror("Mission Allegiance", "Select an allegiance.")
            return

        try:
            power_point_cap = int(self.power_point_cap_var.get().strip() or 0)
            level_min = int(self.level_min_var.get().strip() or 0)
            level_max = int(self.level_max_var.get().strip() or 0)
        except Exception:
            messagebox.showerror("Mission Allegiance", "Power point cap and level range must be integers.")
            return

        try:
            cluster_probability = float(self.cluster_probability_var.get().strip() or 0.0)
            cluster_probability_variance = float(self.cluster_probability_variance_var.get().strip() or 0.0)
        except Exception:
            messagebox.showerror("Mission Allegiance", "Cluster values must be numeric.")
            return

        if power_point_cap < 0:
            messagebox.showerror("Mission Allegiance", "Power point cap cannot be negative.")
            return
        if level_min < 0 or level_max < 0:
            messagebox.showerror("Mission Allegiance", "Level range cannot be negative.")
            return
        if level_max < level_min:
            messagebox.showerror("Mission Allegiance", "Level Max cannot be less than Level Min.")
            return

        self.on_save(
            {
                "allegianceId": self.allegiance_id,
                "powerPointCap": power_point_cap,
                "unitOptions": list(self.unit_options_draft),
                "clusterProbability": max(0.0, min(1.0, cluster_probability)),
                "clusterProbabilityVariance": max(0.0, min(1.0, cluster_probability_variance)),
                "levelMin": level_min,
                "levelMax": level_max,
            }
        )
        self.destroy()

class MissionEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_mission_id = None
        self.allegiance_configs_draft: list[dict] = []

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
        name_row = ttk.Frame(self)
        name_row.pack(fill=tk.X, pady=2)
        ttk.Label(name_row, text="Name", width=18).pack(side=tk.LEFT)
        ttk.Entry(name_row, textvariable=self.name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        allegiance_frame = ttk.LabelFrame(self, text="Mission Allegiances")
        allegiance_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.allegiance_listbox = tk.Listbox(allegiance_frame, height=12)
        self.allegiance_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        actions = ttk.Frame(allegiance_frame)
        actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(actions, text="Add Allegiance", command=self._add_allegiance_config).pack(side=tk.LEFT)
        ttk.Button(actions, text="Edit Selected", command=self._edit_selected_allegiance_config).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Remove Selected", command=self._remove_selected_allegiance_config).pack(side=tk.LEFT)

        self.summary = tk.Text(self, height=12, wrap=tk.WORD)
        self.summary.pack(fill=tk.BOTH, expand=False, pady=6)

        ttk.Button(self, text="Save Mission", command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _clear_form(self):
        self.current_mission_id = None
        self.name_var.set("")
        self.allegiance_configs_draft = []
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _filtered_missions(self):
        query = self.search_var.get().strip().lower()
        results = []
        for mission in self.app.mission_service.list_missions():
            label = self.app.mission_service.get_mission_label(mission)
            if query and query not in label.lower():
                continue
            results.append(mission)
        return results

    def refresh_mission_list(self, reset_form: bool):
        labels = ["<New Mission>"] + [
            self.app.mission_service.get_mission_label(mission) for mission in self._filtered_missions()
        ]
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

        self.current_mission_id = mission.missionId
        self.name_var.set(str(mission.name or ""))
        self.allegiance_configs_draft = [dict(entry) for entry in mission.to_dict().get("allegianceConfigs", [])]
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _allegiance_config_label(self, payload: dict) -> str:
        allegiance_id = str(payload.get("allegianceId", "") or "").strip()
        allegiance = self.app.allegiance_service.get_allegiance_by_id(allegiance_id)
        allegiance_label = (
            self.app.allegiance_service.get_allegiance_label(allegiance)
            if allegiance is not None
            else f"Unknown [{allegiance_id}]"
        )
        unit_count = len(payload.get("unitOptions", []) or [])
        return (
            f"{allegiance_label} | PP {int(payload.get('powerPointCap', 0) or 0)} | "
            f"Lv {int(payload.get('levelMin', 0) or 0)}-{int(payload.get('levelMax', 0) or 0)} | "
            f"Cluster {float(payload.get('clusterProbability', 0.0) or 0.0):.2f} "
            f"+/- {float(payload.get('clusterProbabilityVariance', 0.0) or 0.0):.2f} | "
            f"{unit_count} units"
        )

    def _refresh_allegiance_listbox(self):
        self.allegiance_listbox.delete(0, tk.END)
        for payload in self.allegiance_configs_draft:
            self.allegiance_listbox.insert(tk.END, self._allegiance_config_label(payload))

    def _refresh_summary(self):
        lines = [
            f"Mission: {self.name_var.get().strip() or '<Unnamed Mission>'}",
            f"Mission ID: {self.current_mission_id or '<Unsaved>'}",
            "",
            "Mission Allegiances:",
        ]
        if not self.allegiance_configs_draft:
            lines.append("<None>")
        else:
            for index, payload in enumerate(self.allegiance_configs_draft, start=1):
                lines.append(f"{index}. {self._allegiance_config_label(payload)}")
                for unit_payload in payload.get("unitOptions", []) or []:
                    lines.append(f"   - {self._unit_option_summary(unit_payload)}")
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, "\n".join(lines))

    def _unit_option_summary(self, payload: dict) -> str:
        unit_id = str(payload.get("unitId", "") or "").strip()
        unit = self.app.unit_service.get_unit_by_id(unit_id)
        unit_label = self.app.unit_service.get_unit_label(unit) if unit is not None else f"Unknown [{unit_id}]"
        capacity_min = payload.get("capacityMin")
        capacity_max = payload.get("capacityMax")
        if capacity_min is None and capacity_max is None:
            capacity_text = "No min/max"
        else:
            min_text = "None" if capacity_min is None else str(capacity_min)
            max_text = "None" if capacity_max is None else str(capacity_max)
            capacity_text = f"Min {min_text} / Max {max_text}"
        elite_text = "Elite OK" if payload.get("canBeElite") else "Not Elite"
        return f"{unit_label} | {capacity_text} | {elite_text}"

    def _selected_allegiance_index(self) -> int | None:
        selection = self.allegiance_listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        if index < 0 or index >= len(self.allegiance_configs_draft):
            return None
        return index

    def _add_allegiance_config(self):
        exclude_ids = [entry.get("allegianceId") for entry in self.allegiance_configs_draft]

        def _on_save(payload: dict):
            allegiance_id = str(payload.get("allegianceId", "") or "").strip()
            if allegiance_id in {
                str(entry.get("allegianceId", "") or "").strip() for entry in self.allegiance_configs_draft
            }:
                messagebox.showerror("Mission Editor", "That allegiance is already included in this mission.")
                return
            self.allegiance_configs_draft.append(payload)
            self._refresh_allegiance_listbox()
            self._refresh_summary()

        MissionAllegianceConfigDialog(self, self.app, None, _on_save, exclude_allegiance_ids=exclude_ids)

    def _edit_selected_allegiance_config(self):
        index = self._selected_allegiance_index()
        if index is None:
            messagebox.showerror("Mission Editor", "Select a mission allegiance to edit.")
            return

        current = dict(self.allegiance_configs_draft[index])
        exclude_ids = [
            entry.get("allegianceId")
            for position, entry in enumerate(self.allegiance_configs_draft)
            if position != index
        ]

        def _on_save(payload: dict):
            allegiance_id = str(payload.get("allegianceId", "") or "").strip()
            other_ids = {
                str(entry.get("allegianceId", "") or "").strip()
                for position, entry in enumerate(self.allegiance_configs_draft)
                if position != index
            }
            if allegiance_id in other_ids:
                messagebox.showerror("Mission Editor", "That allegiance is already included in this mission.")
                return
            self.allegiance_configs_draft[index] = payload
            self._refresh_allegiance_listbox()
            self._refresh_summary()

        MissionAllegianceConfigDialog(self, self.app, current, _on_save, exclude_allegiance_ids=exclude_ids)

    def _remove_selected_allegiance_config(self):
        index = self._selected_allegiance_index()
        if index is None:
            return
        self.allegiance_configs_draft.pop(index)
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _build_payload(self) -> dict:
        return {
            "name": str(self.name_var.get() or "").strip(),
            "allegianceConfigs": list(self.allegiance_configs_draft),
        }

    def _save(self):
        payload = self._build_payload()
        if not payload["name"]:
            messagebox.showerror("Mission Editor", "Mission name is required.")
            return

        try:
            if self.current_mission_id:
                mission = self.app.mission_service.edit_mission_from_patch(self.current_mission_id, payload)
            else:
                mission = self.app.mission_service.create_mission_from_dict(payload)
            messagebox.showinfo("Mission Editor", "Mission saved.")
            self.refresh_mission_list(reset_form=False)
            self.pick_var.set(self.app.mission_service.get_mission_label(mission))
            self.current_mission_id = mission.missionId
            self.allegiance_configs_draft = [dict(entry) for entry in mission.to_dict().get("allegianceConfigs", [])]
            self._refresh_allegiance_listbox()
            self._refresh_summary()
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to save mission: {exc}")
