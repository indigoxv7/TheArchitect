import json
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.MainCharacter import MainCharacter


def _pretty(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


class MainCharacterMemoryFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_player_id = None
        self.current_character_instance_id = None
        self.current_player = None
        self.current_main_characters = []
        self.current_participant_candidates = []

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Main Character Memory", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        player_search_row = ttk.Frame(self)
        player_search_row.pack(fill=tk.X, pady=2)
        ttk.Label(player_search_row, text="Player Search", width=18).pack(side=tk.LEFT)
        self.player_search_var = tk.StringVar()
        player_search_entry = ttk.Entry(player_search_row, textvariable=self.player_search_var)
        player_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        player_search_entry.bind("<KeyRelease>", lambda _e: self.refresh_player_list(reset_form=False))

        player_pick_row = ttk.Frame(self)
        player_pick_row.pack(fill=tk.X, pady=2)
        ttk.Label(player_pick_row, text="Select Player", width=18).pack(side=tk.LEFT)
        self.player_pick_var = tk.StringVar(value="<Select Player>")
        self.player_pick = ttk.Combobox(player_pick_row, state="readonly", textvariable=self.player_pick_var)
        self.player_pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.player_pick.bind("<<ComboboxSelected>>", self._on_player_pick)

        character_search_row = ttk.Frame(self)
        character_search_row.pack(fill=tk.X, pady=2)
        ttk.Label(character_search_row, text="Character Search", width=18).pack(side=tk.LEFT)
        self.character_search_var = tk.StringVar()
        character_search_entry = ttk.Entry(character_search_row, textvariable=self.character_search_var)
        character_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        character_search_entry.bind("<KeyRelease>", lambda _e: self.refresh_character_list(reset_form=False))

        character_pick_row = ttk.Frame(self)
        character_pick_row.pack(fill=tk.X, pady=2)
        ttk.Label(character_pick_row, text="Select Main Character", width=18).pack(side=tk.LEFT)
        self.character_pick_var = tk.StringVar(value="<Select Main Character>")
        self.character_pick = ttk.Combobox(character_pick_row, state="readonly", textvariable=self.character_pick_var)
        self.character_pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.character_pick.bind("<<ComboboxSelected>>", self._on_character_pick)
        ttk.Button(character_pick_row, text="Refresh", command=self._refresh_snapshot).pack(side=tk.LEFT, padx=6)

        self.summary_var = tk.StringVar(value="Select a player-owned MainCharacter.")
        ttk.Label(self, textvariable=self.summary_var, justify=tk.LEFT, anchor="w").pack(fill=tk.X, pady=(4, 8))

        scene_frame = ttk.LabelFrame(self, text="Scene Input")
        scene_frame.pack(fill=tk.X, pady=6)

        self.scene_vars = {
            "location": tk.StringVar(),
            "stakes": tk.StringVar(),
            "sensory_details": tk.StringVar(),
            "latest_utterance": tk.StringVar(),
            "prompt": tk.StringVar(),
        }
        for label, key in [
            ("Location", "location"),
            ("Stakes", "stakes"),
            ("Sensory Details", "sensory_details"),
            ("Latest Utterance", "latest_utterance"),
            ("Prompt", "prompt"),
        ]:
            row = ttk.Frame(scene_frame)
            row.pack(fill=tk.X, padx=6, pady=2)
            ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=self.scene_vars[key]).pack(side=tk.LEFT, fill=tk.X, expand=True)

        participant_row = ttk.Frame(scene_frame)
        participant_row.pack(fill=tk.BOTH, padx=6, pady=4)
        ttk.Label(participant_row, text="Participants", width=18).pack(side=tk.LEFT, anchor="n")
        self.participant_listbox = tk.Listbox(participant_row, selectmode=tk.MULTIPLE, height=6)
        self.participant_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Button(scene_frame, text="Generate Turn", command=self._generate_turn).pack(fill=tk.X, padx=6, pady=(4, 6))

        snapshot_frame = ttk.LabelFrame(self, text="Stored Narrative State")
        snapshot_frame.pack(fill=tk.BOTH, expand=True, pady=6)

        columns = ttk.Frame(snapshot_frame)
        columns.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.events_text = self._text_column(columns, "Events")
        self.memories_text = self._text_column(columns, "Memories")
        self.facts_text = self._text_column(columns, "Facts")
        self.relationships_text = self._text_column(columns, "Relationships")

        output_frame = ttk.LabelFrame(self, text="Latest Turn")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.prompt_preview = self._text_block(output_frame, "Prompt Packet")
        self.turn_output = self._text_block(output_frame, "Model Output")
        self.persisted_output = self._text_block(output_frame, "Write-Back Summary")

        self.refresh_player_list(reset_form=True)

    def _text_column(self, parent, title: str):
        frame = ttk.Frame(parent)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        ttk.Label(frame, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        widget = tk.Text(frame, height=14, wrap=tk.WORD)
        widget.pack(fill=tk.BOTH, expand=True)
        return widget

    def _text_block(self, parent, title: str):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        ttk.Label(frame, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        widget = tk.Text(frame, height=8, wrap=tk.WORD)
        widget.pack(fill=tk.BOTH, expand=True)
        return widget

    def _player_candidates(self):
        query = self.player_search_var.get().strip().lower()
        result = []
        for player_id in self.app.player_service.list_known_player_ids():
            player = self.app.player_service.get_player_sync(player_id)
            if player is None:
                continue
            label = f"{getattr(player, 'playerName', player_id)} [{player_id}]"
            if query and query not in label.lower():
                continue
            result.append((player_id, label))
        return result

    def refresh_player_list(self, reset_form: bool):
        labels = ["<Select Player>"] + [label for _, label in self._player_candidates()]
        self.player_pick["values"] = labels
        if reset_form:
            self.player_pick_var.set("<Select Player>")
            self._clear_state()
        elif self.player_pick_var.get() not in labels:
            self.player_pick_var.set("<Select Player>")

    def _clear_state(self):
        self.current_player_id = None
        self.current_character_instance_id = None
        self.current_player = None
        self.current_main_characters = []
        self.current_participant_candidates = []
        self.character_pick_var.set("<Select Main Character>")
        self.character_pick["values"] = ["<Select Main Character>"]
        self.participant_listbox.delete(0, tk.END)
        self.summary_var.set("Select a player-owned MainCharacter.")
        for widget in (self.events_text, self.memories_text, self.facts_text, self.relationships_text, self.prompt_preview, self.turn_output, self.persisted_output):
            widget.delete("1.0", tk.END)

    def _on_player_pick(self, _event=None):
        label = self.player_pick_var.get().strip()
        if label == "<Select Player>":
            self._clear_state()
            return
        try:
            player_id = int(label[label.rfind("[") + 1 : -1])
        except Exception:
            return
        player = self.app.player_service.get_player_sync(player_id)
        if player is None:
            messagebox.showerror("Main Character Memory", f"Failed to load player {player_id}.")
            return
        self.current_player_id = player_id
        self.current_player = player
        self.current_main_characters = self.app.memory_service.list_player_main_characters(player_id)
        self.current_participant_candidates = list(getattr(player, "characters", []) or [])
        self.refresh_character_list(reset_form=True)
        self._refresh_participants()

    def _character_candidates(self):
        query = self.character_search_var.get().strip().lower()
        result = []
        for character in self.current_main_characters:
            label = f"{character.name} [{character.playerInstanceId}]"
            if query and query not in label.lower():
                continue
            result.append((character.playerInstanceId, label))
        return result

    def refresh_character_list(self, reset_form: bool):
        labels = ["<Select Main Character>"] + [label for _, label in self._character_candidates()]
        self.character_pick["values"] = labels
        if reset_form:
            self.character_pick_var.set("<Select Main Character>")
            self.current_character_instance_id = None
            self._refresh_snapshot()
        elif self.character_pick_var.get() not in labels:
            self.character_pick_var.set("<Select Main Character>")

    def _refresh_participants(self):
        self.participant_listbox.delete(0, tk.END)
        for character in self.current_participant_candidates:
            label = f"{getattr(character, 'name', '<Unnamed>')} [{getattr(character, 'playerInstanceId', '')}]"
            self.participant_listbox.insert(tk.END, label)

    def _on_character_pick(self, _event=None):
        label = self.character_pick_var.get().strip()
        if label == "<Select Main Character>":
            self.current_character_instance_id = None
            self._refresh_snapshot()
            return
        self.current_character_instance_id = label[label.rfind("[") + 1 : -1]
        self._refresh_snapshot()

    def _refresh_snapshot(self):
        for widget in (self.events_text, self.memories_text, self.facts_text, self.relationships_text):
            widget.delete("1.0", tk.END)
        if self.current_player_id is None or not self.current_character_instance_id:
            self.summary_var.set("Select a player-owned MainCharacter.")
            return
        try:
            snapshot = self.app.memory_service.build_character_snapshot(self.current_player_id, self.current_character_instance_id)
        except Exception as exc:
            self.summary_var.set(f"Failed to load memory snapshot: {exc}")
            return
        character = snapshot.get("character", {})
        self.summary_var.set(
            f"Player {self.current_player_id} | {character.get('name', '')} [{character.get('playerInstanceId', '')}] | "
            f"Memories: {len(snapshot.get('memories', []))} | Facts: {len(snapshot.get('facts', []))}"
        )
        self.events_text.insert(tk.END, _pretty(snapshot.get("events", [])))
        self.memories_text.insert(tk.END, _pretty(snapshot.get("memories", [])))
        self.facts_text.insert(tk.END, _pretty(snapshot.get("facts", [])))
        self.relationships_text.insert(tk.END, _pretty(snapshot.get("relationships", [])))

    def _selected_participant_ids(self) -> list[str]:
        selected = []
        for index in self.participant_listbox.curselection():
            label = self.participant_listbox.get(index)
            if label.endswith("]") and "[" in label:
                selected.append(label[label.rfind("[") + 1 : -1].strip())
        return selected

    def _generate_turn(self):
        if self.current_player_id is None or not self.current_character_instance_id:
            messagebox.showerror("Main Character Memory", "Select a player-owned MainCharacter first.")
            return
        scene_frame = {
            "location": self.scene_vars["location"].get().strip(),
            "stakes": self.scene_vars["stakes"].get().strip(),
            "sensory_details": self.scene_vars["sensory_details"].get().strip(),
            "latest_utterance": self.scene_vars["latest_utterance"].get().strip(),
            "prompt": self.scene_vars["prompt"].get().strip(),
            "participant_ids": self._selected_participant_ids(),
        }
        try:
            result = self.app.memory_service.generate_turn(
                self.current_player_id,
                self.current_character_instance_id,
                scene_frame,
            )
        except Exception as exc:
            messagebox.showerror("Main Character Memory", f"Failed to generate turn: {exc}")
            return

        self.prompt_preview.delete("1.0", tk.END)
        self.prompt_preview.insert(tk.END, _pretty(result.get("prompt_packet", {})))
        self.turn_output.delete("1.0", tk.END)
        self.turn_output.insert(tk.END, _pretty(result.get("turn_output", {})))
        self.persisted_output.delete("1.0", tk.END)
        self.persisted_output.insert(tk.END, result.get("persisted_summary", ""))
        self._refresh_snapshot()
        messagebox.showinfo("Main Character Memory", "Turn generated and stored.")
