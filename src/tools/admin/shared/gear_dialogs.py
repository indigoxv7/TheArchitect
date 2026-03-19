import json
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.CharacterUtil import EquipSlot
from .forms import _safe_int


class AttributesEditorDialog(tk.Toplevel):
    def __init__(self, parent, draft: dict, on_save):
        super().__init__(parent)
        self.title("Edit Attributes")
        self.resizable(False, False)
        self.on_save = on_save
        self.vars = {}

        fields = [
            ("physical_power", "Physical Power"),
            ("physical_stamina", "Physical Stamina"),
            ("physical_resistance", "Physical Resistance"),
            ("magic_power", "Magic Power"),
            ("magic_stamina", "Magic Stamina"),
            ("magic_resistance", "Magic Resistance"),
        ]

        for key, label in fields:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, padx=10, pady=3)
            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
            var = tk.StringVar(value=str(draft.get(key, 0)))
            self.vars[key] = var
            ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(self, text="Save", command=self._save).pack(fill=tk.X, padx=10, pady=8)

    def _save(self):
        payload = {key: _safe_int(var.get(), 0) for key, var in self.vars.items()}
        self.on_save(payload)
        self.destroy()


class GearEditorDialog(tk.Toplevel):
    SLOT_FIELDS = [
        ("head_item_id", "Head"),
        ("neck_item_id", "Neck"),
        ("body_item_id", "Body"),
        ("hands_item_id", "Hands"),
        ("ring_item_id", "Ring"),
        ("legs_item_id", "Legs"),
        ("feet_item_id", "Feet"),
        ("primary_weapon_item_id", "Primary Weapon"),
        ("offhand_item_id", "Offhand"),
    ]

    SLOT_FILTERS = {
        "head_item_id": EquipSlot.HEAD,
        "neck_item_id": EquipSlot.NECK,
        "body_item_id": EquipSlot.BODY,
        "hands_item_id": EquipSlot.HANDS,
        "ring_item_id": EquipSlot.RING,
        "legs_item_id": EquipSlot.LEGS,
        "feet_item_id": EquipSlot.FEET,
        "primary_weapon_item_id": EquipSlot.PRIMARY_WEAPON,
        "offhand_item_id": EquipSlot.OFFHAND,
    }

    def __init__(self, parent, draft: dict, item_service, on_save):
        super().__init__(parent)
        self.title("Edit Gear")
        self.geometry("700x520")
        self.item_service = item_service
        self.on_save = on_save

        self.slot_vars = {}
        self.slot_choice_labels = {}

        for key, label in self.SLOT_FIELDS:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, padx=10, pady=3)
            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
            current_item_id = draft.get(key, "")
            self.slot_choice_labels[key] = self._build_choices_for_slot(key, current_item_id)
            var = tk.StringVar(value=self._label_for_id(current_item_id))
            self.slot_vars[key] = var
            ttk.Combobox(
                row,
                state="readonly",
                textvariable=var,
                values=self.slot_choice_labels[key],
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        inv_frame = ttk.Frame(self)
        inv_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        ttk.Label(inv_frame, text="Inventory IDs").pack(anchor="w")
        self.inventory_text = tk.Text(inv_frame, height=8)
        self.inventory_text.pack(fill=tk.BOTH, expand=True)
        current_inventory = draft.get("inventory_item_ids", [])
        self.inventory_text.insert("1.0", json.dumps(current_inventory, indent=2, ensure_ascii=False))

        ttk.Button(self, text="Save", command=self._save).pack(fill=tk.X, padx=10, pady=8)

    def _build_choices_for_slot(self, slot_key: str, current_item_id: str) -> list[str]:
        allowed_slot = self.SLOT_FILTERS.get(slot_key)
        labels = ["<None>"]
        for item in self.item_service.list_items():
            if allowed_slot is not None and not item.can_equip_in(allowed_slot):
                continue
            labels.append(self.item_service.get_item_label(item))

        current_label = self._label_for_id(current_item_id)
        if current_label != "<None>" and current_label not in labels:
            labels.append(current_label)
        return labels

    def _label_for_id(self, item_id: str) -> str:
        if not item_id:
            return "<None>"
        item = self.item_service.get_item(item_id)
        if item is None:
            return "<None>"
        return self.item_service.get_item_label(item)

    def _id_from_label(self, label: str) -> str:
        label = str(label or "").strip()
        if label == "<None>":
            return ""
        return self.item_service.parse_item_id_from_label(label)

    def _save(self):
        payload = {}
        for key, _ in self.SLOT_FIELDS:
            payload[key] = self._id_from_label(self.slot_vars[key].get())

        try:
            inventory_ids = json.loads(self.inventory_text.get("1.0", tk.END).strip() or "[]")
            if not isinstance(inventory_ids, list):
                raise ValueError("Inventory must be a JSON list.")
        except Exception as exc:
            messagebox.showerror("Gear", f"Invalid inventory JSON: {exc}")
            return

        payload["inventory_item_ids"] = [str(i).strip() for i in inventory_ids if str(i).strip()]
        self.on_save(payload)
        self.destroy()
