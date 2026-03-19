import tkinter as tk
from tkinter import ttk

from src.domain.CharacterUtil import Attribute, BonusType
from .bonus_payloads import (
    BONUS_ATTRIBUTE_OPTIONS,
    _bonus_summary_text,
    _default_bonus_payload,
    _normalize_bonus_payload,
    _normalize_buff_entry,
)
from .forms import _safe_float, _safe_int


class BonusFieldsSection:
    def __init__(self, parent, title: str = "Bonus"):
        self.frame = ttk.LabelFrame(parent, text=title)
        self.frame.pack(fill=tk.X, padx=10, pady=6)

        self.bonus_type_var = tk.StringVar(value=BonusType.FLAT.name)
        self.attribute_var = tk.StringVar(value="NONE")
        self.attribute_amount_var = tk.StringVar(value="0")
        self.chi_var = tk.StringVar(value="0")
        self.mana_var = tk.StringVar(value="0")
        self.psi_var = tk.StringVar(value="0")
        self.aether_var = tk.StringVar(value="0")
        self.nano_multiplier_var = tk.StringVar(value="0")
        self.reason_var = tk.StringVar()
        self.permanent_var = tk.StringVar(value="False")

        self._row_combo("Bonus Type", self.bonus_type_var, [b.name for b in BonusType])
        self._row_combo("Attribute", self.attribute_var, BONUS_ATTRIBUTE_OPTIONS)
        self._row_entry("Attribute Bonus", self.attribute_amount_var)
        self._row_entry("Nano Multiplier", self.nano_multiplier_var)
        self._row_entry("Reason", self.reason_var)
        self._row_combo("Permanent", self.permanent_var, ["True", "False"])

        aff_row = ttk.Frame(self.frame)
        aff_row.pack(fill=tk.X, pady=2)
        ttk.Label(aff_row, text="Affinities", width=18).pack(side=tk.LEFT)
        for label, var in [
            ("Chi", self.chi_var),
            ("Mana", self.mana_var),
            ("Psi", self.psi_var),
            ("Aether", self.aether_var),
        ]:
            sub = ttk.Frame(aff_row)
            sub.pack(side=tk.LEFT, padx=4)
            ttk.Label(sub, text=label).pack(side=tk.LEFT)
            ttk.Entry(sub, textvariable=var, width=6).pack(side=tk.LEFT)

    def _row_entry(self, label: str, var):
        row = ttk.Frame(self.frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _row_combo(self, label: str, var, values):
        row = ttk.Frame(self.frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Combobox(row, state="readonly", textvariable=var, values=values).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def load_bonus(self, bonus_data):
        bonus = _normalize_bonus_payload(bonus_data)
        self.bonus_type_var.set(bonus.get("bonusType", BonusType.FLAT.name))

        attribute_bonus = bonus.get("attributeBonus")
        if isinstance(attribute_bonus, dict):
            self.attribute_var.set(str(attribute_bonus.get("attribute", "NONE") or "NONE").upper())
            self.attribute_amount_var.set(str(_safe_int(attribute_bonus.get("bonus", 0), 0)))
        else:
            self.attribute_var.set("NONE")
            self.attribute_amount_var.set("0")

        affinities = bonus.get("affinities") if isinstance(bonus.get("affinities"), dict) else {}
        self.chi_var.set(str(_safe_float(affinities.get("chi", 0.0), 0.0)))
        self.mana_var.set(str(_safe_float(affinities.get("mana", 0.0), 0.0)))
        self.psi_var.set(str(_safe_float(affinities.get("psi", 0.0), 0.0)))
        self.aether_var.set(str(_safe_float(affinities.get("aether", 0.0), 0.0)))

        self.nano_multiplier_var.set(str(_safe_float(bonus.get("nanoMultiplier", 0.0), 0.0)))
        self.reason_var.set(str(bonus.get("reason", "") or ""))
        self.permanent_var.set("True" if bool(bonus.get("permanent", False)) else "False")

    def build_bonus(self) -> dict:
        bonus_type = str(self.bonus_type_var.get() or BonusType.FLAT.name).strip().upper()
        if bonus_type not in BonusType.__members__:
            bonus_type = BonusType.FLAT.name

        attribute_name = str(self.attribute_var.get() or "NONE").strip().upper()
        if attribute_name in Attribute.__members__:
            attribute_bonus = {
                "attribute": attribute_name,
                "bonus": _safe_int(self.attribute_amount_var.get(), 0),
            }
        else:
            attribute_bonus = None

        affinities = {
            "chi": _safe_float(self.chi_var.get(), 0.0),
            "mana": _safe_float(self.mana_var.get(), 0.0),
            "psi": _safe_float(self.psi_var.get(), 0.0),
            "aether": _safe_float(self.aether_var.get(), 0.0),
        }
        if not any(value != 0.0 for value in affinities.values()):
            affinities = None

        return {
            "bonusType": bonus_type,
            "attributeBonus": attribute_bonus,
            "affinities": affinities,
            "nanoMultiplier": _safe_float(self.nano_multiplier_var.get(), 0.0),
            "reason": str(self.reason_var.get() or "").strip(),
            "permanent": self.permanent_var.get() == "True",
        }


class BonusEditorDialog(tk.Toplevel):
    def __init__(self, parent, initial_list: list, on_save):
        super().__init__(parent)
        self.title("Edit Bonus List")
        self.geometry("980x620")
        self.on_save = on_save
        self.entries = [_normalize_buff_entry(entry) for entry in (initial_list or []) if isinstance(entry, dict)]
        self.selected_index = None

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(container)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        ttk.Label(left, text="Bonus Entries").pack(anchor="w")
        self.listbox = tk.Listbox(left, width=42, height=20, exportselection=False)
        self.listbox.pack(fill=tk.Y, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        left_buttons = ttk.Frame(left)
        left_buttons.pack(fill=tk.X, pady=6)
        ttk.Button(left_buttons, text="New", command=self._new_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="Remove", command=self._remove_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="Apply", command=self._apply_current).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        duration_row = ttk.Frame(right)
        duration_row.pack(fill=tk.X, pady=2)
        ttk.Label(duration_row, text="Duration", width=18).pack(side=tk.LEFT)
        self.duration_var = tk.StringVar(value="0")
        ttk.Entry(duration_row, textvariable=self.duration_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.bonus_fields = BonusFieldsSection(right, title="Bonus")

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(bottom, text="Save and Close", command=self._save_and_close).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()
        if self.entries:
            self._select_index(0)

    def _entry_label(self, index: int, entry: dict) -> str:
        duration = _safe_int(entry.get("duration", 0), 0)
        return f"{index + 1}. Duration {duration} | {_bonus_summary_text(entry.get('bonus', {}))}"

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for idx, entry in enumerate(self.entries):
            self.listbox.insert(tk.END, self._entry_label(idx, entry))

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
        self.duration_var.set(str(_safe_int(entry.get("duration", 0), 0)))
        self.bonus_fields.load_bonus(entry.get("bonus"))

    def _on_select(self, _event=None):
        selected = self.listbox.curselection()
        if not selected:
            return
        self.selected_index = int(selected[0])
        self._load_selected_entry()

    def _new_entry(self):
        self.entries.append(_normalize_buff_entry({}))
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
            self.duration_var.set("0")
            self.bonus_fields.load_bonus(_default_bonus_payload())

    def _apply_current(self):
        if self.selected_index is None:
            self._new_entry()
        payload = {
            "duration": max(0, _safe_int(self.duration_var.get(), 0)),
            "bonus": self.bonus_fields.build_bonus(),
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


class BonusListEditorDialog(tk.Toplevel):
    def __init__(self, parent, initial_list: list, on_save):
        super().__init__(parent)
        self.title("Edit Achievement Bonuses")
        self.geometry("920x600")
        self.on_save = on_save
        self.entries = [_normalize_bonus_payload(entry) for entry in (initial_list or []) if isinstance(entry, dict)]
        self.selected_index = None

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(container)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        ttk.Label(left, text="Bonuses").pack(anchor="w")
        self.listbox = tk.Listbox(left, width=42, height=20, exportselection=False)
        self.listbox.pack(fill=tk.Y, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        left_buttons = ttk.Frame(left)
        left_buttons.pack(fill=tk.X, pady=6)
        ttk.Button(left_buttons, text="New", command=self._new_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="Remove", command=self._remove_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="Apply", command=self._apply_current).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bonus_fields = BonusFieldsSection(right, title="Achievement Bonus")

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(bottom, text="Save and Close", command=self._save_and_close).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()
        if self.entries:
            self._select_index(0)
        else:
            self.bonus_fields.load_bonus(_default_bonus_payload())

    def _entry_label(self, index: int, entry: dict) -> str:
        return f"{index + 1}. {_bonus_summary_text(entry)}"

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for idx, entry in enumerate(self.entries):
            self.listbox.insert(tk.END, self._entry_label(idx, entry))

    def _select_index(self, index: int):
        if index < 0 or index >= len(self.entries):
            self.selected_index = None
            return
        self.selected_index = index
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.bonus_fields.load_bonus(self.entries[index])

    def _on_select(self, _event=None):
        selected = self.listbox.curselection()
        if not selected:
            return
        self._select_index(int(selected[0]))

    def _new_entry(self):
        self.entries.append(_default_bonus_payload())
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
            self.bonus_fields.load_bonus(_default_bonus_payload())

    def _apply_current(self):
        if self.selected_index is None:
            self._new_entry()
        self.entries[self.selected_index] = self.bonus_fields.build_bonus()
        self._refresh_list()
        self._select_index(self.selected_index)

    def _save_and_close(self):
        if self.entries and self.selected_index is None:
            self._select_index(0)
        if self.selected_index is not None:
            self._apply_current()
        self.on_save(list(self.entries))
        self.destroy()
