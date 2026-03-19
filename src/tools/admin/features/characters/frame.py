import json
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.character import HealthState
from src.domain.main_character import CharacterInfo, HobbyInterestLevel, LLMControlProfile, MainCharacter
from src.domain.character_util import FriendlyFireTolerance
from src.domain.character_io import character_from_state, character_to_state
from src.services.character_generation import generate_main_character_from_scratch
from src.tools.admin.shared.bonus_dialogs import BonusEditorDialog
from src.tools.admin.shared.bonus_payloads import _normalize_achievement_entry
from src.tools.admin.shared.forms import _parse_label_id, _safe_float, _safe_int
from src.tools.admin.shared.gear_dialogs import AttributesEditorDialog, GearEditorDialog
from src.tools.admin.shared.pickers import AchievementPickerDialog, RacePickerDialog
from .dialogs import MainCharacterInfoDialog


class CharacterEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_character_id = None
        self.is_main_character = False
        self.main_character_info_draft = self._default_main_character_info()
        self.llm_control_profile_draft = self._default_llm_control_profile()
        self.main_character_hobbies_draft = self._default_main_character_hobbies()

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Character Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_character_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Character", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Character>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.vars = {
            "name": tk.StringVar(),
            "description": tk.StringVar(),
            "portraitURL": tk.StringVar(),
            "footerImageURL": tk.StringVar(),
            "level": tk.StringVar(value="0"),
            "raceTier": tk.StringVar(value="Tier I"),
            "race": tk.StringVar(value="Human1"),
            "health": tk.StringVar(value="100"),
            "healthState": tk.StringVar(value=HealthState.HEALTHY.name),
            "friendlyFireTolerance": tk.StringVar(value=FriendlyFireTolerance.NO_FRIENDLY_FIRE.value),
        }
        self._row_entry("Name", self.vars["name"])
        self._row_entry("Description", self.vars["description"])
        self._row_entry("Portrait URL", self.vars["portraitURL"])
        self._row_entry("Footer Image URL", self.vars["footerImageURL"])
        self._row_entry("Level", self.vars["level"])
        self._row_entry("Race Tier", self.vars["raceTier"])

        race_row = ttk.Frame(self)
        race_row.pack(fill=tk.X, pady=2)
        ttk.Label(race_row, text="Race", width=18).pack(side=tk.LEFT)
        ttk.Entry(race_row, textvariable=self.vars["race"], state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(race_row, text="Select", command=self._select_race).pack(side=tk.LEFT, padx=4)
        ttk.Button(race_row, text="Clear", command=self._clear_race).pack(side=tk.LEFT)

        self._row_entry("Health", self.vars["health"])
        self._row_combo("Health State", self.vars["healthState"], [e.name for e in HealthState])
        self._row_combo("Friendly Fire", self.vars["friendlyFireTolerance"], [entry.value for entry in FriendlyFireTolerance])

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, pady=8)
        ttk.Button(actions, text="Edit Attributes", command=self._edit_attributes).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Edit Gear", command=self._edit_gear).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Edit Bonus (Buff List)", command=self._edit_buffs).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Add Achievement", command=self._add_achievement).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Remove Achievement", command=self._remove_selected_achievement).pack(side=tk.LEFT, padx=4)
        self.main_character_button = ttk.Button(actions, text="Convert to Main Character", command=self._edit_main_character)
        self.main_character_button.pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Generate Main Character", command=self._generate_main_character_from_scratch).pack(side=tk.LEFT, padx=4)

        achievement_panel = ttk.LabelFrame(self, text="Assigned Achievements")
        achievement_panel.pack(fill=tk.BOTH, expand=False, pady=6)
        self.achievement_listbox = tk.Listbox(achievement_panel, height=6)
        self.achievement_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.summary = tk.Text(self, height=12, wrap=tk.WORD)
        self.summary.pack(fill=tk.BOTH, expand=True, pady=6)

        ttk.Button(self, text="Save Character", command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _row_entry(self, label, var):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _row_combo(self, label, var, values):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Combobox(row, state="readonly", values=values, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _default_attributes(self):
        return {
            "physical_power": 5,
            "physical_stamina": 5,
            "physical_resistance": 5,
            "magic_power": 5,
            "magic_stamina": 5,
            "magic_resistance": 5,
        }

    def _default_gear(self):
        return {
            "head_item_id": "",
            "neck_item_id": "",
            "body_item_id": "",
            "hands_item_id": "",
            "ring_item_id": "",
            "legs_item_id": "",
            "feet_item_id": "",
            "primary_weapon_item_id": "",
            "offhand_item_id": "",
            "inventory_item_ids": [],
        }

    def _default_main_character_info(self):
        return CharacterInfo().to_dict()

    def _default_llm_control_profile(self):
        return LLMControlProfile().to_dict()

    def _default_main_character_hobbies(self):
        return []

    def _normalize_main_character_info(self, payload) -> dict:
        return CharacterInfo.from_dict(payload).to_dict()

    def _normalize_llm_control_profile(self, payload) -> dict:
        return LLMControlProfile.from_dict(payload).to_dict()

    def _normalize_main_character_hobbies(self, payload) -> list[dict]:
        normalized = []
        if not isinstance(payload, list):
            return normalized
        for entry in payload:
            if isinstance(entry, dict):
                hobby_name = str(entry.get("name", "") or "").strip()
                interest_value = str(entry.get("interestLevel", HobbyInterestLevel.INDIFFERENT.value) or HobbyInterestLevel.INDIFFERENT.value)
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                hobby_name = str(entry[0] or "").strip()
                interest_value = str(getattr(entry[1], "value", entry[1]) or HobbyInterestLevel.INDIFFERENT.value)
            else:
                continue
            if not hobby_name:
                continue
            valid_interest = next(
                (option.value for option in HobbyInterestLevel if interest_value.upper() == option.name or interest_value.lower() == option.value.lower()),
                HobbyInterestLevel.INDIFFERENT.value,
            )
            normalized.append({"name": hobby_name, "interestLevel": valid_interest})
        return normalized

    def _refresh_main_character_button(self):
        button_text = "Edit Main Character Info" if self.is_main_character else "Convert to Main Character"
        self.main_character_button.config(text=button_text)

    def _clear_form(self):
        self.current_character_id = None
        self.is_main_character = False
        self.main_character_info_draft = self._default_main_character_info()
        self.llm_control_profile_draft = self._default_llm_control_profile()
        self.main_character_hobbies_draft = self._default_main_character_hobbies()
        self.vars["name"].set("")
        self.vars["description"].set("")
        self.vars["portraitURL"].set("")
        self.vars["footerImageURL"].set("")
        self.vars["level"].set("0")
        self.vars["raceTier"].set("Tier I")
        self.vars["race"].set("Human1")
        self.vars["health"].set("100")
        self.vars["healthState"].set(HealthState.HEALTHY.name)
        self.vars["friendlyFireTolerance"].set(FriendlyFireTolerance.NO_FRIENDLY_FIRE.value)
        self.attributes_draft = self._default_attributes()
        self.gear_draft = self._default_gear()
        self.buffs_draft = []
        self.achievements_draft = []
        self.spells_data = []
        self.general_skills_data = []
        self.stats_data = None
        self._refresh_main_character_button()
        self._refresh_summary()

    def _filtered_characters(self):
        query = self.search_var.get().strip().lower()
        result = []
        for character_id, character in self.app.character_service.list_characters():
            label = f"{character.name} [{character_id}]"
            if query and query not in label.lower():
                continue
            result.append((character_id, character))
        return result

    def refresh_character_list(self, reset_form: bool):
        labels = ["<New Character>"] + [f"{character.name} [{character_id}]" for character_id, character in self._filtered_characters()]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<New Character>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<New Character>")

    def _load_state_into_form(self, state: dict, character_id: str | None = None):
        self.current_character_id = character_id
        self.is_main_character = bool(state.get("characterType") == "MainCharacter" or state.get("characterInfo"))
        self.main_character_info_draft = (
            self._normalize_main_character_info(state.get("characterInfo"))
            if self.is_main_character
            else self._default_main_character_info()
        )
        self.llm_control_profile_draft = (
            self._normalize_llm_control_profile(state.get("llmControlProfile"))
            if self.is_main_character
            else self._default_llm_control_profile()
        )
        self.main_character_hobbies_draft = (
            self._normalize_main_character_hobbies(state.get("hobbies"))
            if self.is_main_character
            else self._default_main_character_hobbies()
        )
        self.vars["name"].set(state.get("name", ""))
        self.vars["description"].set(str(state.get("description", "") or ""))
        self.vars["portraitURL"].set(str(state.get("portraitURL", "") or ""))
        self.vars["footerImageURL"].set(str(state.get("footerImageURL", "") or ""))
        self.vars["level"].set(str(state.get("level", 0)))
        self.vars["raceTier"].set(str(state.get("raceTier", "Tier I")))
        self.vars["race"].set(str(state.get("race", "Human1") or "Human1"))
        self.vars["health"].set(str(state.get("health", 100)))
        self.vars["healthState"].set(str(state.get("healthState", HealthState.HEALTHY.name)))
        self.vars["friendlyFireTolerance"].set(str(state.get("friendlyFireTolerance", FriendlyFireTolerance.NO_FRIENDLY_FIRE.value) or FriendlyFireTolerance.NO_FRIENDLY_FIRE.value))
        attrs = state.get("attributes", {})
        self.attributes_draft = {
            "physical_power": _safe_int(attrs.get("physicalPower", 5), 5),
            "physical_stamina": _safe_int(attrs.get("physicalStamina", 5), 5),
            "physical_resistance": _safe_int(attrs.get("physicalResistance", 5), 5),
            "magic_power": _safe_int(attrs.get("magicPower", 5), 5),
            "magic_stamina": _safe_int(attrs.get("magicStamina", 5), 5),
            "magic_resistance": _safe_int(attrs.get("magicResistance", 5), 5),
        }
        self.gear_draft = state.get("gear", self._default_gear())
        self.buffs_draft = state.get("buffs", [])
        self.achievements_draft = state.get("achievements", [])
        self.spells_data = state.get("spells", [])
        self.general_skills_data = state.get("generalSkills", [])
        self.stats_data = state.get("stats") if self.is_main_character else None
        self._refresh_main_character_button()
        self._refresh_summary()

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Character>":
            self._clear_form()
            return
        character_id = _parse_label_id(selected)
        character = self.app.character_service.get_character(character_id)
        if character is None:
            return
        self._load_state_into_form(character_to_state(character), character_id=character_id)

    def _format_hobby_summary(self) -> str:
        if not self.main_character_hobbies_draft:
            return "No particular hobby [Indifferent]"
        return ", ".join(
            f"{entry.get('name', '')} [{entry.get('interestLevel', HobbyInterestLevel.INDIFFERENT.value)}]"
            for entry in self.main_character_hobbies_draft
            if str(entry.get("name", "") or "").strip()
        ) or "No particular hobby [Indifferent]"

    def _refresh_summary(self):
        lines = [
            f"Character Type: {'MainCharacter' if self.is_main_character else 'Character'}",
            f"Description: {self.vars['description'].get().strip()}",
            f"Portrait URL: {self.vars['portraitURL'].get().strip()}",
            f"Footer Image URL: {self.vars['footerImageURL'].get().strip()}",
            f"Race ID: {self.vars['race'].get().strip() or 'Human1'}",
            f"Friendly Fire: {self.vars['friendlyFireTolerance'].get().strip() or FriendlyFireTolerance.NO_FRIENDLY_FIRE.value}",
        ]

        if self.is_main_character:
            info = self.main_character_info_draft
            lines.extend(
                [
                    f"Main Character Age: {info.get('age', 0)}",
                    f"Occupation: {info.get('occupation', '')}",
                    f"Job: {info.get('job', '')}",
                    f"Personality Type: {info.get('personalityType', '')}",
                    f"Hobbies: {self._format_hobby_summary()}",
                    f"Voice Notes: {self.llm_control_profile_draft.get('voiceNotes', '')[:80]}",
                    f"Knowledge Boundaries: {self.llm_control_profile_draft.get('knowledgeBoundaryNotes', '')[:80]}",
                ]
            )

        lines.extend(
            [
                "",
                "Attributes:",
                json.dumps(self.attributes_draft, indent=2, ensure_ascii=False),
                "",
                "Gear:",
                json.dumps(self.gear_draft, indent=2, ensure_ascii=False),
                "",
                f"Buff entries: {len(self.buffs_draft)}",
                f"Achievement entries: {len(self.achievements_draft)}",
            ]
        )
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, "\n".join(lines))

        self.achievement_listbox.delete(0, tk.END)
        for entry in self.achievements_draft:
            name = str(entry.get("name", "") or "").strip() or "<Unnamed>"
            title = str(entry.get("title", "") or "").strip()
            description = str(entry.get("description", "") or "").strip()
            label = f"{name} ({title})" if title else name
            if description:
                label += f" - {description[:80]}"
            self.achievement_listbox.insert(tk.END, label)

    def _select_race(self):
        def _on_select(race_id: str):
            self.vars["race"].set(str(race_id or "Human1"))
            self._refresh_summary()

        RacePickerDialog(self, self.app.race_service, _on_select)

    def _clear_race(self):
        self.vars["race"].set("Human1")
        self._refresh_summary()

    def _generate_main_character_from_scratch(self):
        race_id = str(self.vars["race"].get() or "Human1").strip() or "Human1"
        race = self.app.race_service.get_race(race_id)
        if race is None:
            messagebox.showerror("Character Editor", f"Select a valid race before generating. '{race_id}' was not found.")
            return

        generated_name = self.vars["name"].get().strip() or f"{race.name} Main Character"
        try:
            generated = generate_main_character_from_scratch(
                name=generated_name,
                race=race,
            )
        except Exception as exc:
            messagebox.showerror("Character Editor", f"Failed to generate Main Character: {exc}")
            return

        self.pick_var.set("<New Character>")
        self._load_state_into_form(character_to_state(generated), character_id=None)
        messagebox.showinfo("Character Editor", "Generated a new unsaved Main Character draft.")

    def _build_character_for_main_character_conversion(self):
        if not self.vars["name"].get().strip():
            self.vars["name"].set("Generated Main Character")
        payload = self._build_payload(include_main_character=False)
        return character_from_state(
            payload,
            item_resolver=self.app.item_service.get_item,
            error_item=self.app.item_service.context.error_item,
        )

    def _edit_main_character(self):
        if not self.is_main_character:
            try:
                base_character = self._build_character_for_main_character_conversion()
                main_character = MainCharacter.from_character(base_character)
                self.main_character_info_draft = self._normalize_main_character_info(
                    main_character.characterInfo.to_dict()
                )
                self.llm_control_profile_draft = self._normalize_llm_control_profile(
                    main_character.llmControlProfile.to_dict()
                )
                self.main_character_hobbies_draft = self._normalize_main_character_hobbies(
                    character_to_state(main_character).get("hobbies", [])
                )
                self.is_main_character = True
            except Exception as exc:
                messagebox.showerror("Character Editor", f"Failed to convert to Main Character: {exc}")
                return

        self._refresh_main_character_button()
        self._refresh_summary()
        MainCharacterInfoDialog(self, self.main_character_info_draft, self.llm_control_profile_draft, self.main_character_hobbies_draft, self._on_main_character_info_saved)

    def _on_main_character_info_saved(self, payload):
        self.main_character_info_draft = self._normalize_main_character_info(payload.get("characterInfo"))
        self.llm_control_profile_draft = self._normalize_llm_control_profile(payload.get("llmControlProfile"))
        self.main_character_hobbies_draft = self._normalize_main_character_hobbies(payload.get("hobbies"))
        self.is_main_character = True
        self._refresh_main_character_button()
        self._refresh_summary()

    def _edit_attributes(self):
        AttributesEditorDialog(self, self.attributes_draft, self._on_attributes_saved)

    def _on_attributes_saved(self, payload):
        self.attributes_draft = payload
        self._refresh_summary()

    def _edit_gear(self):
        GearEditorDialog(self, self.gear_draft, self.app.item_service, self._on_gear_saved)

    def _on_gear_saved(self, payload):
        self.gear_draft = payload
        self._refresh_summary()

    def _edit_buffs(self):
        BonusEditorDialog(self, self.buffs_draft, self._on_buffs_saved)

    def _on_buffs_saved(self, payload):
        self.buffs_draft = payload
        self._refresh_summary()

    def _add_achievement(self):
        def _on_select(payload):
            entry = _normalize_achievement_entry(payload)
            achievement_name = str(entry.get("name", "") or "").strip()
            if not achievement_name:
                return
            if any(str(existing.get("name", "") or "").strip().lower() == achievement_name.lower() for existing in self.achievements_draft):
                messagebox.showinfo("Character Editor", f"Achievement '{achievement_name}' is already assigned.")
                return
            self.achievements_draft.append(entry)
            self._refresh_summary()

        AchievementPickerDialog(self, self.app.achievement_service, _on_select)

    def _remove_selected_achievement(self):
        selection = self.achievement_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.achievements_draft):
            return
        self.achievements_draft.pop(index)
        self._refresh_summary()

    def _build_payload(self, include_main_character: bool = True):
        payload = {
            "name": self.vars["name"].get().strip(),
            "level": _safe_int(self.vars["level"].get(), 0),
            "raceTier": self.vars["raceTier"].get().strip() or "Tier I",
            "race": self.vars["race"].get().strip() or "Human1",
            "health": _safe_int(self.vars["health"].get(), 100),
            "healthState": self.vars["healthState"].get().strip() or HealthState.HEALTHY.name,
            "description": self.vars["description"].get().strip(),
            "portraitURL": self.vars["portraitURL"].get().strip(),
            "footerImageURL": self.vars["footerImageURL"].get().strip(),
            "friendlyFireTolerance": self.vars["friendlyFireTolerance"].get().strip() or FriendlyFireTolerance.NO_FRIENDLY_FIRE.value,
            "attributes": {
                "physicalPower": _safe_float(self.attributes_draft.get("physical_power", 5), 5),
                "physicalStamina": _safe_float(self.attributes_draft.get("physical_stamina", 5), 5),
                "physicalResistance": _safe_float(self.attributes_draft.get("physical_resistance", 5), 5),
                "magicPower": _safe_float(self.attributes_draft.get("magic_power", 5), 5),
                "magicStamina": _safe_float(self.attributes_draft.get("magic_stamina", 5), 5),
                "magicResistance": _safe_float(self.attributes_draft.get("magic_resistance", 5), 5),
            },
            "affinities": {"chi": 0.5, "mana": 0.5, "psi": 0.5, "aether": 0.5},
            "gear": dict(self.gear_draft),
            "buffs": list(self.buffs_draft),
            "achievements": list(self.achievements_draft),
            "spells": list(self.spells_data),
            "generalSkills": list(self.general_skills_data),
        }
        if include_main_character and self.is_main_character:
            payload["characterType"] = "MainCharacter"
            payload["characterInfo"] = dict(self.main_character_info_draft)
            payload["llmControlProfile"] = dict(self.llm_control_profile_draft)
            payload["hobbies"] = list(self.main_character_hobbies_draft)
            payload["stats"] = dict(self.stats_data) if isinstance(self.stats_data, dict) else self.stats_data
        return payload

    def _save(self):
        payload = self._build_payload()
        if not payload["name"]:
            messagebox.showerror("Character Editor", "Character name is required.")
            return
        try:
            if self.current_character_id:
                self.app.character_service.edit_character_from_patch(self.current_character_id, payload)
            else:
                character_id, _ = self.app.character_service.create_character_from_dict(payload)
                self.current_character_id = character_id
            messagebox.showinfo("Character Editor", "Character saved.")
            self.refresh_character_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Character Editor", f"Failed to save character: {exc}")

