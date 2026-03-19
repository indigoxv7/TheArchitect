import copy
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.campaign import CampaignProgress
from src.tools.admin.shared.forms import _safe_int


class PlayerCampaignProgressDialog(tk.Toplevel):
    def __init__(self, parent, app, player, on_saved=None):
        super().__init__(parent)
        self.title("Player Campaign Progress")
        self.geometry("900x700")
        self.app = app
        self.player = player
        self.on_saved = on_saved
        self.current_campaign_id = ""

        self.app.campaign_service.ensure_player_progress(self.player)
        self.progress_draft_by_id = {
            campaign_id: progress.to_dict()
            for campaign_id, progress in getattr(self.player, "campaignProgressById", {}).items()
            if isinstance(progress, CampaignProgress)
        }

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        player_label = str(getattr(self.player, "playerName", "") or f"Player {getattr(self.player, 'discordID', 0)}")
        ttk.Label(container, text=f"Campaign progress for {player_label}", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        pick_row = ttk.Frame(container)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Campaign", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<Select Campaign>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        body = ttk.Frame(container)
        body.pack(fill=tk.BOTH, expand=True, pady=6)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        unlocked_frame = ttk.LabelFrame(body, text="Unlocked Missions")
        unlocked_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        unlocked_frame.rowconfigure(0, weight=1)
        unlocked_frame.columnconfigure(0, weight=1)
        self.unlocked_listbox = tk.Listbox(unlocked_frame, height=16)
        self.unlocked_listbox.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        unlocked_actions = ttk.Frame(unlocked_frame)
        unlocked_actions.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        ttk.Button(unlocked_actions, text="Add", command=self._add_unlocked_mission).pack(side=tk.LEFT)
        ttk.Button(unlocked_actions, text="Remove", command=self._remove_unlocked_mission).pack(side=tk.LEFT, padx=6)

        completed_frame = ttk.LabelFrame(body, text="Completed Missions")
        completed_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        completed_frame.rowconfigure(0, weight=1)
        completed_frame.columnconfigure(0, weight=1)
        self.completed_listbox = tk.Listbox(completed_frame, height=16)
        self.completed_listbox.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        completed_actions = ttk.Frame(completed_frame)
        completed_actions.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        ttk.Button(completed_actions, text="Add", command=self._add_completed_mission).pack(side=tk.LEFT)
        ttk.Button(completed_actions, text="Remove", command=self._remove_completed_mission).pack(side=tk.LEFT, padx=6)

        self.summary_var = tk.StringVar(value="Select a campaign.")
        ttk.Label(container, textvariable=self.summary_var, justify=tk.LEFT, wraplength=820).pack(fill=tk.X, pady=(0, 8))

        action_row = ttk.Frame(container)
        action_row.pack(fill=tk.X)
        ttk.Button(action_row, text="Rebuild from Conditions", command=self._rebuild_current_progress).pack(side=tk.LEFT)
        ttk.Button(action_row, text="Save Progress", command=self._save).pack(side=tk.LEFT, padx=6)
        ttk.Button(action_row, text="Close", command=self.destroy).pack(side=tk.RIGHT)

        self._refresh_campaign_list(reset_selection=True)
        self.transient(parent)
        self.grab_set()

    def _refresh_campaign_list(self, reset_selection: bool):
        labels = ["<Select Campaign>"] + [
            self.app.campaign_service.get_campaign_label(campaign)
            for campaign in self.app.campaign_service.list_campaigns()
        ]
        self.pick["values"] = labels
        if reset_selection or self.pick_var.get() not in labels:
            self.pick_var.set("<Select Campaign>")
            self.current_campaign_id = ""
            self._refresh_lists()

    def _on_pick(self, _event=None):
        selected = self.pick_var.get().strip()
        if selected == "<Select Campaign>":
            self.current_campaign_id = ""
            self._refresh_lists()
            return
        self.current_campaign_id = self.app.campaign_service.parse_campaign_id_from_label(selected)
        self._ensure_draft(self.current_campaign_id)
        self._refresh_lists()

    def _ensure_draft(self, campaign_id: str) -> dict:
        if campaign_id not in self.progress_draft_by_id:
            progress = self.app.campaign_service.get_player_campaign_progress(self.player, campaign_id, create_if_missing=True)
            if progress is None:
                self.progress_draft_by_id[campaign_id] = CampaignProgress(campaignId=campaign_id).to_dict()
            else:
                self.progress_draft_by_id[campaign_id] = progress.to_dict()
        return self.progress_draft_by_id[campaign_id]

    def _mission_label(self, mission_id: str) -> str:
        mission = self.app.mission_service.get_mission_by_id(mission_id)
        if mission is None:
            return f"Unknown [{mission_id}]"
        return self.app.mission_service.get_mission_label(mission)

    def _refresh_lists(self):
        self.unlocked_listbox.delete(0, tk.END)
        self.completed_listbox.delete(0, tk.END)
        if not self.current_campaign_id:
            self.summary_var.set("Select a campaign.")
            return

        campaign = self.app.campaign_service.get_campaign_by_id(self.current_campaign_id)
        draft = self._ensure_draft(self.current_campaign_id)
        unlocked_ids = [str(entry or "").strip() for entry in (draft.get("unlockedMissionIds", []) or []) if str(entry or "").strip()]
        completed_ids = [str(entry or "").strip() for entry in (draft.get("completedMissionIds", []) or []) if str(entry or "").strip()]

        for mission_id in unlocked_ids:
            self.unlocked_listbox.insert(tk.END, self._mission_label(mission_id))
        for mission_id in completed_ids:
            self.completed_listbox.insert(tk.END, self._mission_label(mission_id))

        unlocked_count = len(unlocked_ids)
        completed_count = len(completed_ids)
        group_count = len(getattr(campaign, "unlockGroups", []) or []) if campaign is not None else 0
        self.summary_var.set(
            f"Campaign: {getattr(campaign, 'name', self.current_campaign_id)} | Unlocked: {unlocked_count} | Completed: {completed_count} | Unlock Groups: {group_count}"
        )

    def _append_to_list(self, key: str, mission_id: str):
        if not self.current_campaign_id:
            return
        draft = self._ensure_draft(self.current_campaign_id)
        draft.setdefault(key, [])
        if mission_id not in draft[key]:
            draft[key].append(mission_id)
        if key == "completedMissionIds":
            draft.setdefault("unlockedMissionIds", [])
            if mission_id not in draft["unlockedMissionIds"]:
                draft["unlockedMissionIds"].append(mission_id)
        self._refresh_lists()

    def _selected_id(self, listbox, key: str) -> str | None:
        if not self.current_campaign_id:
            return None
        selection = listbox.curselection()
        if not selection:
            return None
        draft = self._ensure_draft(self.current_campaign_id)
        values = [str(entry or "").strip() for entry in (draft.get(key, []) or []) if str(entry or "").strip()]
        index = int(selection[0])
        if index < 0 or index >= len(values):
            return None
        return values[index]

    def _add_unlocked_mission(self):
        if not self.current_campaign_id:
            messagebox.showerror("Campaign Progress", "Select a campaign first.")
            return
        draft = self._ensure_draft(self.current_campaign_id)
        MissionSelectDialog(
            self,
            self.app.mission_service,
            lambda mission_id: self._append_to_list("unlockedMissionIds", mission_id),
            exclude_ids=draft.get("unlockedMissionIds", []),
        )

    def _remove_unlocked_mission(self):
        mission_id = self._selected_id(self.unlocked_listbox, "unlockedMissionIds")
        if mission_id is None:
            return
        draft = self._ensure_draft(self.current_campaign_id)
        draft["unlockedMissionIds"] = [entry for entry in draft.get("unlockedMissionIds", []) if entry != mission_id]
        self._refresh_lists()

    def _add_completed_mission(self):
        if not self.current_campaign_id:
            messagebox.showerror("Campaign Progress", "Select a campaign first.")
            return
        draft = self._ensure_draft(self.current_campaign_id)
        MissionSelectDialog(
            self,
            self.app.mission_service,
            lambda mission_id: self._append_to_list("completedMissionIds", mission_id),
            exclude_ids=draft.get("completedMissionIds", []),
        )

    def _remove_completed_mission(self):
        mission_id = self._selected_id(self.completed_listbox, "completedMissionIds")
        if mission_id is None:
            return
        draft = self._ensure_draft(self.current_campaign_id)
        draft["completedMissionIds"] = [entry for entry in draft.get("completedMissionIds", []) if entry != mission_id]
        self._refresh_lists()

    def _rebuild_current_progress(self):
        if not self.current_campaign_id:
            messagebox.showerror("Campaign Progress", "Select a campaign first.")
            return
        draft = self._ensure_draft(self.current_campaign_id)
        temp_progress = CampaignProgress.from_dict(draft)

        class _PlayerView:
            def __init__(self, source_player, campaign_id, progress):
                self.characters = list(getattr(source_player, "characters", []) or [])
                self.campaignProgressById = {campaign_id: progress}

        temp_player = _PlayerView(self.player, self.current_campaign_id, temp_progress)
        self.app.campaign_service.refresh_player_campaign_progress(
            temp_player,
            campaign_id=self.current_campaign_id,
            rebuild=True,
        )
        self.progress_draft_by_id[self.current_campaign_id] = temp_progress.to_dict()
        self._refresh_lists()

    def _save(self):
        if not self.progress_draft_by_id:
            messagebox.showinfo("Campaign Progress", "No campaign progress changes to save.")
            self.destroy()
            return

        for campaign_id, payload in self.progress_draft_by_id.items():
            self.player.campaignProgressById[campaign_id] = CampaignProgress.from_dict(payload)
            self.player.campaignProgressById[campaign_id].campaignId = campaign_id

        self.app.campaign_service.refresh_player_campaign_progress(self.player, rebuild=False)
        self.app.player_service.persist_player(self.player)
        if callable(self.on_saved):
            self.on_saved()
        messagebox.showinfo("Campaign Progress", "Player campaign progress saved.")
        self.destroy()
