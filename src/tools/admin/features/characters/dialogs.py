import tkinter as tk
from tkinter import ttk

from src.domain.main_character import CharacterInfo, HobbyInterestLevel, LLMControlProfile
from src.tools.admin.shared.forms import _safe_int


class MainCharacterInfoDialog(tk.Toplevel):
    def __init__(self, parent, info_draft: dict, profile_draft: dict, hobbies_draft: list[dict], on_save):
        super().__init__(parent)
        self.title("Main Character Info")
        self.geometry("820x1040")
        self.on_save = on_save
        self.info_vars = {}
        self.profile_widgets = {}

        body = ttk.Frame(self, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        ttk.Label(body, text="Character Info", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        for field_key, label in CharacterInfo.FIELD_SPECS:
            row = ttk.Frame(body)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            var = tk.StringVar(value=str(info_draft.get(field_key, "") or ""))
            self.info_vars[field_key] = var
            ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Separator(body, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)
        ttk.Label(body, text="Hobbies", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(body, text="One per line: Hobby Name | InterestLevel").pack(anchor="w")
        self.hobbies_widget = tk.Text(body, height=7, wrap=tk.WORD)
        self.hobbies_widget.pack(fill=tk.BOTH, expand=False, pady=(4, 0))
        hobby_lines = []
        for entry in hobbies_draft or []:
            if not isinstance(entry, dict):
                continue
            hobby_name = str(entry.get("name", "") or "").strip()
            if not hobby_name:
                continue
            interest_level = str(
                entry.get("interestLevel", HobbyInterestLevel.INDIFFERENT.value) or HobbyInterestLevel.INDIFFERENT.value
            )
            hobby_lines.append(f"{hobby_name} | {interest_level}")
        if not hobby_lines:
            hobby_lines = [f"No particular hobby | {HobbyInterestLevel.INDIFFERENT.value}"]
        self.hobbies_widget.insert("1.0", "\n".join(hobby_lines))

        ttk.Separator(body, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)
        ttk.Label(body, text="LLM Control Profile", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        for field_key, label in LLMControlProfile.FIELD_SPECS:
            row = ttk.Frame(body)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT, anchor="n")
            widget = tk.Text(row, height=4, wrap=tk.WORD)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            widget.insert("1.0", str(profile_draft.get(field_key, "") or ""))
            self.profile_widgets[field_key] = widget

        actions = ttk.Frame(body)
        actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self.transient(parent)
        self.grab_set()

    def _parse_hobbies(self) -> list[dict]:
        hobbies = []
        seen = set()
        raw_text = self.hobbies_widget.get("1.0", tk.END)
        for raw_line in raw_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if "|" in line:
                hobby_name, interest_text = [part.strip() for part in line.split("|", 1)]
            else:
                hobby_name, interest_text = line, HobbyInterestLevel.INDIFFERENT.value
            if not hobby_name:
                continue
            lowered = hobby_name.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized_interest = next(
                (
                    option.value
                    for option in HobbyInterestLevel
                    if interest_text.upper() == option.name or interest_text.lower() == option.value.lower()
                ),
                HobbyInterestLevel.INDIFFERENT.value,
            )
            hobbies.append({"name": hobby_name, "interestLevel": normalized_interest})
        return hobbies

    def _save(self):
        payload = {
            "characterInfo": {},
            "llmControlProfile": {},
            "hobbies": self._parse_hobbies()
            or [
                {
                    "name": "No particular hobby",
                    "interestLevel": HobbyInterestLevel.INDIFFERENT.value,
                }
            ],
        }
        for field_key, _label in CharacterInfo.FIELD_SPECS:
            value = self.info_vars[field_key].get().strip()
            if field_key == "age":
                payload["characterInfo"][field_key] = _safe_int(value, 0)
            else:
                payload["characterInfo"][field_key] = value
        for field_key, _label in LLMControlProfile.FIELD_SPECS:
            payload["llmControlProfile"][field_key] = self.profile_widgets[field_key].get("1.0", tk.END).strip()
        self.on_save(payload)
        self.destroy()
