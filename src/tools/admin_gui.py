import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.CharacterUtil import DamageType, EquipSlot, ItemType, PowerType
from src.domain.Spells import AffinityTypes


class AdminEditorApp:
    def __init__(self, spell_service, item_service):
        self.spell_service = spell_service
        self.item_service = item_service

        self.root = tk.Tk()
        self.root.title("TheArchitect Admin Editor")
        self.root.geometry("950x800")

        self.container = ttk.Frame(self.root, padding=12)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.home_frame = ttk.Frame(self.container)
        self.spell_frame = SpellEditorFrame(self.container, self)
        self.item_frame = ItemEditorFrame(self.container, self)

        self._build_home()
        self.show_home()

    def _build_home(self):
        ttk.Label(self.home_frame, text="Admin Editor Menu", font=("Segoe UI", 16, "bold")).pack(pady=20)
        ttk.Button(self.home_frame, text="Edit Spells", command=self.show_spell_editor).pack(fill=tk.X, pady=6)
        ttk.Button(self.home_frame, text="Edit Items", command=self.show_item_editor).pack(fill=tk.X, pady=6)

    def _show(self, frame):
        for child in (self.home_frame, self.spell_frame, self.item_frame):
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
        ttk.Label(pick_row, text="Select/Search Spell", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Spell>")
        self.pick = ttk.Combobox(pick_row, state="normal", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)
        self.pick.bind("<FocusIn>", self._on_pick_focus)
        self.pick.bind("<Button-1>", self._on_pick_click)
        self.pick.bind("<KeyRelease>", self._on_pick_text_changed)
        self.pick.bind("<Return>", self._on_pick_enter)

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
        query = self.pick_var.get().strip().lower()
        if query == "<new spell>":
            query = ""
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

    def _show_dropdown(self):
        try:
            self.pick.tk.call("ttk::combobox::Post", self.pick)
        except tk.TclError:
            return
        self.after_idle(self._restore_pick_focus)
    def _restore_pick_focus(self):
        try:
            cursor_pos = self.pick.index(tk.INSERT)
        except tk.TclError:
            cursor_pos = len(self.pick_var.get())
        try:
            self.pick.focus_set()
            self.pick.icursor(cursor_pos)
        except tk.TclError:
            pass

    def _on_pick_focus(self, _evt=None):
        self.after_idle(lambda: self.pick.selection_range(0, tk.END))

    def _on_pick_click(self, _evt=None):
        self.after_idle(lambda: self.pick.selection_range(0, tk.END))
        self.after_idle(self._show_dropdown)


    def _on_pick_text_changed(self, _evt=None):
        self.refresh_spell_list(reset_form=False)
        if self.focus_get() == self.pick:
            self._show_dropdown()

    def _on_pick_enter(self, _evt=None):
        values = list(self.pick.cget("values"))
        top_existing = next((name for name in values if name != "<New Spell>"), None)
        if top_existing:
            self.pick_var.set(top_existing)
            self._on_pick()
        return "break"

    def _on_pick(self, _evt=None):
        name = self.pick.get().strip()
        if name == "<New Spell>":
            self._clear_form()
            return

        spell = self.app.spell_service.get_spell(name)
        if spell is None:
            for candidate in self.app.spell_service.list_spells():
                if candidate.name.lower() == name.lower():
                    spell = candidate
                    break
        if spell is None:
            return

        d = spell.to_dict()
        c = d.get("components", {})
        self.current_name = spell.name
        self.pick_var.set(spell.name)
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
        self.current_name = None

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Item Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

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
        ttk.Label(pick_row, text="Select/Search Item", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Item>")
        self.pick = ttk.Combobox(pick_row, state="normal", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)
        self.pick.bind("<FocusIn>", self._on_pick_focus)
        self.pick.bind("<Button-1>", self._on_pick_click)
        self.pick.bind("<KeyRelease>", self._on_pick_text_changed)
        self.pick.bind("<Return>", self._on_pick_enter)

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
        self.slot_filter_var.set("All")
        self.pick_var.set("<New Item>")
        self.refresh_item_list(reset_form=False)

    def _clear_form(self):
        self.current_name = None
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
        query = self.pick_var.get().strip().lower()
        if query == "<new item>":
            query = ""
        slot_filter = self.slot_filter_var.get().strip()

        items = self.app.item_service.list_items()
        result = []
        for item in items:
            slot_name = item.slot.name if hasattr(item.slot, "name") else str(item.slot)
            if slot_filter and slot_filter != "All" and slot_name != slot_filter:
                continue
            if query and query not in item.name.lower():
                continue
            result.append(item)
        return result

    def refresh_item_list(self, reset_form: bool):
        names = ["<New Item>"] + [item.name for item in self._filtered_items()]
        self.pick["values"] = names
        if reset_form:
            self.pick_var.set("<New Item>")
            self._clear_form()

    def _show_dropdown(self):
        try:
            self.pick.tk.call("ttk::combobox::Post", self.pick)
        except tk.TclError:
            return
        self.after_idle(self._restore_pick_focus)
    def _restore_pick_focus(self):
        try:
            cursor_pos = self.pick.index(tk.INSERT)
        except tk.TclError:
            cursor_pos = len(self.pick_var.get())
        try:
            self.pick.focus_set()
            self.pick.icursor(cursor_pos)
        except tk.TclError:
            pass

    def _on_pick_focus(self, _evt=None):
        self.after_idle(lambda: self.pick.selection_range(0, tk.END))

    def _on_pick_click(self, _evt=None):
        self.after_idle(lambda: self.pick.selection_range(0, tk.END))
        self.after_idle(self._show_dropdown)


    def _on_pick_text_changed(self, _evt=None):
        self.refresh_item_list(reset_form=False)
        if self.focus_get() == self.pick:
            self._show_dropdown()

    def _on_pick_enter(self, _evt=None):
        values = list(self.pick.cget("values"))
        top_existing = next((name for name in values if name != "<New Item>"), None)
        if top_existing:
            self.pick_var.set(top_existing)
            self._on_pick()
        return "break"

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Item>":
            self._clear_form()
            return

        item = self.app.item_service.get_item(selected)
        if item is None:
            for candidate in self.app.item_service.list_items():
                if candidate.name.lower() == selected.lower():
                    item = candidate
                    break
        if item is None:
            return

        data = item.to_dict()
        power = data.get("itemPower", [{}])[0] if data.get("itemPower") else {}
        self.current_name = item.name
        self.pick_var.set(item.name)
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
            if self.current_name:
                self.app.item_service.edit_item_from_patch(self.current_name, payload)
            else:
                self.app.item_service.create_item_from_dict(payload)
            messagebox.showinfo("Item Editor", "Item saved.")
            self.refresh_item_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Item Editor", f"Failed to save item: {exc}")


def start_admin_gui_thread(spell_service, item_service):
    def _run_gui():
        try:
            app = AdminEditorApp(spell_service, item_service)
            app.run()
        except Exception as exc:
            print(f"Admin GUI failed to start: {exc}")

    thread = threading.Thread(target=_run_gui, name="AdminEditorGUI", daemon=True)
    thread.start()
    return thread



