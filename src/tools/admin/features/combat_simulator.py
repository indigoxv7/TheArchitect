import json
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.character_io import character_to_state
from src.tools.admin.shared.pickers import CharacterSelectDialog, SpellSelectDialog


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


class SpellListEditorDialog(tk.Toplevel):
    def __init__(self, parent, spell_service, initial_spells: list, on_save):
        super().__init__(parent)
        self.title("Edit Spell List")
        self.geometry("760x520")
        self.spell_service = spell_service
        self.on_save = on_save
        self.entries = [entry for entry in (initial_spells or []) if isinstance(entry, dict)]

        body = ttk.Frame(self, padding=10)
        body.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(body, height=18)
        self.listbox.pack(fill=tk.BOTH, expand=True)

        actions = ttk.Frame(body)
        actions.pack(fill=tk.X, pady=8)
        ttk.Button(actions, text="Add Spell", command=self._add_spell).pack(side=tk.LEFT)
        ttk.Button(actions, text="Remove Selected", command=self._remove_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Clear", command=self._clear).pack(side=tk.LEFT)

        bottom = ttk.Frame(body)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="Save and Close", command=self._save_and_close).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._refresh_list()
        self.transient(parent)
        self.grab_set()

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for entry in self.entries:
            name = str(entry.get("name", "") or "").strip() or "<Unnamed Spell>"
            level = int(_safe_int(entry.get("level", 0), 0))
            affinity = str(entry.get("affinity", "") or "")
            self.listbox.insert(tk.END, f"{name} (Lv {level}, {affinity})")

    def _add_spell(self):
        def _on_select(spell_name: str):
            spell = self.spell_service.get_spell(spell_name)
            if spell is None:
                messagebox.showerror("Spell List", f"Spell '{spell_name}' was not found.")
                return
            if any(
                str(entry.get("name", "") or "").strip().lower() == spell_name.strip().lower() for entry in self.entries
            ):
                messagebox.showinfo("Spell List", f"Spell '{spell_name}' is already listed.")
                return
            self.entries.append(spell.to_dict())
            self._refresh_list()

        SpellSelectDialog(self, self.spell_service, _on_select)

    def _remove_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.entries):
            self.entries.pop(index)
            self._refresh_list()

    def _clear(self):
        self.entries = []
        self._refresh_list()

    def _save_and_close(self):
        self.on_save(list(self.entries))
        self.destroy()


class CombatSimulatorFrame(ttk.Frame):
    SIDE_LABELS = {"left": "Left Combatant", "right": "Right Combatant"}

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.side_states = {"left": None, "right": None}
        self.side_ids = {"left": "", "right": ""}
        self.current_session = None

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Combat Simulator", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        sides = ttk.Frame(self)
        sides.pack(fill=tk.BOTH, expand=False)
        self.summary_widgets = {}
        self.selected_vars = {}
        for side_key in ("left", "right"):
            panel = ttk.LabelFrame(sides, text=self.SIDE_LABELS[side_key])
            panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
            selected_var = tk.StringVar(value="<None>")
            self.selected_vars[side_key] = selected_var

            pick_row = ttk.Frame(panel)
            pick_row.pack(fill=tk.X, padx=6, pady=(6, 4))
            ttk.Label(pick_row, text="Selected", width=12).pack(side=tk.LEFT)
            ttk.Entry(pick_row, textvariable=selected_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(pick_row, text="Choose", command=lambda key=side_key: self._choose_character(key)).pack(
                side=tk.LEFT, padx=4
            )
            ttk.Button(pick_row, text="Reload", command=lambda key=side_key: self._reload_selected_character(key)).pack(
                side=tk.LEFT
            )

            action_row = ttk.Frame(panel)
            action_row.pack(fill=tk.X, padx=6, pady=4)
            ttk.Button(action_row, text="Edit Stats", command=lambda key=side_key: self._edit_attributes(key)).pack(
                side=tk.LEFT, padx=2
            )
            ttk.Button(action_row, text="Edit Gear", command=lambda key=side_key: self._edit_gear(key)).pack(
                side=tk.LEFT, padx=2
            )
            ttk.Button(action_row, text="Edit Spells", command=lambda key=side_key: self._edit_spells(key)).pack(
                side=tk.LEFT, padx=2
            )
            ttk.Button(action_row, text="Edit Buffs", command=lambda key=side_key: self._edit_buffs(key)).pack(
                side=tk.LEFT, padx=2
            )

            summary = tk.Text(panel, height=16, wrap=tk.WORD)
            summary.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 6))
            self.summary_widgets[side_key] = summary
            self._refresh_side_summary(side_key)

        controls = ttk.LabelFrame(self, text="Simulation Controls")
        controls.pack(fill=tk.X, pady=8)

        settings = ttk.Frame(controls)
        settings.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(settings, text="Auto Repeats", width=16).pack(side=tk.LEFT)
        self.repeats_var = tk.StringVar(value="300")
        ttk.Entry(settings, textvariable=self.repeats_var, width=10).pack(side=tk.LEFT)
        self.debug_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings, text="Debug", variable=self.debug_var).pack(side=tk.LEFT, padx=12)

        buttons = ttk.Frame(controls)
        buttons.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(buttons, text="Auto Simulate", command=self._auto_simulate).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Start Turn by Turn", command=self._start_turn_by_turn).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Next Turn", command=self._next_turn).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Reset", command=self._reset_session).pack(side=tk.LEFT, padx=2)

        self.result_var = tk.StringVar(value="Select two characters to begin.")
        ttk.Label(controls, textvariable=self.result_var).pack(fill=tk.X, padx=6, pady=(0, 6))

        log_frame = ttk.LabelFrame(self, text="Simulation Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.log_text = tk.Text(log_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=6)

    def _append_log_lines(self, lines):
        for line in lines:
            self.log_text.insert(tk.END, f"{line}\n")
        self.log_text.see(tk.END)

    def _clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def _clear_session(self):
        self.current_session = None

    def _get_state(self, side_key: str):
        state = self.side_states.get(side_key)
        return json.loads(json.dumps(state)) if isinstance(state, dict) else None

    def _refresh_side_summary(self, side_key: str):
        widget = self.summary_widgets[side_key]
        widget.delete("1.0", tk.END)
        state = self.side_states.get(side_key)
        if not isinstance(state, dict):
            widget.insert(tk.END, "No character selected.")
            return
        attrs = state.get("attributes", {})
        gear = state.get("gear", {})
        spell_names = [
            str(entry.get("name", "") or "").strip() for entry in state.get("spells", []) if isinstance(entry, dict)
        ]
        inventory_ids = list(gear.get("inventory_item_ids", []) or [])
        inventory_labels = []
        for item_id in inventory_ids:
            item = self.app.item_service.get_item(item_id)
            inventory_labels.append(
                self.app.item_service.get_item_label(item) if item is not None else f"Unknown [{item_id}]"
            )
        summary_lines = [
            f"Name: {state.get('name', '')}",
            f"Race: {state.get('race', 'Human1')}",
            f"Level: {state.get('level', 0)}",
            f"Health: {state.get('health', 100)}",
            f"Friendly Fire: {state.get('friendlyFireTolerance', 'No friendly fire')}",
            "",
            "Attributes:",
            json.dumps(attrs, indent=2, ensure_ascii=False),
            "",
            "Gear:",
            json.dumps({k: v for k, v in gear.items() if k != "inventory_item_ids"}, indent=2, ensure_ascii=False),
            f"Inventory: {', '.join(inventory_labels) if inventory_labels else '<Empty>'}",
            f"Spells: {', '.join([name for name in spell_names if name]) if spell_names else '<None>'}",
            f"Buffs: {len(state.get('buffs', []) or [])}",
        ]
        widget.insert(tk.END, "\n".join(summary_lines))

    def _choose_character(self, side_key: str):
        def _on_select(character_id: str):
            character = self.app.character_service.get_character(character_id)
            if character is None:
                messagebox.showerror("Combat Simulator", f"Character '{character_id}' was not found.")
                return
            self.side_ids[side_key] = character_id
            self.selected_vars[side_key].set(f"{character.name} [{character_id}]")
            self.side_states[side_key] = character_to_state(character)
            self._clear_session()
            self._refresh_side_summary(side_key)

        CharacterSelectDialog(self, self.app.character_service, _on_select)

    def _reload_selected_character(self, side_key: str):
        character_id = str(self.side_ids.get(side_key, "") or "").strip()
        if not character_id:
            return
        character = self.app.character_service.get_character(character_id)
        if character is None:
            messagebox.showerror("Combat Simulator", f"Character '{character_id}' was not found.")
            return
        self.side_states[side_key] = character_to_state(character)
        self._clear_session()
        self._refresh_side_summary(side_key)

    def _edit_attributes(self, side_key: str):
        state = self.side_states.get(side_key)
        if not isinstance(state, dict):
            messagebox.showerror("Combat Simulator", "Select a character first.")
            return
        attrs = state.get("attributes", {})
        payload = {
            "physical_power": attrs.get("physicalPower", 5),
            "physical_stamina": attrs.get("physicalStamina", 5),
            "physical_resistance": attrs.get("physicalResistance", 5),
            "magic_power": attrs.get("magicPower", 5),
            "magic_stamina": attrs.get("magicStamina", 5),
            "magic_resistance": attrs.get("magicResistance", 5),
        }

        def _on_save(updated):
            state["attributes"] = {
                "physicalPower": updated.get("physical_power", 5),
                "physicalStamina": updated.get("physical_stamina", 5),
                "physicalResistance": updated.get("physical_resistance", 5),
                "magicPower": updated.get("magic_power", 5),
                "magicStamina": updated.get("magic_stamina", 5),
                "magicResistance": updated.get("magic_resistance", 5),
            }
            self._clear_session()
            self._refresh_side_summary(side_key)

        from src.tools.admin.shared.gear_dialogs import AttributesEditorDialog

        AttributesEditorDialog(self, payload, _on_save)

    def _edit_gear(self, side_key: str):
        state = self.side_states.get(side_key)
        if not isinstance(state, dict):
            messagebox.showerror("Combat Simulator", "Select a character first.")
            return

        def _on_save(updated):
            state["gear"] = dict(updated)
            self._clear_session()
            self._refresh_side_summary(side_key)

        from src.tools.admin.shared.gear_dialogs import GearEditorDialog

        GearEditorDialog(self, dict(state.get("gear", {})), self.app.item_service, _on_save)

    def _edit_buffs(self, side_key: str):
        state = self.side_states.get(side_key)
        if not isinstance(state, dict):
            messagebox.showerror("Combat Simulator", "Select a character first.")
            return

        def _on_save(updated):
            state["buffs"] = list(updated)
            self._clear_session()
            self._refresh_side_summary(side_key)

        from src.tools.admin.shared.bonus_dialogs import BonusEditorDialog

        BonusEditorDialog(self, list(state.get("buffs", []) or []), _on_save)

    def _edit_spells(self, side_key: str):
        state = self.side_states.get(side_key)
        if not isinstance(state, dict):
            messagebox.showerror("Combat Simulator", "Select a character first.")
            return

        def _on_save(updated):
            state["spells"] = list(updated)
            self._clear_session()
            self._refresh_side_summary(side_key)

        SpellListEditorDialog(self, self.app.spell_service, list(state.get("spells", []) or []), _on_save)

    def _ensure_ready(self) -> bool:
        if not isinstance(self.side_states.get("left"), dict) or not isinstance(self.side_states.get("right"), dict):
            messagebox.showerror("Combat Simulator", "Select both combatants first.")
            return False
        return True

    def _start_turn_by_turn(self):
        if not self._ensure_ready():
            return
        self.current_session = self.app.combat_simulator_service.start_session(
            self._get_state("left"),
            self._get_state("right"),
            debug=bool(self.debug_var.get()),
        )
        self._clear_log()
        self._append_log_lines(self.current_session.log_lines)
        self.result_var.set("Turn-by-turn simulation started.")

    def _next_turn(self):
        if not self._ensure_ready():
            return
        if self.current_session is None:
            self._start_turn_by_turn()
            return
        new_lines = self.app.combat_simulator_service.step_session(self.current_session)
        self._append_log_lines(new_lines)
        self.result_var.set(
            self.current_session.result_text or f"Round {self.current_session.round_number} in progress."
        )

    def _reset_session(self):
        if not self._ensure_ready():
            return
        self.current_session = self.app.combat_simulator_service.start_session(
            self._get_state("left"),
            self._get_state("right"),
            debug=bool(self.debug_var.get()),
        )
        self._clear_log()
        self._append_log_lines(self.current_session.log_lines)
        self.result_var.set("Simulation reset.")

    def _auto_simulate(self):
        if not self._ensure_ready():
            return
        repeats = max(1, _safe_int(self.repeats_var.get(), 300))
        try:
            result = self.app.combat_simulator_service.run_auto(
                self._get_state("left"),
                self._get_state("right"),
                repeats=repeats,
            )
        except Exception as exc:
            messagebox.showerror("Combat Simulator", f"Failed to run auto simulation: {exc}")
            return
        self.result_var.set(
            f"{result.leftName}: {result.leftWinRate * 100:.1f}% | {result.rightName}: {result.rightWinRate * 100:.1f}% | Draws: {result.draws}"
        )
        self._clear_log()
        self._append_log_lines(
            [
                f"Auto simulation complete over {result.sampleCount} fights.",
                f"{result.leftName} wins: {result.leftWins} ({result.leftWinRate * 100:.1f}%)",
                f"{result.rightName} wins: {result.rightWins} ({result.rightWinRate * 100:.1f}%)",
                f"Draws: {result.draws}",
                f"Average rounds: {result.averageRounds:.2f}",
            ]
        )
        self.current_session = None
