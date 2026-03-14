import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Character import HealthState
from src.domain.MainCharacter import CharacterInfo, MainCharacter
from src.domain.CharacterUtil import (
    Affinities,
    Attribute,
    BonusType,
    DamageType,
    EquipSlot,
    ItemType,
    PowerType,
    TitlePreference,
)
from src.domain.Spells import AffinityTypes
from src.domain.character_io import character_from_state, character_to_state
from src.tools.race_editor import RaceEditorFrame


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


BONUS_ATTRIBUTE_OPTIONS = ["NONE"] + [attribute.name for attribute in Attribute]


def _default_bonus_payload() -> dict:
    return {
        "bonusType": BonusType.FLAT.name,
        "attributeBonus": None,
        "affinities": None,
        "nanoMultiplier": 0.0,
        "reason": "",
        "permanent": False,
    }


def _normalize_bonus_payload(raw) -> dict:
    payload = _default_bonus_payload()
    if not isinstance(raw, dict):
        return payload

    bonus_type = str(raw.get("bonusType", BonusType.FLAT.name) or BonusType.FLAT.name).strip().upper()
    if bonus_type not in BonusType.__members__:
        bonus_type = BonusType.FLAT.name
    payload["bonusType"] = bonus_type

    attribute_bonus = raw.get("attributeBonus")
    if isinstance(attribute_bonus, dict):
        attr_name = str(attribute_bonus.get("attribute", "") or "").strip().upper()
        if attr_name in Attribute.__members__:
            payload["attributeBonus"] = {
                "attribute": attr_name,
                "bonus": _safe_int(attribute_bonus.get("bonus", 0), 0),
            }

    affinities = raw.get("affinities")
    if isinstance(affinities, dict):
        payload["affinities"] = {
            "chi": _safe_float(affinities.get("chi", 0.0), 0.0),
            "mana": _safe_float(affinities.get("mana", 0.0), 0.0),
            "psi": _safe_float(affinities.get("psi", 0.0), 0.0),
            "aether": _safe_float(affinities.get("aether", 0.0), 0.0),
        }

    payload["nanoMultiplier"] = _safe_float(raw.get("nanoMultiplier", 0.0), 0.0)
    payload["reason"] = str(raw.get("reason", "") or "")
    payload["permanent"] = bool(raw.get("permanent", False))
    return payload


def _normalize_buff_entry(raw) -> dict:
    if not isinstance(raw, dict):
        return {"duration": 0, "bonus": _default_bonus_payload()}

    return {
        "duration": max(0, _safe_int(raw.get("duration", 0), 0)),
        "bonus": _normalize_bonus_payload(raw.get("bonus")),
    }


def _normalize_achievement_entry(raw) -> dict:
    if not isinstance(raw, dict):
        return {"name": "", "title": "", "bonuses": []}

    bonuses = []
    raw_bonuses = raw.get("bonuses")
    if isinstance(raw_bonuses, list):
        bonuses = [_normalize_bonus_payload(entry) for entry in raw_bonuses if isinstance(entry, dict)]
    elif isinstance(raw.get("bonus"), dict):
        # Backward compatibility with earlier single-bonus achievement schema.
        bonuses = [_normalize_bonus_payload(raw.get("bonus"))]

    return {
        "name": str(raw.get("name", "") or ""),
        "title": str(raw.get("title", "") or ""),
        "description": str(raw.get("description", "") or ""),
        "bonuses": bonuses,
    }


def _bonus_summary_text(bonus: dict) -> str:
    normalized = _normalize_bonus_payload(bonus)
    attr = normalized.get("attributeBonus")
    if isinstance(attr, dict):
        attr_text = f"{attr.get('attribute', 'NONE')} {attr.get('bonus', 0)}"
    else:
        attr_text = "No Attribute"
    reason = str(normalized.get("reason", "") or "").strip() or "No Reason"
    permanence = "Permanent" if normalized.get("permanent") else "Temporary"
    return f"{normalized.get('bonusType', BonusType.FLAT.name)} | {attr_text} | {permanence} | {reason}"

def _summarize_bonus_list(bonuses: list[dict]) -> str:
    if not bonuses:
        return "No bonuses"
    if len(bonuses) == 1:
        return _bonus_summary_text(bonuses[0])
    return f"{len(bonuses)} bonuses (first: {_bonus_summary_text(bonuses[0])})"


def _list_bonus_lines(bonuses: list[dict]) -> str:
    if not bonuses:
        return "No bonuses"
    lines = []
    for index, bonus in enumerate(bonuses, start=1):
        lines.append(f"{index}. {_bonus_summary_text(bonus)}")
    return "\n".join(lines)

def _bonus_object_to_payload(bonus_obj) -> dict:
    if bonus_obj is None:
        return _default_bonus_payload()

    attribute_bonus = None
    raw_attribute_bonus = getattr(bonus_obj, "attributeBonus", None)
    if raw_attribute_bonus is not None and getattr(raw_attribute_bonus, "attribute", None) is not None:
        attribute_bonus = {
            "attribute": raw_attribute_bonus.attribute.name,
            "bonus": _safe_int(getattr(raw_attribute_bonus, "bonus", 0), 0),
        }

    affinities = None
    raw_affinities = getattr(bonus_obj, "affinities", None)
    if raw_affinities is not None:
        affinities = {
            "chi": _safe_float(getattr(raw_affinities, "chi", 0.0), 0.0),
            "mana": _safe_float(getattr(raw_affinities, "mana", 0.0), 0.0),
            "psi": _safe_float(getattr(raw_affinities, "psi", 0.0), 0.0),
            "aether": _safe_float(getattr(raw_affinities, "aether", 0.0), 0.0),
        }

    bonus_type = getattr(getattr(bonus_obj, "bonusType", None), "name", BonusType.FLAT.name)
    if bonus_type not in BonusType.__members__:
        bonus_type = BonusType.FLAT.name

    return {
        "bonusType": bonus_type,
        "attributeBonus": attribute_bonus,
        "affinities": affinities,
        "nanoMultiplier": _safe_float(getattr(bonus_obj, "nanoMultiplier", 0.0), 0.0),
        "reason": str(getattr(bonus_obj, "reason", "") or ""),
        "permanent": bool(getattr(bonus_obj, "permanent", False)),
    }


def _achievement_object_to_entry(achievement_obj) -> dict:
    bonuses = [_bonus_object_to_payload(entry) for entry in getattr(achievement_obj, "bonuses", []) if entry is not None]
    return {
        "name": str(getattr(achievement_obj, "name", "") or ""),
        "title": str(getattr(achievement_obj, "title", "") or ""),
        "description": str(getattr(achievement_obj, "description", "") or ""),
        "bonuses": bonuses,
    }



class AdminEditorApp:
    def __init__(self, spell_service, item_service, character_service, achievement_service, player_service, race_service):
        self.spell_service = spell_service
        self.item_service = item_service
        self.character_service = character_service
        self.achievement_service = achievement_service
        self.player_service = player_service
        self.race_service = race_service

        self.root = tk.Tk()
        self.root.title("TheArchitect Admin Editor")
        self.root.geometry("950x800")

        self.container = ttk.Frame(self.root, padding=12)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.home_frame = ttk.Frame(self.container)
        self.spell_frame = SpellEditorFrame(self.container, self)
        self.item_frame = ItemEditorFrame(self.container, self)
        self.character_frame = CharacterEditorFrame(self.container, self)
        self.player_frame = PlayerEditorFrame(self.container, self)
        self.achievement_frame = AchievementBookFrame(self.container, self)
        self.race_frame = RaceEditorFrame(self.container, self)

        self._build_home()
        self.show_home()

    def _build_home(self):
        ttk.Label(self.home_frame, text="Admin Editor Menu", font=("Segoe UI", 16, "bold")).pack(pady=20)
        ttk.Button(self.home_frame, text="Edit Spells", command=self.show_spell_editor).pack(fill=tk.X, pady=6)
        ttk.Button(self.home_frame, text="Edit Items", command=self.show_item_editor).pack(fill=tk.X, pady=6)
        ttk.Button(self.home_frame, text="Edit Characters", command=self.show_character_editor).pack(fill=tk.X, pady=6)
        ttk.Button(self.home_frame, text="Edit Players", command=self.show_player_editor).pack(fill=tk.X, pady=6)
        ttk.Button(self.home_frame, text="Edit Achievements", command=self.show_achievement_editor).pack(fill=tk.X, pady=6)
        ttk.Button(self.home_frame, text="Edit Races", command=self.show_race_editor).pack(fill=tk.X, pady=6)

    def _show(self, frame):
        for child in (
            self.home_frame,
            self.spell_frame,
            self.item_frame,
            self.character_frame,
            self.player_frame,
            self.achievement_frame,
            self.race_frame,
        ):
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

    def show_player_editor(self):
        self.player_frame.refresh_player_list(reset_form=True)
        self._show(self.player_frame)

    def show_achievement_editor(self):
        self.achievement_frame.refresh_achievement_list(reset_form=True)
        self._show(self.achievement_frame)

    def show_race_editor(self):
        self.race_frame.refresh_race_list(reset_form=True)
        self._show(self.race_frame)

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


class AchievementEditorDialog(tk.Toplevel):
    def __init__(self, parent, initial_list: list, on_save):
        super().__init__(parent)
        self.title("Edit Achievement List")
        self.geometry("980x640")
        self.on_save = on_save
        self.entries = [_normalize_achievement_entry(entry) for entry in (initial_list or []) if isinstance(entry, dict)]
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


class AchievementPickerDialog(tk.Toplevel):
    def __init__(self, parent, achievement_service, on_select):
        super().__init__(parent)
        self.title("Add Achievement")
        self.geometry("760x500")
        self.achievement_service = achievement_service
        self.on_select = on_select
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Add Selected", command=self._add_selected).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for achievement in self.achievement_service.list_achievements():
            name = str(getattr(achievement, "name", "") or "")
            title = str(getattr(achievement, "title", "") or "")
            description = str(getattr(achievement, "description", "") or "")
            haystack = f"{name} {title} {description}".lower()
            if query and query not in haystack:
                continue
            self.filtered.append(achievement)
            display = f"{name} ({title})" if title else name
            if description:
                display += f" - {description[:80]}"
            self.listbox.insert(tk.END, display)

    def _add_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Add Achievement", "Select an achievement to add.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        payload = _achievement_object_to_entry(self.filtered[index])
        self.on_select(payload)
        self.destroy()


class RacePickerDialog(tk.Toplevel):
    def __init__(self, parent, race_service, on_select):
        super().__init__(parent)
        self.title("Select Race")
        self.geometry("760x500")
        self.race_service = race_service
        self.on_select = on_select
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Select", command=self._select).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for race in self.race_service.list_races():
            label = self.race_service.get_race_label(race)
            if query and query not in label.lower():
                continue
            self.filtered.append(race)
            self.listbox.insert(tk.END, label)

    def _select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Select Race", "Select a race.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        race = self.filtered[index]
        self.on_select(race.raceId)
        self.destroy()


class MainCharacterInfoDialog(tk.Toplevel):
    def __init__(self, parent, draft: dict, on_save):
        super().__init__(parent)
        self.title("Main Character Info")
        self.geometry("760x820")
        self.on_save = on_save
        self.vars = {}

        body = ttk.Frame(self, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        for field_key, label in CharacterInfo.FIELD_SPECS:
            row = ttk.Frame(body)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
            var = tk.StringVar(value=str(draft.get(field_key, "") or ""))
            self.vars[field_key] = var
            ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        actions = ttk.Frame(body)
        actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self.transient(parent)
        self.grab_set()

    def _save(self):
        payload = {}
        for field_key, _label in CharacterInfo.FIELD_SPECS:
            value = self.vars[field_key].get().strip()
            if field_key == "age":
                payload[field_key] = _safe_int(value, 0)
            else:
                payload[field_key] = value
        self.on_save(payload)
        self.destroy()


class CharacterEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_character_id = None
        self.is_main_character = False
        self.main_character_info_draft = self._default_main_character_info()

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
            "party": tk.StringVar(value="0"),
            "health": tk.StringVar(value="100"),
            "healthState": tk.StringVar(value=HealthState.HEALTHY.name),
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

        self._row_entry("Party", self.vars["party"])
        self._row_entry("Health", self.vars["health"])
        self._row_combo("Health State", self.vars["healthState"], [e.name for e in HealthState])

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, pady=8)
        ttk.Button(actions, text="Edit Attributes", command=self._edit_attributes).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Edit Gear", command=self._edit_gear).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Edit Bonus (Buff List)", command=self._edit_buffs).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Add Achievement", command=self._add_achievement).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Remove Achievement", command=self._remove_selected_achievement).pack(side=tk.LEFT, padx=4)
        self.main_character_button = ttk.Button(actions, text="Convert to Main Character", command=self._edit_main_character)
        self.main_character_button.pack(side=tk.LEFT, padx=4)

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

    def _normalize_main_character_info(self, payload) -> dict:
        return CharacterInfo.from_dict(payload).to_dict()

    def _refresh_main_character_button(self):
        button_text = "Edit Main Character Info" if self.is_main_character else "Convert to Main Character"
        self.main_character_button.config(text=button_text)

    def _clear_form(self):
        self.current_character_id = None
        self.is_main_character = False
        self.main_character_info_draft = self._default_main_character_info()
        self.vars["name"].set("")
        self.vars["description"].set("")
        self.vars["portraitURL"].set("")
        self.vars["footerImageURL"].set("")
        self.vars["level"].set("0")
        self.vars["raceTier"].set("Tier I")
        self.vars["race"].set("Human1")
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
        self.is_main_character = isinstance(character, MainCharacter) or bool(state.get("characterInfo"))
        self.main_character_info_draft = (
            self._normalize_main_character_info(state.get("characterInfo"))
            if self.is_main_character
            else self._default_main_character_info()
        )
        self.vars["name"].set(state.get("name", ""))
        self.vars["description"].set(str(state.get("description", "") or ""))
        self.vars["portraitURL"].set(str(state.get("portraitURL", "") or ""))
        self.vars["footerImageURL"].set(str(state.get("footerImageURL", "") or ""))
        self.vars["level"].set(str(state.get("level", 0)))
        self.vars["raceTier"].set(str(state.get("raceTier", "Tier I")))
        self.vars["race"].set(str(state.get("race", "Human1") or "Human1"))
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
        self._refresh_main_character_button()
        self._refresh_summary()

    def _refresh_summary(self):
        lines = [
            f"Character Type: {'MainCharacter' if self.is_main_character else 'Character'}",
            f"Description: {self.vars['description'].get().strip()}",
            f"Portrait URL: {self.vars['portraitURL'].get().strip()}",
            f"Footer Image URL: {self.vars['footerImageURL'].get().strip()}",
            f"Race ID: {self.vars['race'].get().strip() or 'Human1'}",
        ]

        if self.is_main_character:
            info = self.main_character_info_draft
            lines.extend(
                [
                    f"Main Character Age: {info.get('age', 0)}",
                    f"Occupation: {info.get('occupation', '')}",
                    f"Job: {info.get('job', '')}",
                    f"Personality Type: {info.get('personalityType', '')}",
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
                self.is_main_character = True
            except Exception as exc:
                messagebox.showerror("Character Editor", f"Failed to convert to Main Character: {exc}")
                return

        self._refresh_main_character_button()
        self._refresh_summary()
        MainCharacterInfoDialog(self, self.main_character_info_draft, self._on_main_character_info_saved)

    def _on_main_character_info_saved(self, payload):
        self.main_character_info_draft = self._normalize_main_character_info(payload)
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
            "party": _safe_int(self.vars["party"].get(), 0),
            "health": _safe_int(self.vars["health"].get(), 100),
            "healthState": self.vars["healthState"].get().strip() or HealthState.HEALTHY.name,
            "description": self.vars["description"].get().strip(),
            "portraitURL": self.vars["portraitURL"].get().strip(),
            "footerImageURL": self.vars["footerImageURL"].get().strip(),
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
        if include_main_character and self.is_main_character:
            payload["characterType"] = "MainCharacter"
            payload["characterInfo"] = dict(self.main_character_info_draft)
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


class CharacterPickerDialog(tk.Toplevel):
    def __init__(self, parent, character_service, on_select):
        super().__init__(parent)
        self.title("Add Character")
        self.geometry("760x500")
        self.character_service = character_service
        self.on_select = on_select
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Add Selected", command=self._add_selected).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for character_id, character in self.character_service.list_characters():
            name = str(getattr(character, "name", "") or "")
            level = int(_safe_int(getattr(character, "level", 0), 0))
            display = f"{name} [{character_id}] (Lv {level})"
            if query and query not in display.lower():
                continue
            self.filtered.append((character_id, character))
            self.listbox.insert(tk.END, display)

    def _add_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Add Character", "Select a character to add.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        character_id, _ = self.filtered[index]
        self.on_select(character_id)
        self.destroy()


class ItemPickerDialog(tk.Toplevel):
    def __init__(self, parent, item_service, on_select):
        super().__init__(parent)
        self.title("Add Inventory Item")
        self.geometry("760x500")
        self.item_service = item_service
        self.on_select = on_select
        self.filtered = []

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(search_row, text="Search", width=10).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="Add Selected", command=self._add_selected).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()

    def _refresh_list(self):
        query = self.search_var.get().strip().lower()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for item in self.item_service.list_items():
            label = self.item_service.get_item_label(item)
            if query and query not in label.lower():
                continue
            self.filtered.append(item)
            self.listbox.insert(tk.END, label)

    def _add_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("Add Inventory Item", "Select an item to add.")
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.filtered):
            return
        item = self.filtered[index]
        self.on_select(item.itemId)
        self.destroy()


class PlayerEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_player_id = None
        self.current_player = None
        self.characters_draft = []
        self.inventory_draft = []

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Player Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_player_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Player", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<Select Player>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.discord_id_var = tk.StringVar(value="")
        self._row_entry("Discord ID", self.discord_id_var, state="readonly")

        self.vars = {
            "playerName": tk.StringVar(),
            "nano": tk.StringVar(value="0"),
            "energy": tk.StringVar(value="100"),
            "energyCap": tk.StringVar(value="100"),
            "energyLastCalculatedTime": tk.StringVar(value="0"),
            "energyRegenRatePerSecond": tk.StringVar(value=str(1.0 / 60.0)),
            "titlePreference": tk.StringVar(value=TitlePreference.Masculine.name),
            "achievementTitle": tk.StringVar(),
            "isNewPlayer": tk.StringVar(value="False"),
            "intChoice": tk.StringVar(value="0"),
            "partyNames": tk.StringVar(value='["Delta Team", "2", "3", "4"]'),
        }

        self._row_entry("Player Name", self.vars["playerName"])
        self._row_entry("Nano", self.vars["nano"])
        self._row_entry("Energy", self.vars["energy"])
        self._row_entry("Energy Cap", self.vars["energyCap"])
        self._row_entry("Energy Last Time", self.vars["energyLastCalculatedTime"])
        self._row_entry("Energy Regen / Sec", self.vars["energyRegenRatePerSecond"])
        self._row_combo("Title Preference", self.vars["titlePreference"], [e.name for e in TitlePreference])
        self._row_entry("Achievement Title", self.vars["achievementTitle"])
        self._row_combo("Is New Player", self.vars["isNewPlayer"], ["True", "False"])
        self._row_entry("Int Choice", self.vars["intChoice"])
        self._row_entry("Party Names JSON", self.vars["partyNames"])

        character_panel = ttk.LabelFrame(self, text="Owned Characters")
        character_panel.pack(fill=tk.BOTH, expand=False, pady=6)
        self.character_listbox = tk.Listbox(character_panel, height=6)
        self.character_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        character_actions = ttk.Frame(character_panel)
        character_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(character_actions, text="Add Character", command=self._add_character).pack(side=tk.LEFT)
        ttk.Button(character_actions, text="Remove Selected", command=self._remove_selected_character).pack(side=tk.LEFT, padx=6)

        inventory_panel = ttk.LabelFrame(self, text="Inventory Items")
        inventory_panel.pack(fill=tk.BOTH, expand=False, pady=6)
        self.inventory_listbox = tk.Listbox(inventory_panel, height=8)
        self.inventory_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        inventory_actions = ttk.Frame(inventory_panel)
        inventory_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(inventory_actions, text="Add Item", command=self._add_inventory_item).pack(side=tk.LEFT)
        ttk.Button(inventory_actions, text="Remove Selected", command=self._remove_selected_inventory_item).pack(side=tk.LEFT, padx=6)

        self.summary_var = tk.StringVar(value="No player selected.")
        ttk.Label(self, textvariable=self.summary_var, justify=tk.LEFT, anchor="w").pack(fill=tk.X, pady=(2, 8))

        ttk.Button(self, text="Save Player", command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _row_entry(self, label, var, state="normal"):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var, state=state).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _row_combo(self, label, var, values):
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Combobox(row, state="readonly", values=values, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _clear_form(self):
        self.current_player_id = None
        self.current_player = None
        self.discord_id_var.set("")
        self.vars["playerName"].set("")
        self.vars["nano"].set("0")
        self.vars["energy"].set("100")
        self.vars["energyCap"].set("100")
        self.vars["energyLastCalculatedTime"].set("0")
        self.vars["energyRegenRatePerSecond"].set(str(1.0 / 60.0))
        self.vars["titlePreference"].set(TitlePreference.Masculine.name)
        self.vars["achievementTitle"].set("")
        self.vars["isNewPlayer"].set("False")
        self.vars["intChoice"].set("0")
        self.vars["partyNames"].set('["Delta Team", "2", "3", "4"]')
        self.characters_draft = []
        self.inventory_draft = []
        self._refresh_lists()

    def _filtered_players(self):
        query = self.search_var.get().strip().lower()
        result = []
        for player_id in self.app.player_service.list_known_player_ids():
            player = self.app.player_service.get_player_sync(player_id)
            if player is None:
                continue
            name = str(getattr(player, "playerName", "") or "").strip() or f"Player {player_id}"
            label = f"{name} [{player_id}]"
            if query and query not in label.lower():
                continue
            result.append((player_id, label))
        return result

    def refresh_player_list(self, reset_form: bool):
        labels = ["<Select Player>"] + [label for _, label in self._filtered_players()]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<Select Player>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<Select Player>")

    def _normalize_character_entry(self, entry):
        if entry is None:
            return None
        if hasattr(entry, "name") and hasattr(entry, "level"):
            return entry
        if isinstance(entry, str):
            resolved = self.app.character_service.get_character(entry)
            if resolved is not None:
                return resolved
        return None

    def _normalize_inventory_entry(self, entry):
        if entry is None:
            return None
        if hasattr(entry, "itemId") and hasattr(entry, "name"):
            return entry
        resolved = self.app.item_service.get_item(str(entry))
        if resolved is not None:
            return resolved
        if isinstance(entry, (str, int, float)):
            return str(entry)
        return None

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<Select Player>":
            self._clear_form()
            return

        try:
            player_id = int(_parse_label_id(selected))
        except Exception:
            return

        player = self.app.player_service.get_player_sync(player_id)
        if player is None:
            messagebox.showerror("Player Editor", f"Could not load player {player_id}.")
            return

        self.current_player_id = player_id
        self.current_player = player
        self.discord_id_var.set(str(player_id))
        self.vars["playerName"].set(str(getattr(player, "playerName", "") or ""))
        self.vars["nano"].set(str(_safe_int(getattr(player, "nano", 0), 0)))
        self.vars["energy"].set(str(_safe_float(getattr(player, "energy", 0.0), 0.0)))
        self.vars["energyCap"].set(str(_safe_float(getattr(player, "energyCap", 100.0), 100.0)))
        self.vars["energyLastCalculatedTime"].set(str(_safe_float(getattr(player, "energyLastCalculatedTime", 0.0), 0.0)))
        self.vars["energyRegenRatePerSecond"].set(str(_safe_float(getattr(player, "energyRegenRatePerSecond", 1.0 / 60.0), 1.0 / 60.0)))

        title_pref = getattr(player, "titlePreference", TitlePreference.Masculine)
        title_pref_name = getattr(title_pref, "name", TitlePreference.Masculine.name)
        if title_pref_name not in TitlePreference.__members__:
            title_pref_name = TitlePreference.Masculine.name
        self.vars["titlePreference"].set(title_pref_name)

        self.vars["achievementTitle"].set(str(getattr(player, "achievementTitle", "") or ""))
        self.vars["isNewPlayer"].set("True" if bool(getattr(player, "isNewPlayer", False)) else "False")
        self.vars["intChoice"].set(str(_safe_int(getattr(player, "intChoice", 0), 0)))

        party_names = getattr(player, "partyNames", ["Delta Team", "2", "3", "4"])
        if not isinstance(party_names, list):
            party_names = ["Delta Team", "2", "3", "4"]
        self.vars["partyNames"].set(json.dumps([str(name) for name in party_names], ensure_ascii=False))

        self.characters_draft = []
        for entry in getattr(player, "characters", []) or []:
            normalized = self._normalize_character_entry(entry)
            if normalized is not None:
                self.characters_draft.append(normalized)

        self.inventory_draft = []
        for entry in getattr(player, "inventory", []) or []:
            normalized = self._normalize_inventory_entry(entry)
            if normalized is not None:
                self.inventory_draft.append(normalized)

        self._refresh_lists()

    def _resolve_character_id(self, character_obj):
        for character_id, character in self.app.character_service.list_characters():
            if character is character_obj:
                return character_id

        target_name = str(getattr(character_obj, "name", "") or "").strip().lower()
        if not target_name:
            return None

        matches = []
        for character_id, character in self.app.character_service.list_characters():
            candidate_name = str(getattr(character, "name", "") or "").strip().lower()
            if candidate_name == target_name:
                matches.append(character_id)
        if len(matches) == 1:
            return matches[0]
        return None

    def _character_label(self, character_obj) -> str:
        character_id = self._resolve_character_id(character_obj)
        name = str(getattr(character_obj, "name", "") or "").strip() or "<Unnamed>"
        if character_id:
            return f"{name} [{character_id}]"
        return f"{name} [Unlinked]"

    def _item_label(self, item_entry) -> str:
        if hasattr(item_entry, "itemId") and hasattr(item_entry, "name"):
            return self.app.item_service.get_item_label(item_entry)

        resolved = self.app.item_service.get_item(str(item_entry))
        if resolved is not None:
            return self.app.item_service.get_item_label(resolved)

        text = str(item_entry or "").strip() or "Unknown"
        return f"{text} [Unlinked]"

    def _refresh_lists(self):
        self.character_listbox.delete(0, tk.END)
        for character in self.characters_draft:
            self.character_listbox.insert(tk.END, self._character_label(character))

        self.inventory_listbox.delete(0, tk.END)
        for item in self.inventory_draft:
            self.inventory_listbox.insert(tk.END, self._item_label(item))

        self.summary_var.set(
            f"Characters: {len(self.characters_draft)} | Inventory Items: {len(self.inventory_draft)}"
        )

    def _add_character(self):
        def _on_select(character_id: str):
            character = self.app.character_service.get_character(character_id)
            if character is None:
                return
            for existing in self.characters_draft:
                if self._resolve_character_id(existing) == character_id:
                    messagebox.showinfo("Player Editor", f"Character '{character.name}' is already assigned.")
                    return
            self.characters_draft.append(character)
            self._refresh_lists()

        CharacterPickerDialog(self, self.app.character_service, _on_select)

    def _remove_selected_character(self):
        selection = self.character_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.characters_draft):
            return
        self.characters_draft.pop(index)
        self._refresh_lists()

    def _add_inventory_item(self):
        def _on_select(item_id: str):
            item = self.app.item_service.get_item(item_id)
            if item is None:
                return
            self.inventory_draft.append(item)
            self._refresh_lists()

        ItemPickerDialog(self, self.app.item_service, _on_select)

    def _remove_selected_inventory_item(self):
        selection = self.inventory_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self.inventory_draft):
            return
        self.inventory_draft.pop(index)
        self._refresh_lists()

    def _save(self):
        if self.current_player is None or self.current_player_id is None:
            messagebox.showerror("Player Editor", "Select a player before saving.")
            return

        try:
            party_names = json.loads(self.vars["partyNames"].get() or "[]")
            if not isinstance(party_names, list):
                raise ValueError("Party names must be a JSON list.")
            party_names = [str(entry) for entry in party_names]
        except Exception as exc:
            messagebox.showerror("Player Editor", f"Invalid Party Names JSON: {exc}")
            return

        player = self.current_player
        previous_autosave = bool(getattr(player, "_auto_save_enabled", False))
        try:
            player.SetAutoSaveEnabled(False)
            player.playerName = str(self.vars["playerName"].get() or "").strip()
            player.nano = _safe_int(self.vars["nano"].get(), 0)
            player.energy = _safe_float(self.vars["energy"].get(), 0.0)
            player.energyCap = max(0.0, _safe_float(self.vars["energyCap"].get(), 100.0))
            player.energyLastCalculatedTime = _safe_float(self.vars["energyLastCalculatedTime"].get(), 0.0)
            player.energyRegenRatePerSecond = _safe_float(self.vars["energyRegenRatePerSecond"].get(), 1.0 / 60.0)

            title_preference_name = str(self.vars["titlePreference"].get() or TitlePreference.Masculine.name).strip()
            if title_preference_name not in TitlePreference.__members__:
                title_preference_name = TitlePreference.Masculine.name
            player.titlePreference = TitlePreference[title_preference_name]

            player.achievementTitle = str(self.vars["achievementTitle"].get() or "").strip()
            player.isNewPlayer = self.vars["isNewPlayer"].get() == "True"
            player.intChoice = _safe_int(self.vars["intChoice"].get(), 0)
            player.partyNames = party_names
            player.characters = list(self.characters_draft)
            player.inventory = list(self.inventory_draft)
        except Exception as exc:
            messagebox.showerror("Player Editor", f"Failed to update player fields: {exc}")
            player.SetAutoSaveEnabled(previous_autosave)
            return

        player.SetAutoSaveEnabled(previous_autosave)
        try:
            self.app.player_service.persist_player(player)
            messagebox.showinfo("Player Editor", "Player saved.")
            self.refresh_player_list(reset_form=False)
            self.pick_var.set(f"{player.playerName} [{self.current_player_id}]")
        except Exception as exc:
            messagebox.showerror("Player Editor", f"Failed to save player: {exc}")

def start_admin_gui_thread(spell_service, item_service, character_service, achievement_service, player_service, race_service):
    def _run_gui():
        try:
            app = AdminEditorApp(spell_service, item_service, character_service, achievement_service, player_service, race_service)
            app.run()
        except Exception as exc:
            print(f"Admin GUI failed to start: {exc}")

    thread = threading.Thread(target=_run_gui, name="AdminEditorGUI", daemon=True)
    thread.start()
    return thread





