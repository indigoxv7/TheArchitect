import json
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Items import Armor, Consumable, Item, Weapon
from src.domain.CharacterUtil import ConsumableKind, DamageType, EquipSlot, ItemType, PowerType
from src.tools.admin.shared.forms import _safe_float


class ItemEditorFrame(ttk.Frame):
    ITEM_CLASS_OPTIONS = ["Item", "Weapon", "Armor", "Consumable"]
    SLOT_OPTIONS = [slot.name for slot in EquipSlot]
    ITEM_TYPE_OPTIONS = [item_type.name for item_type in ItemType]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_item_id = None
        self._suspend_class_refresh = False

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
            values=["All"] + self.SLOT_OPTIONS,
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
            "itemClass": tk.StringVar(value="Item"),
            "slot": tk.StringVar(value=EquipSlot.NOT_EQUIPABLE.name),
            "powerLevel": tk.StringVar(value="0.0"),
            "itemType": tk.StringVar(value=ItemType.DEFAULT.name),
            "tier": tk.StringVar(value="0"),
            "durability": tk.StringVar(value="100"),
            "damageType": tk.StringVar(value="NONE"),
            "damageMin": tk.StringVar(value="0"),
            "damageMax": tk.StringVar(value="0"),
            "armorMultiplier": tk.StringVar(value="1.0"),
            "ignoreArmorFraction": tk.StringVar(value="0.0"),
            "penetrationBase": tk.StringVar(value="0.0"),
            "maxArmor": tk.StringVar(value="0"),
            "currentArmor": tk.StringVar(value="0"),
            "consumableKind": tk.StringVar(value=ConsumableKind.NONE.name),
            "effectPowerType": tk.StringVar(value=PowerType.CONSUMABLE_POWER.name),
            "effectPower": tk.StringVar(value="0"),
            "spellName": tk.StringVar(),
            "statBonuses": tk.StringVar(value="[]"),
        }

        common_frame = ttk.LabelFrame(self, text="Common")
        common_frame.pack(fill=tk.X, pady=6)
        self._row_entry(common_frame, "Name", self.vars["name"])
        self._row_combo(common_frame, "Item Class", self.vars["itemClass"], self.ITEM_CLASS_OPTIONS)
        self._row_combo(common_frame, "Slot", self.vars["slot"], self.SLOT_OPTIONS)
        self._row_entry(common_frame, "Power Level", self.vars["powerLevel"])
        self.item_type_combo = self._row_combo(common_frame, "Item Type", self.vars["itemType"], self.ITEM_TYPE_OPTIONS)
        self._row_entry(common_frame, "Tier", self.vars["tier"])
        self._row_entry(common_frame, "Stat Bonuses JSON", self.vars["statBonuses"])

        self.base_frame = ttk.LabelFrame(self, text="Generic Item")
        self._row_entry(self.base_frame, "Durability", self.vars["durability"])

        self.weapon_frame = ttk.LabelFrame(self, text="Weapon Stats")
        self._row_entry(self.weapon_frame, "Durability", self.vars["durability"])
        self._row_combo(self.weapon_frame, "Damage Type", self.vars["damageType"], ["NONE"] + [entry.name for entry in DamageType])
        self._row_entry(self.weapon_frame, "Damage Min", self.vars["damageMin"])
        self._row_entry(self.weapon_frame, "Damage Max", self.vars["damageMax"])
        self._row_entry(self.weapon_frame, "Armor Multiplier", self.vars["armorMultiplier"])
        self._row_entry(self.weapon_frame, "Ignore Armor Fraction", self.vars["ignoreArmorFraction"])
        self._row_entry(self.weapon_frame, "Penetration Base", self.vars["penetrationBase"])

        self.armor_frame = ttk.LabelFrame(self, text="Armor Stats")
        self._row_entry(self.armor_frame, "Max Armor", self.vars["maxArmor"])
        self._row_entry(self.armor_frame, "Current Armor", self.vars["currentArmor"])

        self.consumable_frame = ttk.LabelFrame(self, text="Consumable Stats")
        self._row_combo(self.consumable_frame, "Consumable Kind", self.vars["consumableKind"], [entry.name for entry in ConsumableKind])
        self._row_combo(self.consumable_frame, "Effect Power Type", self.vars["effectPowerType"], [entry.name for entry in PowerType])
        self._row_entry(self.consumable_frame, "Effect Power", self.vars["effectPower"])
        self._row_entry(self.consumable_frame, "Spell Name", self.vars["spellName"])
        self._row_combo(self.consumable_frame, "Damage Type", self.vars["damageType"], ["NONE"] + [entry.name for entry in DamageType])

        button_row = ttk.Frame(self)
        button_row.pack(fill=tk.X, pady=8)
        ttk.Button(button_row, text="Simulate", command=self._simulate).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(button_row, text="Save Item", command=self._save).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        self.vars["itemClass"].trace_add("write", self._on_item_class_changed)
        self._refresh_item_class_ui(force=True)

    def _row_entry(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _row_combo(self, parent, label, var, values):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        combo = ttk.Combobox(row, state="readonly", values=values, textvariable=var)
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return combo

    def _clear_filters(self):
        self.search_var.set("")
        self.slot_filter_var.set("All")
        self.pick_var.set("<New Item>")
        self.refresh_item_list(reset_form=False)

    def _clear_form(self):
        self.current_item_id = None
        self._suspend_class_refresh = True
        try:
            self.vars["name"].set("")
            self.vars["itemClass"].set("Item")
            self.vars["slot"].set(EquipSlot.NOT_EQUIPABLE.name)
            self.vars["powerLevel"].set("0.0")
            self.vars["itemType"].set(ItemType.DEFAULT.name)
            self.vars["tier"].set("0")
            self.vars["durability"].set("100")
            self.vars["damageType"].set("NONE")
            self.vars["damageMin"].set("0")
            self.vars["damageMax"].set("0")
            self.vars["armorMultiplier"].set("1.0")
            self.vars["ignoreArmorFraction"].set("0.0")
            self.vars["penetrationBase"].set("0.0")
            self.vars["maxArmor"].set("0")
            self.vars["currentArmor"].set("0")
            self.vars["consumableKind"].set(ConsumableKind.NONE.name)
            self.vars["effectPowerType"].set(PowerType.CONSUMABLE_POWER.name)
            self.vars["effectPower"].set("0")
            self.vars["spellName"].set("")
            self.vars["statBonuses"].set("[]")
        finally:
            self._suspend_class_refresh = False
        self._refresh_item_class_ui(force=True)

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

    def _item_class_for_item(self, item) -> str:
        if isinstance(item, Weapon):
            return "Weapon"
        if isinstance(item, Armor):
            return "Armor"
        if isinstance(item, Consumable):
            return "Consumable"
        return "Item"

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
        self._suspend_class_refresh = True
        try:
            self.vars["itemClass"].set(self._item_class_for_item(item))
            self.vars["name"].set(data.get("name", ""))
            self.vars["slot"].set(data.get("slot", EquipSlot.NOT_EQUIPABLE.name))
            self.vars["powerLevel"].set(str(data.get("powerLevel", 0.0)))
            self.vars["itemType"].set(data.get("itemType", ItemType.DEFAULT.name))
            self.vars["tier"].set(str(data.get("tier", 0)))
            self.vars["durability"].set(str(data.get("durability", 100)))
            self.vars["damageType"].set(data.get("damageType", ["NONE"])[0] if data.get("damageType") else "NONE")
            self.vars["damageMin"].set(str(data.get("damageMin", 0)))
            self.vars["damageMax"].set(str(data.get("damageMax", 0)))
            self.vars["armorMultiplier"].set(str(data.get("armorMultiplier", 1.0)))
            self.vars["ignoreArmorFraction"].set(str(data.get("ignoreArmorFraction", 0.0)))
            self.vars["penetrationBase"].set(str(data.get("penetrationBase", 0.0)))
            self.vars["maxArmor"].set(str(data.get("maxArmor", 0)))
            self.vars["currentArmor"].set(str(data.get("currentArmor", data.get("durability", 0))))
            self.vars["consumableKind"].set(data.get("consumableKind", ConsumableKind.NONE.name))
            self.vars["effectPowerType"].set(power.get("powerType", PowerType.CONSUMABLE_POWER.name))
            self.vars["effectPower"].set(str(power.get("power", 0)))
            self.vars["spellName"].set(power.get("spellName", ""))
            self.vars["statBonuses"].set(json.dumps(data.get("statBonuses", []), ensure_ascii=False))
        finally:
            self._suspend_class_refresh = False
        self._refresh_item_class_ui(force=True)

    def _on_item_class_changed(self, *_args):
        if self._suspend_class_refresh:
            return
        self._refresh_item_class_ui(force=False)

    def _refresh_item_class_ui(self, force: bool):
        item_class = self.vars["itemClass"].get() or "Item"
        for frame in (self.base_frame, self.weapon_frame, self.armor_frame, self.consumable_frame):
            frame.pack_forget()

        if item_class == "Weapon":
            self.item_type_combo["values"] = [ItemType.MELEE_WEAPON.name, ItemType.MELEE_THROWABLE.name, ItemType.RANGED_WEAPON.name]
            if force or self.vars["itemType"].get() not in self.item_type_combo["values"]:
                self.vars["itemType"].set(ItemType.MELEE_WEAPON.name)
            if force and self.vars["slot"].get() not in {EquipSlot.PRIMARY_WEAPON.name, EquipSlot.OFFHAND.name}:
                self.vars["slot"].set(EquipSlot.PRIMARY_WEAPON.name)
            self.weapon_frame.pack(fill=tk.X, pady=6)
        elif item_class == "Armor":
            self.item_type_combo["values"] = [ItemType.ARMOR.name]
            self.vars["itemType"].set(ItemType.ARMOR.name)
            if force and self.vars["slot"].get() in {EquipSlot.NOT_EQUIPABLE.name, EquipSlot.PRIMARY_WEAPON.name}:
                self.vars["slot"].set(EquipSlot.BODY.name)
            self.armor_frame.pack(fill=tk.X, pady=6)
        elif item_class == "Consumable":
            self.item_type_combo["values"] = [ItemType.CONSUMABLE.name]
            self.vars["itemType"].set(ItemType.CONSUMABLE.name)
            self.vars["slot"].set(EquipSlot.NOT_EQUIPABLE.name)
            self.consumable_frame.pack(fill=tk.X, pady=6)
        else:
            self.item_type_combo["values"] = [ItemType.DEFAULT.name]
            self.vars["itemType"].set(ItemType.DEFAULT.name)
            self.base_frame.pack(fill=tk.X, pady=6)

    def _build_payload(self):
        stat_bonuses = json.loads(self.vars["statBonuses"].get() or "[]")
        if not isinstance(stat_bonuses, list):
            raise ValueError("Stat bonuses must be a JSON array.")

        item_class = self.vars["itemClass"].get() or "Item"
        payload = {
            "name": self.vars["name"].get().strip(),
            "slot": self.vars["slot"].get(),
            "tier": int(self.vars["tier"].get() or 0),
            "powerLevel": _safe_float(self.vars["powerLevel"].get(), 0.0),
            "statBonuses": stat_bonuses,
            "itemClass": item_class,
        }

        if item_class == "Weapon":
            damage = self.vars["damageType"].get()
            payload.update(
                {
                    "itemType": self.vars["itemType"].get(),
                    "durability": _safe_float(self.vars["durability"].get(), 100.0),
                    "damageType": [] if damage == "NONE" else [damage],
                    "damageMin": _safe_float(self.vars["damageMin"].get(), 0.0),
                    "damageMax": _safe_float(self.vars["damageMax"].get(), 0.0),
                    "armorMultiplier": _safe_float(self.vars["armorMultiplier"].get(), 1.0),
                    "ignoreArmorFraction": _safe_float(self.vars["ignoreArmorFraction"].get(), 0.0),
                    "penetrationBase": _safe_float(self.vars["penetrationBase"].get(), 0.0),
                }
            )
        elif item_class == "Armor":
            current_armor = _safe_float(self.vars["currentArmor"].get(), 0.0)
            payload.update(
                {
                    "itemType": ItemType.ARMOR.name,
                    "durability": current_armor,
                    "maxArmor": _safe_float(self.vars["maxArmor"].get(), current_armor),
                    "currentArmor": current_armor,
                }
            )
        elif item_class == "Consumable":
            damage = self.vars["damageType"].get()
            payload.update(
                {
                    "itemType": ItemType.CONSUMABLE.name,
                    "consumableKind": self.vars["consumableKind"].get(),
                    "effectPowerType": self.vars["effectPowerType"].get(),
                    "effectPower": _safe_float(self.vars["effectPower"].get(), 0.0),
                    "spellName": self.vars["spellName"].get().strip(),
                    "damageType": [] if damage == "NONE" else [damage],
                }
            )
        else:
            payload.update(
                {
                    "itemType": ItemType.DEFAULT.name,
                    "durability": _safe_float(self.vars["durability"].get(), 100.0),
                }
            )
        return payload

    def _simulate(self):
        try:
            payload = self._build_payload()
            item = Item.from_dict(payload)
            result = self.app.power_rating_service.simulate_item_power_level(item)
            self.vars["powerLevel"].set(str(result.recommendedPowerLevel))
            messagebox.showinfo(
                "Item Simulation",
                f"Recommended power level: {result.recommendedPowerLevel:.2f}\n"
                f"Simulated equivalent: {result.simulatedPowerEquivalent:.2f}\n"
                f"Win rate: {result.winRate * 100:.1f}% over {result.sampleCount} duels.",
            )
        except Exception as exc:
            messagebox.showerror("Item Simulation", f"Failed to simulate item: {exc}")

    def _save(self):
        try:
            payload = self._build_payload()
            if self.current_item_id:
                self.app.item_service.edit_item_from_patch(self.current_item_id, payload)
            else:
                self.app.item_service.create_item_from_dict(payload)
            messagebox.showinfo("Item Editor", "Item saved.")
            self.refresh_item_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Item Editor", f"Failed to save item: {exc}")
