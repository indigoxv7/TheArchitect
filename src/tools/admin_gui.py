import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Character import HealthState
from src.domain.CharacterUtil import (
    Affinities,
    Attribute,
    BonusType,
    DamageType,
    EquipSlot,
    ItemType,
    PowerType,
)
from src.domain.Spells import AffinityTypes
from src.domain.character_io import character_to_state


def _parse_label_id(label: str) -> str:
    text = str(label or "").strip()
    if text.endswith("]") and "[" in text:
        return text[text.rfind("[") + 1 : -1].strip()
    return text


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default

class AdminEditorApp:
    def __init__(self, spell_service, item_service, character_service):
        self.spell_service = spell_service
        self.item_service = item_service
        self.character_service = character_service

        self.root = tk.Tk()
        self.root.title("TheArchitect Admin Editor")
        self.root.geometry("950x800")

        self.container = ttk.Frame(self.root, padding=12)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.home_frame = ttk.Frame(self.container)
        self.spell_frame = SpellEditorFrame(self.container, self)
        self.item_frame = ItemEditorFrame(self.container, self)
        self.character_frame = CharacterEditorFrame(self.container, self)

        self._build_home()
        self.show_home()

    def _build_home(self):
        ttk.Label(self.home_frame, text="Admin Editor Menu", font=("Segoe UI", 16, "bold")).pack(pady=20)
        ttk.Button(self.home_frame, text="Edit Spells", command=self.show_spell_editor).pack(fill=tk.X, pady=6)
        ttk.Button(self.home_frame, text="Edit Items", command=self.show_item_editor).pack(fill=tk.X, pady=6)
        ttk.Button(self.home_frame, text="Edit Characters", command=self.show_character_editor).pack(fill=tk.X, pady=6)

    def _show(self, frame):
        for child in (self.home_frame, self.spell_frame, self.item_frame, self.character_frame):
            child.pack_forget()
        frame.pack(fill=tk.BOTH, expand=True)

    def show_home(self):
        self._show(self.home_frame)

    def show_spell_editor(self):
        self.spell_frame.refresh_spell_list(reset_form=True)
        self._show(self.spell_frame)

    def show_item_editor(self):
        self.item_frame.refresh_item_list(reset_form=True)
        self._show(self.item_frame)

    def show_character_editor(self):
        self.character_frame.refresh_character_list(reset_form=True)
        self._show(self.character_frame)

    def run(self):
        self.root.mainloop()


class SpellEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_name = None

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Spell Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_spell_list(reset_form=False))

        filter_row = ttk.Frame(self)
        filter_row.pack(fill=tk.X, pady=4)
        ttk.Label(filter_row, text="Filter Affinity", width=18).pack(side=tk.LEFT)
        self.affinity_filter_var = tk.StringVar(value="All")
        self.affinity_filter = ttk.Combobox(
            filter_row,
            state="readonly",
            textvariable=self.affinity_filter_var,
            values=["All"] + [a.value for a in AffinityTypes],
        )
        self.affinity_filter.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(filter_row, text="Apply Filter", command=lambda: self.refresh_spell_list(reset_form=False)).pack(side=tk.LEFT, padx=6)
        ttk.Button(filter_row, text="Clear", command=self._clear_filters).pack(side=tk.LEFT)

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Spell", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Spell>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.vars = {
            "name": tk.StringVar(),
            "level": tk.StringVar(),
            "power": tk.StringVar(),
            "affinity": tk.StringVar(value=AffinityTypes.MANA.value),
            "casting_time": tk.StringVar(),
            "range": tk.StringVar(),
            "verbal": tk.StringVar(value="False"),
            "somatic": tk.StringVar(value="False"),
            "material": tk.StringVar(),
            "duration": tk.StringVar(),
            "description": tk.StringVar(),
            "higher_level": tk.StringVar(),
        }

        fields = [
            ("Name", "name"),
            ("Level", "level"),
            ("Power", "power"),
            ("Casting Time", "casting_time"),
            ("Range", "range"),
            ("Material", "material"),
            ("Duration", "duration"),
            ("Description", "description"),
            ("Higher Level", "higher_level"),
        ]
        for label, key in fields:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=self.vars[key]).pack(side=tk.LEFT, fill=tk.X, expand=True)

        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Affinity", width=18).pack(side=tk.LEFT)
        ttk.Combobox(row, state="readonly", values=[a.value for a in AffinityTypes], textvariable=self.vars["affinity"]).pack(side=tk.LEFT, fill=tk.X, expand=True)

        for label, key in [("Verbal", "verbal"), ("Somatic", "somatic")]:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
            ttk.Combobox(row, state="readonly", values=["True", "False"], textvariable=self.vars[key]).pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(self, text="Save Spell", command=self._save).pack(fill=tk.X, pady=8)

    def _clear_filters(self):
        self.search_var.set("")
        self.affinity_filter_var.set("All")
        self.pick_var.set("<New Spell>")
        self.refresh_spell_list(reset_form=False)

    def _clear_form(self):
        self.current_name = None
        for key, var in self.vars.items():
            if key in {"verbal", "somatic", "affinity"}:
                continue
            var.set("")
        self.vars["affinity"].set(AffinityTypes.MANA.value)
        self.vars["verbal"].set("False")
        self.vars["somatic"].set("False")

    def _filtered_spells(self):
        query = self.search_var.get().strip().lower()
        affinity_filter = self.affinity_filter_var.get().strip()

        spells = self.app.spell_service.list_spells()
        result = []
        for spell in spells:
            affinity_value = spell.affinity.value if hasattr(spell.affinity, "value") else str(spell.affinity)
            if affinity_filter and affinity_filter != "All" and affinity_value != affinity_filter:
                continue
            if query and query not in spell.name.lower():
                continue
            result.append(spell)
        return result

    def refresh_spell_list(self, reset_form: bool):
        names = ["<New Spell>"] + [spell.name for spell in self._filtered_spells()]
        self.pick["values"] = names
        if reset_form:
            self.pick_var.set("<New Spell>")
            self._clear_form()
        elif self.pick_var.get() not in names:
            self.pick_var.set("<New Spell>")

    def _on_pick(self, _evt=None):
        name = self.pick.get().strip()
        if name == "<New Spell>":
            self._clear_form()
            return

        spell = self.app.spell_service.get_spell(name)
        if spell is None:
            return

        d = spell.to_dict()
        c = d.get("components", {})
        self.current_name = name
        self.vars["name"].set(d.get("name", ""))
        self.vars["level"].set(str(d.get("level", 0)))
        self.vars["power"].set(str(d.get("power", "")))
        self.vars["affinity"].set(str(d.get("affinity", AffinityTypes.MANA.value)))
        self.vars["casting_time"].set(str(d.get("casting_time", "")))
        self.vars["range"].set(str(d.get("range", "")))
        self.vars["material"].set(str(c.get("material", False)))
        self.vars["duration"].set(str(d.get("duration", "")))
        self.vars["description"].set(d.get("description", ""))
        self.vars["higher_level"].set(d.get("higher_level", "") or "")
        self.vars["verbal"].set(str(bool(c.get("verbal", False))))
        self.vars["somatic"].set(str(bool(c.get("somatic", False))))

    def _save(self):
        payload = {
            "name": self.vars["name"].get().strip(),
            "level": int(self.vars["level"].get() or 0),
            "power": self.vars["power"].get().strip(),
            "affinity": self.vars["affinity"].get().strip(),
            "casting_time": self.vars["casting_time"].get().strip(),
            "range": self.vars["range"].get().strip(),
            "components": {
                "verbal": self.vars["verbal"].get() == "True",
                "somatic": self.vars["somatic"].get() == "True",
                "material": self.vars["material"].get().strip() or False,
            },
            "duration": self.vars["duration"].get().strip(),
            "description": self.vars["description"].get().strip(),
            "higher_level": self.vars["higher_level"].get().strip(),
        }
        try:
            if self.current_name:
                self.app.spell_service.edit_spell_from_patch(self.current_name, payload)
            else:
                self.app.spell_service.create_spell_from_dict(payload)
            messagebox.showinfo("Spell Editor", "Spell saved.")
            self.refresh_spell_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Spell Editor", f"Failed to save spell: {exc}")


class ItemEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_item_id = None

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Item Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_item_list(reset_form=False))

        filter_row = ttk.Frame(self)
        filter_row.pack(fill=tk.X, pady=4)
        ttk.Label(filter_row, text="Filter Slot", width=18).pack(side=tk.LEFT)
        self.slot_filter_var = tk.StringVar(value="All")
        self.slot_filter = ttk.Combobox(
            filter_row,
            state="readonly",
            textvariable=self.slot_filter_var,
            values=["All"] + [e.name for e in EquipSlot],
        )
        self.slot_filter.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(filter_row, text="Apply Filter", command=lambda: self.refresh_item_list(reset_form=False)).pack(side=tk.LEFT, padx=6)
        ttk.Button(filter_row, text="Clear", command=self._clear_filters).pack(side=tk.LEFT)

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Item", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Item>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.vars = {
            "name": tk.StringVar(),
            "slot": tk.StringVar(value=EquipSlot.NOT_EQUIPABLE.name),
            "tier": tk.StringVar(value="0"),
            "durability": tk.StringVar(value="100"),
            "itemType": tk.StringVar(value=ItemType.DEFAULT.name),
            "damageType": tk.StringVar(value="NONE"),
            "powerType": tk.StringVar(value="NONE"),
            "power": tk.StringVar(value="0"),
            "spellName": tk.StringVar(),
            "statBonuses": tk.StringVar(value="[]"),
        }
        self._row_entry("Name", self.vars["name"])
        self._row_combo("Slot", self.vars["slot"], [e.name for e in EquipSlot])
        self._row_entry("Tier", self.vars["tier"])
        self._row_entry("Durability", self.vars["durability"])
        self._row_combo("Item Type", self.vars["itemType"], [e.name for e in ItemType])
        self._row_combo("Damage Type", self.vars["damageType"], ["NONE"] + [e.name for e in DamageType])
        self._row_combo("Power Type", self.vars["powerType"], ["NONE"] + [e.name for e in PowerType])
        self._row_entry("Power Value", self.vars["power"])
        self._row_entry("Power Spell Name", self.vars["spellName"])
        self._row_entry("Stat Bonuses JSON", self.vars["statBonuses"])
        ttk.Button(self, text="Save Item", command=self._save).pack(fill=tk.X, pady=8)

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

    def _clear_filters(self):
        self.search_var.set("")
        self.slot_filter_var.set("All")
        self.pick_var.set("<New Item>")
        self.refresh_item_list(reset_form=False)

    def _clear_form(self):
        self.current_item_id = None
        self.vars["name"].set("")
        self.vars["slot"].set(EquipSlot.NOT_EQUIPABLE.name)
        self.vars["tier"].set("0")
        self.vars["durability"].set("100")
        self.vars["itemType"].set(ItemType.DEFAULT.name)
        self.vars["damageType"].set("NONE")
        self.vars["powerType"].set("NONE")
        self.vars["power"].set("0")
        self.vars["spellName"].set("")
        self.vars["statBonuses"].set("[]")

    def _filtered_items(self):
        query = self.search_var.get().strip().lower()
        slot_filter = self.slot_filter_var.get().strip()

        items = self.app.item_service.list_items()
        result = []
        for item in items:
            slot_name = item.slot.name if hasattr(item.slot, "name") else str(item.slot)
            if slot_filter and slot_filter != "All" and slot_name != slot_filter:
                continue
            label = self.app.item_service.get_item_label(item).lower()
            if query and query not in label:
                continue
            result.append(item)
        return result

    def refresh_item_list(self, reset_form: bool):
        labels = ["<New Item>"] + [self.app.item_service.get_item_label(item) for item in self._filtered_items()]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<New Item>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<New Item>")

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Item>":
            self._clear_form()
            return

        item_id = self.app.item_service.parse_item_id_from_label(selected)
        item = self.app.item_service.get_item(item_id)
        if item is None:
            return

        data = item.to_dict()
        power = data.get("itemPower", [{}])[0] if data.get("itemPower") else {}
        self.current_item_id = item.itemId
        self.vars["name"].set(data.get("name", ""))
        self.vars["slot"].set(data.get("slot", EquipSlot.NOT_EQUIPABLE.name))
        self.vars["tier"].set(str(data.get("tier", 0)))
        self.vars["durability"].set(str(data.get("durability", 100)))
        self.vars["itemType"].set(data.get("itemType", ItemType.DEFAULT.name))
        self.vars["damageType"].set(data.get("damageType", ["NONE"])[0] if data.get("damageType") else "NONE")
        self.vars["powerType"].set(power.get("powerType", "NONE"))
        self.vars["power"].set(str(power.get("power", 0)))
        self.vars["spellName"].set(power.get("spellName", ""))
        self.vars["statBonuses"].set(json.dumps(data.get("statBonuses", []), ensure_ascii=False))

    def _save(self):
        try:
            power_type = self.vars["powerType"].get()
            item_power = []
            if power_type != "NONE":
                item_power.append(
                    {
                        "powerType": power_type,
                        "power": int(self.vars["power"].get() or 0),
                        "spellName": self.vars["spellName"].get().strip(),
                    }
                )

            damage = self.vars["damageType"].get()
            stat_bonuses = json.loads(self.vars["statBonuses"].get() or "[]")

            payload = {
                "name": self.vars["name"].get().strip(),
                "slot": self.vars["slot"].get(),
                "tier": int(self.vars["tier"].get() or 0),
                "durability": int(self.vars["durability"].get() or 100),
                "itemType": self.vars["itemType"].get(),
                "itemPower": item_power,
                "damageType": [] if damage == "NONE" else [damage],
                "statBonuses": stat_bonuses,
            }
            if self.current_item_id:
                self.app.item_service.edit_item_from_patch(self.current_item_id, payload)
            else:
                self.app.item_service.create_item_from_dict(payload)
            messagebox.showinfo("Item Editor", "Item saved.")
            self.refresh_item_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Item Editor", f"Failed to save item: {exc}")



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
        "primary_weapon_item_id": EquipSlot.HANDS,
        "offhand_item_id": EquipSlot.HANDS,
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
            if allowed_slot is not None and item.slot != allowed_slot:
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

class JsonListEditorDialog(tk.Toplevel):
    def __init__(self, parent, title: str, initial_list: list, on_save):
        super().__init__(parent)
        self.title(title)
        self.geometry("760x520")
        self.on_save = on_save

        ttk.Label(self, text="Edit JSON list").pack(anchor="w", padx=10, pady=(8, 0))
        self.text = tk.Text(self, wrap=tk.NONE)
        self.text.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.text.insert("1.0", json.dumps(initial_list or [], indent=2, ensure_ascii=False))

        ttk.Button(self, text="Save", command=self._save).pack(fill=tk.X, padx=10, pady=8)

    def _save(self):
        raw = self.text.get("1.0", tk.END).strip() or "[]"
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError("Value must be a JSON list.")
        except Exception as exc:
            messagebox.showerror("JSON Editor", f"Invalid list JSON: {exc}")
            return
        self.on_save(parsed)
        self.destroy()


class CharacterEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_character_id = None

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
            "level": tk.StringVar(value="0"),
            "raceTier": tk.StringVar(value="Tier I"),
            "party": tk.StringVar(value="0"),
            "health": tk.StringVar(value="100"),
            "healthState": tk.StringVar(value=HealthState.HEALTHY.name),
        }
        self._row_entry("Name", self.vars["name"])
        self._row_entry("Level", self.vars["level"])
        self._row_entry("Race Tier", self.vars["raceTier"])
        self._row_entry("Party", self.vars["party"])
        self._row_entry("Health", self.vars["health"])
        self._row_combo("Health State", self.vars["healthState"], [e.name for e in HealthState])

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, pady=8)
        ttk.Button(actions, text="Edit Attributes", command=self._edit_attributes).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Edit Gear", command=self._edit_gear).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Edit Bonus (Buff List)", command=self._edit_buffs).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Edit Achievements", command=self._edit_achievements).pack(side=tk.LEFT, padx=4)

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

    def _clear_form(self):
        self.current_character_id = None
        self.vars["name"].set("")
        self.vars["level"].set("0")
        self.vars["raceTier"].set("Tier I")
        self.vars["party"].set("0")
        self.vars["health"].set("100")
        self.vars["healthState"].set(HealthState.HEALTHY.name)
        self.attributes_draft = self._default_attributes()
        self.gear_draft = self._default_gear()
        self.buffs_draft = []
        self.achievements_draft = []
        self.spells_data = []
        self.general_skills_data = []
        self.stats_data = None
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

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Character>":
            self._clear_form()
            return
        character_id = _parse_label_id(selected)
        character = self.app.character_service.get_character(character_id)
        if character is None:
            return
        state = character_to_state(character)
        self.current_character_id = character_id
        self.vars["name"].set(state.get("name", ""))
        self.vars["level"].set(str(state.get("level", 0)))
        self.vars["raceTier"].set(str(state.get("raceTier", "Tier I")))
        self.vars["party"].set(str(state.get("party", 0)))
        self.vars["health"].set(str(state.get("health", 100)))
        self.vars["healthState"].set(str(state.get("healthState", HealthState.HEALTHY.name)))
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
        self.stats_data = state.get("stats")
        self._refresh_summary()

    def _refresh_summary(self):
        lines = [
            "Attributes:",
            json.dumps(self.attributes_draft, indent=2, ensure_ascii=False),
            "",
            "Gear:",
            json.dumps(self.gear_draft, indent=2, ensure_ascii=False),
            "",
            f"Buff entries: {len(self.buffs_draft)}",
            f"Achievement entries: {len(self.achievements_draft)}",
        ]
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, "\n".join(lines))

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
        JsonListEditorDialog(self, "Edit Buff List", self.buffs_draft, self._on_buffs_saved)

    def _on_buffs_saved(self, payload):
        self.buffs_draft = payload
        self._refresh_summary()

    def _edit_achievements(self):
        JsonListEditorDialog(self, "Edit Achievement List", self.achievements_draft, self._on_achievements_saved)

    def _on_achievements_saved(self, payload):
        self.achievements_draft = payload
        self._refresh_summary()

    def _build_payload(self):
        return {
            "name": self.vars["name"].get().strip(),
            "level": _safe_int(self.vars["level"].get(), 0),
            "raceTier": self.vars["raceTier"].get().strip() or "Tier I",
            "party": _safe_int(self.vars["party"].get(), 0),
            "health": _safe_int(self.vars["health"].get(), 100),
            "healthState": self.vars["healthState"].get().strip() or HealthState.HEALTHY.name,
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
            "stats": self.stats_data,
        }

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


def start_admin_gui_thread(spell_service, item_service, character_service):
    def _run_gui():
        try:
            app = AdminEditorApp(spell_service, item_service, character_service)
            app.run()
        except Exception as exc:
            print(f"Admin GUI failed to start: {exc}")

    thread = threading.Thread(target=_run_gui, name="AdminEditorGUI", daemon=True)
    thread.start()
    return thread

