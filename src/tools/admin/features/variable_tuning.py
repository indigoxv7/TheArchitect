import tkinter as tk
from tkinter import messagebox, ttk

from src.config.tuning import get_tuning_registry


def _coerce_value(raw_value: str, value_type: str):
    text = str(raw_value or "").strip()
    if value_type == "int":
        return int(text)
    if value_type == "float":
        return float(text)
    return text


class VariableTuningFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.registry = get_tuning_registry()
        self.section_vars: dict[str, dict[str, tk.StringVar]] = {}
        self.section_fields: dict[str, list[dict]] = {}
        self.section_messages: dict[str, tk.StringVar] = {}
        self.section_paths: dict[str, tk.StringVar] = {}

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Variable Tuning", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        intro = (
            "These values are loaded from JSON files and applied live. "
            "Save changes here, then rerun a simulation or keep testing without restarting the app."
        )
        ttk.Label(self, text=intro, wraplength=860, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 8))

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(actions, text="Save All", command=self.save_all).pack(side=tk.LEFT)
        ttk.Button(actions, text="Reload From Disk", command=self.reload_from_disk).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Reset Current Section", command=self.reset_current_section).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, wraplength=860, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 8))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.section_frames: dict[str, ttk.Frame] = {}
        for category in self.registry.list_categories():
            schema = self.registry.get_category_schema(category)
            frame = ttk.Frame(self.notebook)
            self.section_frames[category] = frame
            self.notebook.add(frame, text=schema.get("title", category))
            self._build_section(frame, category, schema)

        self.reload_from_disk(show_message=False)

    def _build_section(self, frame: ttk.Frame, category: str, schema: dict):
        description = str(schema.get("description", "") or "")
        if description:
            ttk.Label(frame, text=description, wraplength=840, justify=tk.LEFT).pack(fill=tk.X, pady=(4, 8))

        path_var = tk.StringVar(value=self.registry.get_category_path(category))
        self.section_paths[category] = path_var
        path_row = ttk.Frame(frame)
        path_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(path_row, text="File", width=18).pack(side=tk.LEFT)
        ttk.Entry(path_row, textvariable=path_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)

        message_var = tk.StringVar(value="")
        self.section_messages[category] = message_var
        ttk.Label(frame, textvariable=message_var, wraplength=840, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 8))

        fields = list(schema.get("fields", []) or [])
        self.section_fields[category] = fields
        self.section_vars[category] = {}
        if not fields:
            ttk.Label(frame, text="No faction-level tuning variables are defined yet.", justify=tk.LEFT).pack(
                fill=tk.X, pady=8
            )
            return

        for field in fields:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=field.get("label", field.get("key", "")), width=30).pack(side=tk.LEFT)
            var = tk.StringVar(value=str(field.get("default", "")))
            self.section_vars[category][field["key"]] = var
            ttk.Entry(row, textvariable=var, width=18).pack(side=tk.LEFT, padx=(0, 8))
            ttk.Label(
                row,
                text=str(field.get("description", "") or ""),
                wraplength=520,
                justify=tk.LEFT,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _current_category(self) -> str | None:
        selected = self.notebook.select()
        if not selected:
            return None
        selected_index = self.notebook.index(selected)
        categories = self.registry.list_categories()
        if 0 <= selected_index < len(categories):
            return categories[selected_index]
        return None

    def reload_from_disk(self, show_message: bool = True):
        sections = self.registry.reload_all()
        for category in self.registry.list_categories():
            section = sections.get(category, {})
            for field in self.section_fields.get(category, []):
                key = field["key"]
                if key in self.section_vars.get(category, {}):
                    self.section_vars[category][key].set(str(section.get(key, field.get("default", ""))))
            self.section_messages[category].set(f"Loaded {len(self.section_fields.get(category, []))} values.")
            self.section_paths[category].set(self.registry.get_category_path(category))
        self.status_var.set("Reloaded tuning values from disk.")
        if show_message:
            messagebox.showinfo("Variable Tuning", "Reloaded tuning values from disk.")

    def _build_section_payload(self, category: str) -> dict:
        payload = self.registry.get_section(category)
        for field in self.section_fields.get(category, []):
            key = field["key"]
            raw_value = self.section_vars.get(category, {}).get(key)
            if raw_value is None:
                continue
            payload[key] = _coerce_value(raw_value.get(), field.get("type", "float"))
        return payload

    def save_all(self):
        try:
            for category in self.registry.list_categories():
                self.registry.save_section(category, self._build_section_payload(category))
                self.section_messages[category].set("Saved.")
            self.status_var.set("Saved all tuning sections. New calculations will use the updated values immediately.")
            messagebox.showinfo("Variable Tuning", "Saved all tuning values.")
        except Exception as exc:
            messagebox.showerror("Variable Tuning", f"Failed to save tuning values: {exc}")

    def reset_current_section(self):
        category = self._current_category()
        if not category:
            return
        try:
            self.registry.reset_section(category)
            section = self.registry.get_section(category)
            for field in self.section_fields.get(category, []):
                self.section_vars[category][field["key"]].set(str(section.get(field["key"], field.get("default", ""))))
            self.section_messages[category].set("Reset to defaults.")
            self.status_var.set(
                f"Reset {self.registry.get_category_schema(category).get('title', category)} to defaults."
            )
        except Exception as exc:
            messagebox.showerror("Variable Tuning", f"Failed to reset section: {exc}")
