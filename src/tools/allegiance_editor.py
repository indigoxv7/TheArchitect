import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.Allegiance import AllegianceDefaultPolicy, AllegianceRelationship
from src.tools.catalog_selectors import AllegianceSelectDialog


class RelationshipChoiceDialog(tk.Toplevel):
    def __init__(self, parent, initial_relationship: str, on_save):
        super().__init__(parent)
        self.title("Set Relationship")
        self.resizable(False, False)
        self.on_save = on_save
        self.relationship_var = tk.StringVar(
            value=initial_relationship if initial_relationship in AllegianceRelationship.__members__ else AllegianceRelationship.NEUTRAL.name
        )

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        row = ttk.Frame(container)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Relationship", width=16).pack(side=tk.LEFT)
        ttk.Combobox(
            row,
            state="readonly",
            textvariable=self.relationship_var,
            values=[entry.name for entry in AllegianceRelationship],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

        self.transient(parent)
        self.grab_set()

    def _save(self):
        self.on_save(self.relationship_var.get())
        self.destroy()


class AllegianceEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_allegiance_id = None
        self.relationships_draft: dict[str, str] = {}

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Allegiance Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_allegiance_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Allegiance", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Allegiance>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.vars = {
            "name": tk.StringVar(),
            "defaultPolicy": tk.StringVar(value=AllegianceDefaultPolicy.HOSTILE_BY_DEFAULT.name),
        }

        self._row_entry("Name", self.vars["name"])
        self._row_combo("Default Policy", self.vars["defaultPolicy"], [entry.name for entry in AllegianceDefaultPolicy])

        relationship_frame = ttk.LabelFrame(self, text="Relationship Overrides")
        relationship_frame.pack(fill=tk.BOTH, expand=True, pady=6)

        self.relationship_listbox = tk.Listbox(relationship_frame, height=12)
        self.relationship_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        relationship_actions = ttk.Frame(relationship_frame)
        relationship_actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(relationship_actions, text="Add Override", command=self._add_relationship).pack(side=tk.LEFT)
        ttk.Button(relationship_actions, text="Edit Selected", command=self._edit_selected_relationship).pack(side=tk.LEFT, padx=6)
        ttk.Button(relationship_actions, text="Remove Selected", command=self._remove_selected_relationship).pack(side=tk.LEFT)

        self.summary = tk.Text(self, height=8, wrap=tk.WORD)
        self.summary.pack(fill=tk.BOTH, expand=False, pady=6)

        ttk.Button(self, text="Save Allegiance", command=self._save).pack(fill=tk.X, pady=8)
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

    def _clear_form(self):
        self.current_allegiance_id = None
        self.relationships_draft = {}
        self.vars["name"].set("")
        self.vars["defaultPolicy"].set(AllegianceDefaultPolicy.HOSTILE_BY_DEFAULT.name)
        self._refresh_relationship_listbox()
        self._refresh_summary()

    def _filtered_allegiances(self):
        query = self.search_var.get().strip().lower()
        results = []
        for allegiance in self.app.allegiance_service.list_allegiances():
            label = self.app.allegiance_service.get_allegiance_label(allegiance)
            if query and query not in label.lower():
                continue
            results.append(allegiance)
        return results

    def refresh_allegiance_list(self, reset_form: bool):
        labels = ["<New Allegiance>"] + [
            self.app.allegiance_service.get_allegiance_label(allegiance) for allegiance in self._filtered_allegiances()
        ]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<New Allegiance>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<New Allegiance>")

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Allegiance>":
            self._clear_form()
            return

        allegiance_id = self.app.allegiance_service.parse_allegiance_id_from_label(selected)
        allegiance = self.app.allegiance_service.get_allegiance_by_id(allegiance_id)
        if allegiance is None:
            return

        self.current_allegiance_id = allegiance.allegianceId
        self.vars["name"].set(str(allegiance.name or ""))
        self.vars["defaultPolicy"].set(allegiance.defaultPolicy.name)
        self.relationships_draft = {
            other_id: relationship.name for other_id, relationship in sorted(allegiance.relationships.items())
        }
        self._refresh_relationship_listbox()
        self._refresh_summary()

    def _relationship_label(self, other_id: str, relationship_name: str) -> str:
        other = self.app.allegiance_service.get_allegiance_by_id(other_id)
        other_label = self.app.allegiance_service.get_allegiance_label(other) if other is not None else f"Unknown [{other_id}]"
        relationship = AllegianceRelationship[relationship_name]
        return f"{other_label} -> {relationship.value}"

    def _refresh_relationship_listbox(self):
        self.relationship_listbox.delete(0, tk.END)
        for other_id, relationship_name in sorted(self.relationships_draft.items()):
            self.relationship_listbox.insert(tk.END, self._relationship_label(other_id, relationship_name))

    def _refresh_summary(self):
        policy_name = self.vars["defaultPolicy"].get().strip() or AllegianceDefaultPolicy.HOSTILE_BY_DEFAULT.name
        relationship_lines = [self._relationship_label(other_id, relationship_name) for other_id, relationship_name in sorted(self.relationships_draft.items())]
        text = [
            f"Name: {self.vars['name'].get().strip() or '<Unnamed Allegiance>'}",
            f"Default Policy: {AllegianceDefaultPolicy[policy_name].value}",
            "",
            "Relationship Overrides:",
        ]
        text.extend(relationship_lines if relationship_lines else ["<None>"])
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, "\n".join(text))

    def _add_relationship(self):
        exclude_ids = list(self.relationships_draft.keys())
        if self.current_allegiance_id:
            exclude_ids.append(self.current_allegiance_id)

        def _on_select(other_id: str):
            RelationshipChoiceDialog(self, AllegianceRelationship.NEUTRAL.name, lambda relationship_name: self._save_relationship_choice(other_id, relationship_name))

        AllegianceSelectDialog(self, self.app.allegiance_service, _on_select, exclude_ids=exclude_ids)

    def _save_relationship_choice(self, other_id: str, relationship_name: str):
        if relationship_name not in AllegianceRelationship.__members__:
            return
        self.relationships_draft[str(other_id or "").strip()] = relationship_name
        self._refresh_relationship_listbox()
        self._refresh_summary()

    def _selected_other_id(self) -> str | None:
        selection = self.relationship_listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        keys = sorted(self.relationships_draft.keys())
        if index < 0 or index >= len(keys):
            return None
        return keys[index]

    def _edit_selected_relationship(self):
        other_id = self._selected_other_id()
        if not other_id:
            messagebox.showerror("Allegiance Editor", "Select a relationship override to edit.")
            return
        current_relationship = self.relationships_draft.get(other_id, AllegianceRelationship.NEUTRAL.name)
        RelationshipChoiceDialog(self, current_relationship, lambda relationship_name: self._save_relationship_choice(other_id, relationship_name))

    def _remove_selected_relationship(self):
        other_id = self._selected_other_id()
        if not other_id:
            return
        self.relationships_draft.pop(other_id, None)
        self._refresh_relationship_listbox()
        self._refresh_summary()

    def _build_payload(self) -> dict:
        return {
            "name": str(self.vars["name"].get() or "").strip(),
            "defaultPolicy": str(self.vars["defaultPolicy"].get() or AllegianceDefaultPolicy.HOSTILE_BY_DEFAULT.name).strip(),
            "relationships": dict(self.relationships_draft),
        }

    def _save(self):
        payload = self._build_payload()
        if not payload["name"]:
            messagebox.showerror("Allegiance Editor", "Allegiance name is required.")
            return

        try:
            if self.current_allegiance_id:
                self.app.allegiance_service.edit_allegiance_from_patch(self.current_allegiance_id, payload)
            else:
                self.app.allegiance_service.create_allegiance_from_dict(payload)
            messagebox.showinfo("Allegiance Editor", "Allegiance saved.")
            self.refresh_allegiance_list(reset_form=True)
        except Exception as exc:
            messagebox.showerror("Allegiance Editor", f"Failed to save allegiance: {exc}")
