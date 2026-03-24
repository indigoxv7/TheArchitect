import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.campaign import CampaignUnlockGroup
from src.tools.admin.shared.forms import _safe_int
from src.tools.admin.shared.pickers import MissionSelectDialog


class CampaignUnlockGroupDialog(tk.Toplevel):
    def __init__(self, parent, app, initial_payload, on_save):
        super().__init__(parent)
        self.title("Campaign Unlock Group")
        self.geometry("840x620")
        self.app = app
        self.on_save = on_save
        initial = initial_payload or {}
        self.unlock_id = str(initial.get("unlockId", "") or "").strip()
        self.minimum_level_var = tk.StringVar(
            value="" if initial.get("minimumCharacterLevel") is None else str(initial.get("minimumCharacterLevel"))
        )
        self.required_mission_ids = [
            str(entry or "").strip()
            for entry in (initial.get("requiredCompletedMissionIds", []) or [])
            if str(entry or "").strip()
        ]
        self.unlocked_mission_ids = [
            str(entry or "").strip() for entry in (initial.get("missionIds", []) or []) if str(entry or "").strip()
        ]
        self.summary_var = tk.StringVar(value="")

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        level_row = ttk.Frame(container)
        level_row.pack(fill=tk.X, pady=2)
        ttk.Label(level_row, text="Min Character Level", width=20).pack(side=tk.LEFT)
        ttk.Entry(level_row, textvariable=self.minimum_level_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        required_frame = ttk.LabelFrame(container, text="Required Completed Missions")
        required_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.required_listbox = tk.Listbox(required_frame, height=8)
        self.required_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        required_actions = ttk.Frame(required_frame)
        required_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(required_actions, text="Add Mission", command=self._add_required_mission).pack(side=tk.LEFT)
        ttk.Button(required_actions, text="Remove Selected", command=self._remove_required_mission).pack(
            side=tk.LEFT, padx=6
        )

        unlock_frame = ttk.LabelFrame(container, text="Unlocked Missions")
        unlock_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.unlock_listbox = tk.Listbox(unlock_frame, height=8)
        self.unlock_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        unlock_actions = ttk.Frame(unlock_frame)
        unlock_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(unlock_actions, text="Add Mission", command=self._add_unlocked_mission).pack(side=tk.LEFT)
        ttk.Button(unlock_actions, text="Remove Selected", command=self._remove_unlocked_mission).pack(
            side=tk.LEFT, padx=6
        )

        ttk.Label(container, textvariable=self.summary_var, justify=tk.LEFT, wraplength=760).pack(
            fill=tk.X, pady=(2, 8)
        )

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_required_listbox()
        self._refresh_unlocked_listbox()
        self._refresh_summary()
        self.transient(parent)
        self.grab_set()

    def _mission_label(self, mission_id: str) -> str:
        mission = self.app.mission_service.get_mission_by_id(mission_id)
        if mission is None:
            return f"Unknown [{mission_id}]"
        return self.app.mission_service.get_mission_label(mission)

    def _refresh_required_listbox(self):
        self.required_listbox.delete(0, tk.END)
        for mission_id in self.required_mission_ids:
            self.required_listbox.insert(tk.END, self._mission_label(mission_id))

    def _refresh_unlocked_listbox(self):
        self.unlock_listbox.delete(0, tk.END)
        for mission_id in self.unlocked_mission_ids:
            self.unlock_listbox.insert(tk.END, self._mission_label(mission_id))

    def _refresh_summary(self):
        description = CampaignUnlockGroup(
            missionIds=self.unlocked_mission_ids,
            requiredCompletedMissionIds=self.required_mission_ids,
            minimumCharacterLevel=None
            if self.minimum_level_var.get().strip() == ""
            else _safe_int(self.minimum_level_var.get(), 0),
            unlockId=self.unlock_id,
        ).describe()
        self.summary_var.set(description)

    def _add_required_mission(self):
        MissionSelectDialog(
            self,
            self.app.mission_service,
            self._append_required_mission,
            exclude_ids=self.required_mission_ids,
        )

    def _append_required_mission(self, mission_id: str):
        if mission_id not in self.required_mission_ids:
            self.required_mission_ids.append(mission_id)
            self._refresh_required_listbox()
            self._refresh_summary()

    def _remove_required_mission(self):
        selection = self.required_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.required_mission_ids):
            self.required_mission_ids.pop(index)
            self._refresh_required_listbox()
            self._refresh_summary()

    def _add_unlocked_mission(self):
        MissionSelectDialog(
            self,
            self.app.mission_service,
            self._append_unlocked_mission,
            exclude_ids=self.unlocked_mission_ids,
        )

    def _append_unlocked_mission(self, mission_id: str):
        if mission_id not in self.unlocked_mission_ids:
            self.unlocked_mission_ids.append(mission_id)
            self._refresh_unlocked_listbox()
            self._refresh_summary()

    def _remove_unlocked_mission(self):
        selection = self.unlock_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.unlocked_mission_ids):
            self.unlocked_mission_ids.pop(index)
            self._refresh_unlocked_listbox()
            self._refresh_summary()

    def _save(self):
        minimum_level_text = self.minimum_level_var.get().strip()
        minimum_level = None
        if minimum_level_text != "":
            try:
                minimum_level = max(0, int(minimum_level_text))
            except Exception:
                messagebox.showerror("Campaign Unlock Group", "Minimum Character Level must be blank or an integer.")
                return
        if not self.unlocked_mission_ids:
            messagebox.showerror("Campaign Unlock Group", "Select at least one mission to unlock.")
            return
        self.on_save(
            {
                "unlockId": self.unlock_id,
                "missionIds": list(self.unlocked_mission_ids),
                "requiredCompletedMissionIds": list(self.required_mission_ids),
                "minimumCharacterLevel": minimum_level,
            }
        )
        self.destroy()
