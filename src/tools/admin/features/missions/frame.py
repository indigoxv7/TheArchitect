import tkinter as tk
from tkinter import messagebox, ttk

from .dialogs import MissionAllegianceConfigDialog, MissionObjectiveDialog, _objective_description


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
        ttk.Entry(objective_row, textvariable=self.objective_label_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(objective_row, text="Edit Objective", command=self._edit_objective).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(objective_row, text="Clear", command=self._clear_objective).pack(side=tk.LEFT, padx=(6, 0))

        allegiance_frame = ttk.LabelFrame(self, text="Mission Allegiances")
        allegiance_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.allegiance_listbox = tk.Listbox(allegiance_frame, height=12)
        self.allegiance_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        actions = ttk.Frame(allegiance_frame)
        actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(actions, text="Add Allegiance", command=self._add_allegiance_config).pack(side=tk.LEFT)
        ttk.Button(actions, text="Edit Selected", command=self._edit_selected_allegiance_config).pack(
            side=tk.LEFT, padx=6
        )
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
        return [
            mission
            for mission in self.app.mission_service.list_missions()
            if not query or query in self.app.mission_service.get_mission_label(mission).lower()
        ]

    def refresh_mission_list(self, reset_form):
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
        allegiance_label = (
            self.app.allegiance_service.get_allegiance_label(allegiance)
            if allegiance is not None
            else f"Unknown [{allegiance_id}]"
        )
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
        lines = [
            f"Mission: {self.name_var.get().strip() or '<Unnamed Mission>'}",
            f"Mission ID: {self.current_mission_id or '<Unsaved>'}",
            f"Portal Mission: {'Yes' if self.portal_mission_var.get() else 'No'}",
            f"Objective: {_objective_description(self.objective_draft)}",
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

    def _selected_allegiance_index(self):
        selection = self.allegiance_listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        return index if 0 <= index < len(self.allegiance_configs_draft) else None

    def _add_allegiance_config(self):
        exclude_ids = [entry.get("allegianceId") for entry in self.allegiance_configs_draft]
        MissionAllegianceConfigDialog(
            self, self.app, None, self._append_allegiance_config, exclude_allegiance_ids=exclude_ids
        )

    def _append_allegiance_config(self, payload):
        allegiance_id = str(payload.get("allegianceId", "") or "").strip()
        if allegiance_id in {
            str(entry.get("allegianceId", "") or "").strip() for entry in self.allegiance_configs_draft
        }:
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
        exclude_ids = [
            entry.get("allegianceId")
            for position, entry in enumerate(self.allegiance_configs_draft)
            if position != index
        ]
        MissionAllegianceConfigDialog(
            self,
            self.app,
            dict(self.allegiance_configs_draft[index]),
            lambda payload: self._replace_allegiance_config(index, payload),
            exclude_allegiance_ids=exclude_ids,
        )

    def _replace_allegiance_config(self, index, payload):
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

    def _remove_selected_allegiance_config(self):
        index = self._selected_allegiance_index()
        if index is None:
            return
        self.allegiance_configs_draft.pop(index)
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _save(self):
        payload = {
            "name": str(self.name_var.get() or "").strip(),
            "portalMission": bool(self.portal_mission_var.get()),
            "objective": dict(self.objective_draft),
            "allegianceConfigs": list(self.allegiance_configs_draft),
        }
        if not payload["name"]:
            messagebox.showerror("Mission Editor", "Mission name is required.")
            return
        if not payload["objective"]:
            messagebox.showerror("Mission Editor", "Mission objective is required.")
            return
        try:
            mission = (
                self.app.mission_service.edit_mission_from_patch(self.current_mission_id, payload)
                if self.current_mission_id
                else self.app.mission_service.create_mission_from_dict(payload)
            )
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
