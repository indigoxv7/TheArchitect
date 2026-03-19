import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.character_util import TitlePreference
from src.tools.admin.shared.forms import _parse_label_id, _safe_float, _safe_int
from src.tools.admin.shared.pickers import CharacterPickerDialog, ItemPickerDialog
from src.tools.admin.shared.campaign_progress_dialog import PlayerCampaignProgressDialog


class PlayerEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_player_id = None
        self.current_player = None
        self.characters_draft = []
        self.inventory_draft = []
        self.mission_party_ids_draft = []

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Player Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_player_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Player", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<Select Player>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.discord_id_var = tk.StringVar(value="")
        self._row_entry("Discord ID", self.discord_id_var, state="readonly")

        self.vars = {
            "playerName": tk.StringVar(),
            "nano": tk.StringVar(value="0"),
            "energy": tk.StringVar(value="100"),
            "energyCap": tk.StringVar(value="100"),
            "energyLastCalculatedTime": tk.StringVar(value="0"),
            "energyRegenRatePerSecond": tk.StringVar(value=str(1.0 / 60.0)),
            "titlePreference": tk.StringVar(value=TitlePreference.Masculine.name),
            "achievementTitle": tk.StringVar(),
            "isNewPlayer": tk.StringVar(value="False"),
            "intChoice": tk.StringVar(value="0"),
        }

        self._row_entry("Player Name", self.vars["playerName"])
        self._row_entry("Nano", self.vars["nano"])
        self._row_entry("Energy", self.vars["energy"])
        self._row_entry("Energy Cap", self.vars["energyCap"])
        self._row_entry("Energy Last Time", self.vars["energyLastCalculatedTime"])
        self._row_entry("Energy Regen / Sec", self.vars["energyRegenRatePerSecond"])
        self._row_combo("Title Preference", self.vars["titlePreference"], [e.name for e in TitlePreference])
        self._row_entry("Achievement Title", self.vars["achievementTitle"])
        self._row_combo("Is New Player", self.vars["isNewPlayer"], ["True", "False"])
        self._row_entry("Int Choice", self.vars["intChoice"])

        character_panel = ttk.LabelFrame(self, text="Owned Characters")
        character_panel.pack(fill=tk.BOTH, expand=False, pady=6)
        self.character_listbox = tk.Listbox(character_panel, height=6)
        self.character_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        character_actions = ttk.Frame(character_panel)
        character_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(character_actions, text="Add Character", command=self._add_character).pack(side=tk.LEFT)
        ttk.Button(character_actions, text="Remove Selected", command=self._remove_selected_character).pack(side=tk.LEFT, padx=6)
        ttk.Button(character_actions, text="Add to Mission Party", command=self._add_selected_character_to_mission_party).pack(side=tk.LEFT)

        mission_party_panel = ttk.LabelFrame(self, text="Selected for Mission")
        mission_party_panel.pack(fill=tk.BOTH, expand=False, pady=6)
        self.mission_party_listbox = tk.Listbox(mission_party_panel, height=5)
        self.mission_party_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        mission_party_actions = ttk.Frame(mission_party_panel)
        mission_party_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(mission_party_actions, text="Add Selected Owned", command=self._add_selected_character_to_mission_party).pack(side=tk.LEFT)
        ttk.Button(mission_party_actions, text="Remove Selected", command=self._remove_selected_mission_party_member).pack(side=tk.LEFT, padx=6)

        inventory_panel = ttk.LabelFrame(self, text="Inventory Items")
        inventory_panel.pack(fill=tk.BOTH, expand=False, pady=6)
        self.inventory_listbox = tk.Listbox(inventory_panel, height=8)
        self.inventory_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        inventory_actions = ttk.Frame(inventory_panel)
        inventory_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(inventory_actions, text="Add Item", command=self._add_inventory_item).pack(side=tk.LEFT)
        ttk.Button(inventory_actions, text="Remove Selected", command=self._remove_selected_inventory_item).pack(side=tk.LEFT, padx=6)

        self.summary_var = tk.StringVar(value="No player selected.")
        ttk.Label(self, textvariable=self.summary_var, justify=tk.LEFT, anchor="w").pack(fill=tk.X, pady=(2, 8))

        action_row = ttk.Frame(self)
        action_row.pack(fill=tk.X, pady=8)
        ttk.Button(action_row, text="Edit Campaign Progress", command=self._edit_campaign_progress).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(action_row, text="Save Player", command=self._save).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        self._clear_form()

    def _row_entry(self, label, var, state="normal"):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var, state=state).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _row_combo(self, label, var, values):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Combobox(row, state="readonly", values=values, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _clear_form(self):
        self.current_player_id = None
        self.current_player = None
        self.discord_id_var.set("")
        self.vars["playerName"].set("")
        self.vars["nano"].set("0")
        self.vars["energy"].set("100")
        self.vars["energyCap"].set("100")
        self.vars["energyLastCalculatedTime"].set("0")
        self.vars["energyRegenRatePerSecond"].set(str(1.0 / 60.0))
        self.vars["titlePreference"].set(TitlePreference.Masculine.name)
        self.vars["achievementTitle"].set("")
        self.vars["isNewPlayer"].set("False")
        self.vars["intChoice"].set("0")
        self.characters_draft = []
        self.inventory_draft = []
        self.mission_party_ids_draft = []
        self._refresh_lists()

    def _filtered_players(self):
        query = self.search_var.get().strip().lower()
        result = []
        for player_id in self.app.player_service.list_known_player_ids():
            player = self.app.player_service.get_player_sync(player_id)
            if player is None:
                continue
            name = str(getattr(player, "playerName", "") or "").strip() or f"Player {player_id}"
            label = f"{name} [{player_id}]"
            if query and query not in label.lower():
                continue
            result.append((player_id, label))
        return result

    def refresh_player_list(self, reset_form: bool):
        labels = ["<Select Player>"] + [label for _, label in self._filtered_players()]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<Select Player>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<Select Player>")

    def _normalize_character_entry(self, entry):
        if entry is None:
            return None
        if hasattr(entry, "name") and hasattr(entry, "level"):
            return entry
        if isinstance(entry, str):
            return self.app.player_service.clone_character_from_template(entry, self.characters_draft)
        return None

    def _normalize_inventory_entry(self, entry):
        if entry is None:
            return None
        if hasattr(entry, "itemId") and hasattr(entry, "name"):
            return entry
        resolved = self.app.item_service.get_item(str(entry))
        if resolved is not None:
            return resolved
        if isinstance(entry, (str, int, float)):
            return str(entry)
        return None

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<Select Player>":
            self._clear_form()
            return

        try:
            player_id = int(_parse_label_id(selected))
        except Exception:
            return

        player = self.app.player_service.get_player_sync(player_id)
        if player is None:
            messagebox.showerror("Player Editor", f"Could not load player {player_id}.")
            return

        self.current_player_id = player_id
        self.current_player = player
        self.discord_id_var.set(str(player_id))
        self.vars["playerName"].set(str(getattr(player, "playerName", "") or ""))
        self.vars["nano"].set(str(_safe_int(getattr(player, "nano", 0), 0)))
        self.vars["energy"].set(str(_safe_float(getattr(player, "energy", 0.0), 0.0)))
        self.vars["energyCap"].set(str(_safe_float(getattr(player, "energyCap", 100.0), 100.0)))
        self.vars["energyLastCalculatedTime"].set(str(_safe_float(getattr(player, "energyLastCalculatedTime", 0.0), 0.0)))
        self.vars["energyRegenRatePerSecond"].set(str(_safe_float(getattr(player, "energyRegenRatePerSecond", 1.0 / 60.0), 1.0 / 60.0)))

        title_pref = getattr(player, "titlePreference", TitlePreference.Masculine)
        title_pref_name = getattr(title_pref, "name", TitlePreference.Masculine.name)
        if title_pref_name not in TitlePreference.__members__:
            title_pref_name = TitlePreference.Masculine.name
        self.vars["titlePreference"].set(title_pref_name)

        self.vars["achievementTitle"].set(str(getattr(player, "achievementTitle", "") or ""))
        self.vars["isNewPlayer"].set("True" if bool(getattr(player, "isNewPlayer", False)) else "False")
        self.vars["intChoice"].set(str(_safe_int(getattr(player, "intChoice", 0), 0)))

        self.characters_draft = []
        for entry in getattr(player, "characters", []) or []:
            normalized = self._normalize_character_entry(entry)
            if normalized is not None:
                self.characters_draft.append(normalized)

        self.inventory_draft = []
        for entry in getattr(player, "inventory", []) or []:
            normalized = self._normalize_inventory_entry(entry)
            if normalized is not None:
                self.inventory_draft.append(normalized)

        try:
            selected_party = list(player.GetMissionPartyCharacterIds())
        except Exception:
            selected_party = [str(entry or "").strip() for entry in getattr(player, "missionPartyCharacterIds", []) or [] if str(entry or "").strip()]
        self.mission_party_ids_draft = [
            character_id
            for character_id in selected_party
            if any(self._resolve_character_id(character) == character_id for character in self.characters_draft)
        ]

        self._refresh_lists()

    def _resolve_character_id(self, character_obj):
        player_instance_id = str(getattr(character_obj, "playerInstanceId", "") or "").strip()
        return player_instance_id or None

    def _character_label(self, character_obj) -> str:
        character_id = self._resolve_character_id(character_obj)
        name = str(getattr(character_obj, "name", "") or "").strip() or "<Unnamed>"
        if character_id:
            return f"{name} [{character_id}]"
        return f"{name} [Unlinked]"

    def _item_label(self, item_entry) -> str:
        if hasattr(item_entry, "itemId") and hasattr(item_entry, "name"):
            return self.app.item_service.get_item_label(item_entry)

        resolved = self.app.item_service.get_item(str(item_entry))
        if resolved is not None:
            return self.app.item_service.get_item_label(resolved)

        text = str(item_entry or "").strip() or "Unknown"
        return f"{text} [Unlinked]"

    def _ordered_mission_party_ids(self) -> list[str]:
        valid_ids = [
            character_id
            for character_id in (self._resolve_character_id(character) for character in self.characters_draft)
            if character_id
        ]
        return [character_id for character_id in self.mission_party_ids_draft if character_id in valid_ids]

    def _refresh_lists(self):
        self.character_listbox.delete(0, tk.END)
        for character in self.characters_draft:
            self.character_listbox.insert(tk.END, self._character_label(character))

        self.mission_party_listbox.delete(0, tk.END)
        ordered_party_ids = self._ordered_mission_party_ids()
        for character_id in ordered_party_ids:
            character = next((entry for entry in self.characters_draft if self._resolve_character_id(entry) == character_id), None)
            if character is not None:
                self.mission_party_listbox.insert(tk.END, self._character_label(character))

        self.inventory_listbox.delete(0, tk.END)
        for item in self.inventory_draft:
            self.inventory_listbox.insert(tk.END, self._item_label(item))

        campaign_count = len(getattr(self.current_player, "campaignProgressById", {}) or {}) if self.current_player is not None else 0
        self.summary_var.set(
            f"Characters: {len(self.characters_draft)} | Mission Party: {len(ordered_party_ids)} | Inventory Items: {len(self.inventory_draft)} | Campaigns: {campaign_count}"
        )

    def _add_character(self):
        def _on_select(character_id: str):
            character = self.app.player_service.clone_character_from_template(character_id, self.characters_draft)
            if character is None:
                return
            self.characters_draft.append(character)
            resolved_id = self._resolve_character_id(character)
            if resolved_id and not self.mission_party_ids_draft:
                self.mission_party_ids_draft.append(resolved_id)
            self._refresh_lists()

        CharacterPickerDialog(self, self.app.character_service, _on_select)

    def _remove_selected_character(self):
        selection = self.character_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.characters_draft):
            return
        character_id = self._resolve_character_id(self.characters_draft[index])
        self.characters_draft.pop(index)
        if character_id:
            self.mission_party_ids_draft = [entry for entry in self.mission_party_ids_draft if entry != character_id]
        self._refresh_lists()

    def _add_selected_character_to_mission_party(self):
        selection = self.character_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.characters_draft):
            return
        character_id = self._resolve_character_id(self.characters_draft[index])
        if not character_id:
            return
        if character_id not in self.mission_party_ids_draft:
            self.mission_party_ids_draft.append(character_id)
        self._refresh_lists()

    def _remove_selected_mission_party_member(self):
        selection = self.mission_party_listbox.curselection()
        if not selection:
            return
        ordered_party_ids = self._ordered_mission_party_ids()
        index = int(selection[0])
        if index < 0 or index >= len(ordered_party_ids):
            return
        character_id = ordered_party_ids[index]
        self.mission_party_ids_draft = [entry for entry in self.mission_party_ids_draft if entry != character_id]
        self._refresh_lists()

    def _add_inventory_item(self):
        def _on_select(item_id: str):
            item = self.app.item_service.get_item(item_id)
            if item is None:
                return
            self.inventory_draft.append(item)
            self._refresh_lists()

        ItemPickerDialog(self, self.app.item_service, _on_select)

    def _remove_selected_inventory_item(self):
        selection = self.inventory_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.inventory_draft):
            return
        self.inventory_draft.pop(index)
        self._refresh_lists()

    def _edit_campaign_progress(self):
        if self.current_player is None:
            messagebox.showerror("Player Editor", "Select a player before editing campaign progress.")
            return
        if not self.app.campaign_service.list_campaigns():
            messagebox.showerror("Player Editor", "Create at least one campaign before editing campaign progress.")
            return
        PlayerCampaignProgressDialog(self, self.app, self.current_player, on_saved=self._refresh_lists)

    def _save(self):
        if self.current_player is None or self.current_player_id is None:
            messagebox.showerror("Player Editor", "Select a player before saving.")
            return

        player = self.current_player
        previous_autosave = bool(getattr(player, "_auto_save_enabled", False))
        try:
            player.SetAutoSaveEnabled(False)
            player.playerName = str(self.vars["playerName"].get() or "").strip()
            player.nano = _safe_int(self.vars["nano"].get(), 0)
            player.energy = _safe_float(self.vars["energy"].get(), 0.0)
            player.energyCap = max(0.0, _safe_float(self.vars["energyCap"].get(), 100.0))
            player.energyLastCalculatedTime = _safe_float(self.vars["energyLastCalculatedTime"].get(), 0.0)
            player.energyRegenRatePerSecond = _safe_float(self.vars["energyRegenRatePerSecond"].get(), 1.0 / 60.0)

            title_preference_name = str(self.vars["titlePreference"].get() or TitlePreference.Masculine.name).strip()
            if title_preference_name not in TitlePreference.__members__:
                title_preference_name = TitlePreference.Masculine.name
            player.titlePreference = TitlePreference[title_preference_name]

            player.achievementTitle = str(self.vars["achievementTitle"].get() or "").strip()
            player.isNewPlayer = self.vars["isNewPlayer"].get() == "True"
            player.intChoice = _safe_int(self.vars["intChoice"].get(), 0)
            player.characters = list(self.characters_draft)
            player.inventory = list(self.inventory_draft)

            selected_party = self._ordered_mission_party_ids()
            if not selected_party and self.characters_draft:
                selected_party = [
                    character_id
                    for character_id in (self._resolve_character_id(character) for character in self.characters_draft)
                    if character_id
                ]
            player.SetMissionPartyCharacterIds(selected_party)
        except Exception as exc:
            messagebox.showerror("Player Editor", f"Failed to update player fields: {exc}")
            player.SetAutoSaveEnabled(previous_autosave)
            return

        player.SetAutoSaveEnabled(previous_autosave)
        try:
            self.app.player_service.persist_player(player)
            self.current_player = player
            self.mission_party_ids_draft = list(player.GetMissionPartyCharacterIds())
            messagebox.showinfo("Player Editor", "Player saved.")
            self.refresh_player_list(reset_form=False)
            self.pick_var.set(f"{player.playerName} [{self.current_player_id}]")
            self._refresh_lists()
        except Exception as exc:
            messagebox.showerror("Player Editor", f"Failed to save player: {exc}")

