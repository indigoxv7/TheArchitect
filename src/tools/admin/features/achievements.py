import tkinter as tk
from tkinter import messagebox, ttk

from src.tools.admin.shared.bonus_dialogs import BonusListEditorDialog
from src.tools.admin.shared.bonus_payloads import (
    _achievement_object_to_entry,
    _list_bonus_lines,
    _normalize_achievement_entry,
    _normalize_bonus_payload,
    _summarize_bonus_list,
)


class AchievementEditorDialog(tk.Toplevel):
    def __init__(self, parent, initial_list: list, on_save):
        super().__init__(parent)
        self.title("Edit Achievement List")
        self.geometry("980x640")
        self.on_save = on_save
        self.entries = [
            _normalize_achievement_entry(entry) for entry in (initial_list or []) if isinstance(entry, dict)
        ]
        self.selected_index = None
        self.current_bonuses = []

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(container)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        ttk.Label(left, text="Achievements").pack(anchor="w")
        self.listbox = tk.Listbox(left, width=52, height=20, exportselection=False)
        self.listbox.pack(fill=tk.Y, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        left_buttons = ttk.Frame(left)
        left_buttons.pack(fill=tk.X, pady=6)
        ttk.Button(left_buttons, text="New", command=self._new_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="Remove", command=self._remove_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="Apply", command=self._apply_current).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        name_row = ttk.Frame(right)
        name_row.pack(fill=tk.X, pady=2)
        ttk.Label(name_row, text="Name", width=18).pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        ttk.Entry(name_row, textvariable=self.name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        title_row = ttk.Frame(right)
        title_row.pack(fill=tk.X, pady=2)
        ttk.Label(title_row, text="Title", width=18).pack(side=tk.LEFT)
        self.title_var = tk.StringVar()
        ttk.Entry(title_row, textvariable=self.title_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        bonuses_row = ttk.Frame(right)
        bonuses_row.pack(fill=tk.X, pady=8)
        ttk.Label(bonuses_row, text="Bonuses", width=18).pack(side=tk.LEFT)
        self.bonus_summary_var = tk.StringVar(value="No bonuses")
        self.bonus_summary_label = ttk.Label(
            bonuses_row,
            textvariable=self.bonus_summary_var,
            justify=tk.LEFT,
            anchor="w",
            wraplength=760,
        )
        self.bonus_summary_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bonuses_row, text="Edit Bonuses", command=self._edit_bonuses).pack(side=tk.LEFT, padx=4)

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(bottom, text="Save and Close", command=self._save_and_close).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()
        if self.entries:
            self._select_index(0)
        else:
            self._refresh_bonus_summary()

    def _entry_label(self, index: int, entry: dict) -> str:
        name = str(entry.get("name", "") or "").strip() or "<Unnamed>"
        title = str(entry.get("title", "") or "").strip() or "No Title"
        bonuses = entry.get("bonuses", []) if isinstance(entry.get("bonuses"), list) else []
        return f"{index + 1}. {name} ({title}) | {_summarize_bonus_list(bonuses)}"

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for idx, entry in enumerate(self.entries):
            self.listbox.insert(tk.END, self._entry_label(idx, entry))

    def _refresh_bonus_summary(self):
        self.bonus_summary_var.set(_list_bonus_lines(self.current_bonuses))

    def _select_index(self, index: int):
        if index < 0 or index >= len(self.entries):
            self.selected_index = None
            return
        self.selected_index = index
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self._load_selected_entry()

    def _load_selected_entry(self):
        if self.selected_index is None:
            return
        entry = self.entries[self.selected_index]
        self.name_var.set(str(entry.get("name", "") or ""))
        self.title_var.set(str(entry.get("title", "") or ""))
        self.current_bonuses = [_normalize_bonus_payload(b) for b in entry.get("bonuses", []) if isinstance(b, dict)]
        self._refresh_bonus_summary()

    def _on_select(self, _event=None):
        selected = self.listbox.curselection()
        if not selected:
            return
        self.selected_index = int(selected[0])
        self._load_selected_entry()

    def _new_entry(self):
        self.entries.append(_normalize_achievement_entry({}))
        self._refresh_list()
        self._select_index(len(self.entries) - 1)

    def _remove_entry(self):
        if self.selected_index is None:
            return
        self.entries.pop(self.selected_index)
        self._refresh_list()
        if self.entries:
            self._select_index(min(self.selected_index, len(self.entries) - 1))
        else:
            self.selected_index = None
            self.name_var.set("")
            self.title_var.set("")
            self.current_bonuses = []
            self._refresh_bonus_summary()

    def _edit_bonuses(self):
        def _on_save(updated):
            self.current_bonuses = [_normalize_bonus_payload(entry) for entry in updated if isinstance(entry, dict)]
            self._refresh_bonus_summary()

        BonusListEditorDialog(self, self.current_bonuses, _on_save)

    def _apply_current(self):
        if self.selected_index is None:
            self._new_entry()

        payload = {
            "name": str(self.name_var.get() or "").strip(),
            "title": str(self.title_var.get() or "").strip(),
            "bonuses": list(self.current_bonuses),
        }
        self.entries[self.selected_index] = payload
        self._refresh_list()
        self._select_index(self.selected_index)

    def _save_and_close(self):
        if self.entries and self.selected_index is None:
            self._select_index(0)
        if self.selected_index is not None:
            self._apply_current()
        self.on_save(list(self.entries))
        self.destroy()


class AchievementBookFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_name = None
        self.current_bonuses = []

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Achievement Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_achievement_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Achievement", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Achievement>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.vars = {
            "name": tk.StringVar(),
            "title": tk.StringVar(),
            "description": tk.StringVar(),
        }
        self._row_entry("Name", self.vars["name"])
        self._row_entry("Title", self.vars["title"])
        self._row_entry("Description", self.vars["description"])

        bonuses_row = ttk.Frame(self)
        bonuses_row.pack(fill=tk.X, pady=8)
        ttk.Label(bonuses_row, text="Bonuses", width=18).pack(side=tk.LEFT)
        self.bonus_summary_var = tk.StringVar(value="No bonuses")
        self.bonus_summary_label = ttk.Label(
            bonuses_row,
            textvariable=self.bonus_summary_var,
            justify=tk.LEFT,
            anchor="w",
            wraplength=760,
        )
        self.bonus_summary_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bonuses_row, text="Edit Bonuses", command=self._edit_bonuses).pack(side=tk.LEFT, padx=4)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, pady=8)
        ttk.Button(actions, text="Save Achievement", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Reload Achievementbook", command=self._reload).pack(side=tk.LEFT, padx=6)

        self._clear_form()

    def _row_entry(self, label, var):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _clear_form(self):
        self.current_name = None
        self.current_bonuses = []
        self.vars["name"].set("")
        self.vars["title"].set("")
        self.vars["description"].set("")
        self._refresh_bonus_summary()

    def _refresh_bonus_summary(self):
        self.bonus_summary_var.set(_list_bonus_lines(self.current_bonuses))

    def _filtered_achievements(self):
        query = self.search_var.get().strip().lower()
        achievements = self.app.achievement_service.list_achievements()
        result = []
        for achievement in achievements:
            name = str(getattr(achievement, "name", "") or "")
            title = str(getattr(achievement, "title", "") or "")
            description = str(getattr(achievement, "description", "") or "")
            haystack = f"{name} {title} {description}".lower()
            if query and query not in haystack:
                continue
            result.append(achievement)
        return result

    def refresh_achievement_list(self, reset_form: bool):
        names = ["<New Achievement>"] + [achievement.name for achievement in self._filtered_achievements()]
        self.pick["values"] = names
        if reset_form:
            self.pick_var.set("<New Achievement>")
            self._clear_form()
        elif self.pick_var.get() not in names:
            self.pick_var.set("<New Achievement>")

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Achievement>":
            self._clear_form()
            return

        achievement = self.app.achievement_service.get_achievement(selected)
        if achievement is None:
            return

        entry = _achievement_object_to_entry(achievement)
        self.current_name = entry["name"]
        self.vars["name"].set(entry.get("name", ""))
        self.vars["title"].set(entry.get("title", ""))
        self.vars["description"].set(entry.get("description", ""))
        self.current_bonuses = [_normalize_bonus_payload(b) for b in entry.get("bonuses", []) if isinstance(b, dict)]
        self._refresh_bonus_summary()

    def _edit_bonuses(self):
        def _on_save(updated):
            self.current_bonuses = [_normalize_bonus_payload(entry) for entry in updated if isinstance(entry, dict)]
            self._refresh_bonus_summary()

        BonusListEditorDialog(self, self.current_bonuses, _on_save)

    def _build_payload(self):
        return {
            "name": str(self.vars["name"].get() or "").strip(),
            "title": str(self.vars["title"].get() or "").strip(),
            "description": str(self.vars["description"].get() or "").strip(),
            "bonuses": list(self.current_bonuses),
        }

    def _save(self):
        payload = self._build_payload()
        if not payload["name"]:
            messagebox.showerror("Achievement Editor", "Achievement name is required.")
            return
        try:
            if self.current_name:
                self.app.achievement_service.edit_achievement_from_patch(self.current_name, payload)
            else:
                self.app.achievement_service.create_achievement_from_dict(payload)
            messagebox.showinfo("Achievement Editor", "Achievement saved.")
            self.refresh_achievement_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Achievement Editor", f"Failed to save achievement: {exc}")

    def _reload(self):
        try:
            self.app.achievement_service.load_achievementbook()
            self.refresh_achievement_list(reset_form=True)
            messagebox.showinfo("Achievement Editor", "Achievementbook reloaded.")
        except Exception as exc:
            messagebox.showerror("Achievement Editor", f"Failed to reload achievementbook: {exc}")
