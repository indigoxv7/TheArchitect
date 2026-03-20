import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Spells import AffinityTypes, Spell
from src.tools.admin.shared.forms import _safe_float


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
        ttk.Button(filter_row, text="Apply Filter", command=lambda: self.refresh_spell_list(reset_form=False)).pack(
            side=tk.LEFT, padx=6
        )
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
            "powerLevel": tk.StringVar(value="0.0"),
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
            ("Power Level", "powerLevel"),
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
        ttk.Combobox(
            row, state="readonly", values=[a.value for a in AffinityTypes], textvariable=self.vars["affinity"]
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        for label, key in [("Verbal", "verbal"), ("Somatic", "somatic")]:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
            ttk.Combobox(row, state="readonly", values=["True", "False"], textvariable=self.vars[key]).pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )

        button_row = ttk.Frame(self)
        button_row.pack(fill=tk.X, pady=8)
        ttk.Button(button_row, text="Simulate", command=self._simulate).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4)
        )
        ttk.Button(button_row, text="Save Spell", command=self._save).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0)
        )

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
        self.vars["powerLevel"].set("0.0")
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
        self.vars["powerLevel"].set(str(d.get("powerLevel", 0.0)))
        self.vars["affinity"].set(str(d.get("affinity", AffinityTypes.MANA.value)))
        self.vars["casting_time"].set(str(d.get("casting_time", "")))
        self.vars["range"].set(str(d.get("range", "")))
        self.vars["material"].set(str(c.get("material", False)))
        self.vars["duration"].set(str(d.get("duration", "")))
        self.vars["description"].set(d.get("description", ""))
        self.vars["higher_level"].set(d.get("higher_level", "") or "")
        self.vars["verbal"].set(str(bool(c.get("verbal", False))))
        self.vars["somatic"].set(str(bool(c.get("somatic", False))))

    def _build_payload(self):
        return {
            "name": self.vars["name"].get().strip(),
            "level": int(self.vars["level"].get() or 0),
            "power": self.vars["power"].get().strip(),
            "powerLevel": _safe_float(self.vars["powerLevel"].get(), 0.0),
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

    def _simulate(self):
        try:
            payload = self._build_payload()
            spell = Spell.from_dict(payload)
            result = self.app.power_rating_service.simulate_spell_power_level(spell)
            self.vars["powerLevel"].set(str(result.recommendedPowerLevel))
            messagebox.showinfo(
                "Spell Simulation",
                f"Recommended power level: {result.recommendedPowerLevel:.2f}\n"
                f"Simulated equivalent: {result.simulatedPowerEquivalent:.2f}\n"
                f"Win rate: {result.winRate * 100:.1f}% over {result.sampleCount} duels.",
            )
        except Exception as exc:
            messagebox.showerror("Spell Simulation", f"Failed to simulate spell: {exc}")

    def _save(self):
        payload = self._build_payload()
        try:
            if self.current_name:
                self.app.spell_service.edit_spell_from_patch(self.current_name, payload)
            else:
                self.app.spell_service.create_spell_from_dict(payload)
            messagebox.showinfo("Spell Editor", "Spell saved.")
            self.refresh_spell_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Spell Editor", f"Failed to save spell: {exc}")
