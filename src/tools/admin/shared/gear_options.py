import tkinter as tk
from tkinter import ttk

from src.domain.gear_options import GearOptions
from src.tools.admin.shared.pickers import ItemSelectDialog


GEAR_OPTION_FIELDS = GearOptions.FIELD_SPECS
NONE_OPTION_ID = GearOptions.NONE_OPTION_ID
NONE_OPTION_LABEL = "<Nothing>"


def default_gear_options_payload() -> dict[str, list[str]]:
    return GearOptions.empty_payload()


def normalize_gear_options_payload(payload) -> dict[str, list[str]]:
    normalized = default_gear_options_payload()
    if not isinstance(payload, dict):
        return normalized

    for field_name, _label, _slot in GEAR_OPTION_FIELDS:
        values = payload.get(field_name, [])
        if not isinstance(values, list):
            continue
        clean_values = []
        for value in values:
            item_id = str(value or "").strip()
            if item_id == NONE_OPTION_ID and item_id not in clean_values:
                clean_values.append(item_id)
            elif item_id and item_id not in clean_values:
                clean_values.append(item_id)
        normalized[field_name] = clean_values
    return normalized


def build_gear_options_summary(item_service, payload: dict[str, list[str]]) -> str:
    normalized = normalize_gear_options_payload(payload)
    lines = []
    for field_name, label, _slot in GEAR_OPTION_FIELDS:
        item_labels = []
        for item_id in normalized[field_name]:
            if item_id == NONE_OPTION_ID:
                item_labels.append(NONE_OPTION_LABEL)
            else:
                item = item_service.get_item(item_id)
                item_labels.append(item_service.get_item_label(item) if item is not None else f"Unknown [{item_id}]")
        if item_labels:
            lines.append(f"{label}: {', '.join(item_labels)}")
        else:
            lines.append(f"{label}: <None>")
    return "\n".join(lines)


class GearOptionsEditorDialog(tk.Toplevel):
    def __init__(self, parent, item_service, initial_payload: dict[str, list[str]], on_save):
        super().__init__(parent)
        self.title("Edit Gear Options")
        self.geometry("860x900")
        self.item_service = item_service
        self.on_save = on_save
        self.draft = normalize_gear_options_payload(initial_payload)
        self.listboxes = {}

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        for field_name, label, allowed_slot in GEAR_OPTION_FIELDS:
            section = ttk.LabelFrame(container, text=label)
            section.pack(fill=tk.BOTH, expand=False, pady=4)

            listbox = tk.Listbox(section, height=3)
            listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 4))
            self.listboxes[field_name] = listbox

            buttons = ttk.Frame(section)
            buttons.pack(fill=tk.X, padx=6, pady=(0, 6))
            ttk.Button(
                buttons,
                text="Add",
                command=lambda key=field_name, slot=allowed_slot: self._add_item(key, slot),
            ).pack(side=tk.LEFT)
            if allowed_slot is not None:
                ttk.Button(
                    buttons,
                    text="Add Nothing",
                    command=lambda key=field_name: self._add_nothing_option(key),
                ).pack(side=tk.LEFT, padx=6)
            ttk.Button(
                buttons,
                text="Remove Selected",
                command=lambda key=field_name: self._remove_selected(key),
            ).pack(side=tk.LEFT, padx=6 if allowed_slot is None else 0)
            ttk.Button(
                buttons,
                text="Clear",
                command=lambda key=field_name: self._clear_field(key),
            ).pack(side=tk.LEFT)

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_all()
        self.transient(parent)
        self.grab_set()

    def _refresh_all(self):
        for field_name, _label, _slot in GEAR_OPTION_FIELDS:
            self._refresh_field(field_name)

    def _refresh_field(self, field_name: str):
        listbox = self.listboxes[field_name]
        listbox.delete(0, tk.END)
        for item_id in self.draft[field_name]:
            if item_id == NONE_OPTION_ID:
                label = NONE_OPTION_LABEL
            else:
                item = self.item_service.get_item(item_id)
                label = self.item_service.get_item_label(item) if item is not None else f"Unknown [{item_id}]"
            listbox.insert(tk.END, label)

    def _add_item(self, field_name: str, allowed_slot):
        allowed_slots = [allowed_slot] if allowed_slot is not None else None

        def _on_select(item_id: str):
            if item_id not in self.draft[field_name]:
                self.draft[field_name].append(item_id)
                self._refresh_field(field_name)

        ItemSelectDialog(self, self.item_service, _on_select, allowed_slots=allowed_slots)

    def _add_nothing_option(self, field_name: str):
        if NONE_OPTION_ID not in self.draft[field_name]:
            self.draft[field_name].append(NONE_OPTION_ID)
            self._refresh_field(field_name)

    def _remove_selected(self, field_name: str):
        listbox = self.listboxes[field_name]
        selection = listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.draft[field_name]):
            return
        self.draft[field_name].pop(index)
        self._refresh_field(field_name)

    def _clear_field(self, field_name: str):
        self.draft[field_name] = []
        self._refresh_field(field_name)

    def _save(self):
        self.on_save(normalize_gear_options_payload(self.draft))
        self.destroy()
