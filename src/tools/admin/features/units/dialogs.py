import tkinter as tk
from tkinter import ttk

from .helpers import _safe_float


class AttributeBoundsEditorDialog(tk.Toplevel):
    ATTRIBUTE_FIELDS = [
        ("physicalPower", "Physical Power"),
        ("physicalStamina", "Physical Stamina"),
        ("physicalResistance", "Physical Resistance"),
        ("magicPower", "Magic Power"),
        ("magicStamina", "Magic Stamina"),
        ("magicResistance", "Magic Resistance"),
    ]

    def __init__(self, parent, initial_payload: dict, on_save):
        super().__init__(parent)
        self.title("Edit Attribute Bounds")
        self.resizable(False, False)
        self.on_save = on_save
        self.min_vars = {}
        self.max_vars = {}
        payload = initial_payload or {}
        min_attrs = payload.get("minAverageAttributes", {})
        max_attrs = payload.get("maxAverageAttributes", {})

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        min_frame = ttk.LabelFrame(container, text="Min Average Attributes")
        min_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        max_frame = ttk.LabelFrame(container, text="Max Average Attributes")
        max_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        for key, label in self.ATTRIBUTE_FIELDS:
            min_row = ttk.Frame(min_frame)
            min_row.pack(fill=tk.X, padx=6, pady=2)
            ttk.Label(min_row, text=label, width=18).pack(side=tk.LEFT)
            min_var = tk.StringVar(value=str(min_attrs.get(key, 5)))
            self.min_vars[key] = min_var
            ttk.Entry(min_row, textvariable=min_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

            max_row = ttk.Frame(max_frame)
            max_row.pack(fill=tk.X, padx=6, pady=2)
            ttk.Label(max_row, text=label, width=18).pack(side=tk.LEFT)
            max_var = tk.StringVar(value=str(max_attrs.get(key, 5)))
            self.max_vars[key] = max_var
            ttk.Entry(max_row, textvariable=max_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(8, 0), side=tk.BOTTOM)
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self.transient(parent)
        self.grab_set()

    def _collect_attributes(self, vars_by_key: dict) -> dict:
        return {
            "physicalPower": _safe_float(vars_by_key["physicalPower"].get(), 5.0),
            "physicalStamina": _safe_float(vars_by_key["physicalStamina"].get(), 5.0),
            "physicalResistance": _safe_float(vars_by_key["physicalResistance"].get(), 5.0),
            "magicPower": _safe_float(vars_by_key["magicPower"].get(), 5.0),
            "magicStamina": _safe_float(vars_by_key["magicStamina"].get(), 5.0),
            "magicResistance": _safe_float(vars_by_key["magicResistance"].get(), 5.0),
        }

    def _save(self):
        payload = {
            "minAverageAttributes": self._collect_attributes(self.min_vars),
            "maxAverageAttributes": self._collect_attributes(self.max_vars),
        }
        self.on_save(payload)
        self.destroy()
