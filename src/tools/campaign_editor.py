import copy
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Campaign import CampaignProgress, CampaignUnlockGroup
from src.tools.catalog_selectors import MissionSelectDialog


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


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
            str(entry or "").strip()
            for entry in (initial.get("missionIds", []) or [])
            if str(entry or "").strip()
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
        ttk.Button(required_actions, text="Remove Selected", command=self._remove_required_mission).pack(side=tk.LEFT, padx=6)

        unlock_frame = ttk.LabelFrame(container, text="Unlocked Missions")
        unlock_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.unlock_listbox = tk.Listbox(unlock_frame, height=8)
        self.unlock_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        unlock_actions = ttk.Frame(unlock_frame)
        unlock_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(unlock_actions, text="Add Mission", command=self._add_unlocked_mission).pack(side=tk.LEFT)
        ttk.Button(unlock_actions, text="Remove Selected", command=self._remove_unlocked_mission).pack(side=tk.LEFT, padx=6)

        ttk.Label(container, textvariable=self.summary_var, justify=tk.LEFT, wraplength=760).pack(fill=tk.X, pady=(2, 8))

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
            minimumCharacterLevel=None if self.minimum_level_var.get().strip() == "" else _safe_int(self.minimum_level_var.get(), 0),
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


class CampaignEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_campaign_id = None
        self.starting_mission_ids_draft = []
        self.unlock_groups_draft = []

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Campaign Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_campaign_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Campaign", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Campaign>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.name_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self._row_entry("Name", self.name_var)
        self._row_entry("Description", self.description_var)

        starting_frame = ttk.LabelFrame(self, text="Starting Missions")
        starting_frame.pack(fill=tk.BOTH, expand=False, pady=6)
        self.starting_listbox = tk.Listbox(starting_frame, height=6)
        self.starting_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        starting_actions = ttk.Frame(starting_frame)
        starting_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(starting_actions, text="Add Mission", command=self._add_starting_mission).pack(side=tk.LEFT)
        ttk.Button(starting_actions, text="Remove Selected", command=self._remove_starting_mission).pack(side=tk.LEFT, padx=6)

        unlock_frame = ttk.LabelFrame(self, text="Unlock Groups")
        unlock_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.unlock_group_listbox = tk.Listbox(unlock_frame, height=10)
        self.unlock_group_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        unlock_actions = ttk.Frame(unlock_frame)
        unlock_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(unlock_actions, text="Add Group", command=self._add_unlock_group).pack(side=tk.LEFT)
        ttk.Button(unlock_actions, text="Edit Selected", command=self._edit_selected_unlock_group).pack(side=tk.LEFT, padx=6)
        ttk.Button(unlock_actions, text="Remove Selected", command=self._remove_unlock_group).pack(side=tk.LEFT)

        self.summary = tk.Text(self, height=10, wrap=tk.WORD)
        self.summary.pack(fill=tk.BOTH, expand=False, pady=6)

        ttk.Button(self, text="Save Campaign", command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _row_entry(self, label, var):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _mission_label(self, mission_id: str) -> str:
        mission = self.app.mission_service.get_mission_by_id(mission_id)
        if mission is None:
            return f"Unknown [{mission_id}]"
        return self.app.mission_service.get_mission_label(mission)

    def _unlock_group_label(self, payload: dict) -> str:
        try:
            group = CampaignUnlockGroup.from_dict(payload)
            label = group.describe()
        except Exception:
            label = "<Invalid Unlock Group>"
        unlock_id = str(payload.get("unlockId", "") or "").strip()
        if unlock_id:
            return f"[{unlock_id}] {label}"
        return label

    def _clear_form(self):
        self.current_campaign_id = None
        self.name_var.set("")
        self.description_var.set("")
        self.starting_mission_ids_draft = []
        self.unlock_groups_draft = []
        self._refresh_starting_listbox()
        self._refresh_unlock_group_listbox()
        self._refresh_summary()

    def _filtered_campaigns(self):
        query = self.search_var.get().strip().lower()
        results = []
        for campaign in self.app.campaign_service.list_campaigns():
            label = self.app.campaign_service.get_campaign_label(campaign)
            if query and query not in label.lower():
                continue
            results.append(campaign)
        return results

    def refresh_campaign_list(self, reset_form: bool):
        labels = ["<New Campaign>"] + [
            self.app.campaign_service.get_campaign_label(campaign)
            for campaign in self._filtered_campaigns()
        ]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<New Campaign>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<New Campaign>")

    def _on_pick(self, _event=None):
        selected = self.pick.get().strip()
        if selected == "<New Campaign>":
            self._clear_form()
            return

        campaign_id = self.app.campaign_service.parse_campaign_id_from_label(selected)
        campaign = self.app.campaign_service.get_campaign_by_id(campaign_id)
        if campaign is None:
            return

        self.current_campaign_id = campaign.campaignId
        self.name_var.set(str(campaign.name or ""))
        self.description_var.set(str(campaign.description or ""))
        self.starting_mission_ids_draft = list(campaign.startingMissionIds)
        self.unlock_groups_draft = [group.to_dict() for group in campaign.unlockGroups]
        self._refresh_starting_listbox()
        self._refresh_unlock_group_listbox()
        self._refresh_summary()

    def _refresh_starting_listbox(self):
        self.starting_listbox.delete(0, tk.END)
        for mission_id in self.starting_mission_ids_draft:
            self.starting_listbox.insert(tk.END, self._mission_label(mission_id))

    def _refresh_unlock_group_listbox(self):
        self.unlock_group_listbox.delete(0, tk.END)
        for payload in self.unlock_groups_draft:
            self.unlock_group_listbox.insert(tk.END, self._unlock_group_label(payload))

    def _refresh_summary(self):
        text = [
            f"Name: {self.name_var.get().strip() or '<Unnamed Campaign>'}",
            f"Description: {self.description_var.get().strip() or '<None>'}",
            "",
            "Starting Missions:",
        ]
        text.extend(
            [self._mission_label(mission_id) for mission_id in self.starting_mission_ids_draft] or ["<None>"]
        )
        text.extend(["", "Unlock Groups:"])
        text.extend(
            [self._unlock_group_label(payload) for payload in self.unlock_groups_draft] or ["<None>"]
        )
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, "\n".join(text))

    def _add_starting_mission(self):
        MissionSelectDialog(
            self,
            self.app.mission_service,
            self._append_starting_mission,
            exclude_ids=self.starting_mission_ids_draft,
        )

    def _append_starting_mission(self, mission_id: str):
        if mission_id not in self.starting_mission_ids_draft:
            self.starting_mission_ids_draft.append(mission_id)
            self._refresh_starting_listbox()
            self._refresh_summary()

    def _remove_starting_mission(self):
        selection = self.starting_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.starting_mission_ids_draft):
            self.starting_mission_ids_draft.pop(index)
            self._refresh_starting_listbox()
            self._refresh_summary()

    def _add_unlock_group(self):
        CampaignUnlockGroupDialog(self, self.app, None, self._append_unlock_group)

    def _append_unlock_group(self, payload: dict):
        self.unlock_groups_draft.append(dict(payload))
        self._refresh_unlock_group_listbox()
        self._refresh_summary()

    def _selected_unlock_group_index(self) -> int | None:
        selection = self.unlock_group_listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        if index < 0 or index >= len(self.unlock_groups_draft):
            return None
        return index

    def _edit_selected_unlock_group(self):
        index = self._selected_unlock_group_index()
        if index is None:
            messagebox.showerror("Campaign Editor", "Select an unlock group to edit.")
            return
        CampaignUnlockGroupDialog(
            self,
            self.app,
            dict(self.unlock_groups_draft[index]),
            lambda payload: self._replace_unlock_group(index, payload),
        )

    def _replace_unlock_group(self, index: int, payload: dict):
        self.unlock_groups_draft[index] = dict(payload)
        self._refresh_unlock_group_listbox()
        self._refresh_summary()

    def _remove_unlock_group(self):
        index = self._selected_unlock_group_index()
        if index is None:
            return
        self.unlock_groups_draft.pop(index)
        self._refresh_unlock_group_listbox()
        self._refresh_summary()

    def _build_payload(self) -> dict:
        return {
            "name": str(self.name_var.get() or "").strip(),
            "description": str(self.description_var.get() or "").strip(),
            "startingMissionIds": list(self.starting_mission_ids_draft),
            "unlockGroups": [dict(payload) for payload in self.unlock_groups_draft],
        }

    def _save(self):
        payload = self._build_payload()
        if not payload["name"]:
            messagebox.showerror("Campaign Editor", "Campaign name is required.")
            return

        try:
            if self.current_campaign_id:
                self.app.campaign_service.edit_campaign_from_patch(self.current_campaign_id, payload)
            else:
                self.app.campaign_service.create_campaign_from_dict(payload)
            messagebox.showinfo("Campaign Editor", "Campaign saved.")
            self.refresh_campaign_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Campaign Editor", f"Failed to save campaign: {exc}")
