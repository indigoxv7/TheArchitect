import json
import tkinter as tk
from tkinter import ttk

from src.domain.character_io import character_to_state


class ReadonlyCharacterViewer(tk.Toplevel):
    def __init__(self, parent, character, title: str = "Character Preview"):
        super().__init__(parent)
        self.title(title)
        self.geometry("760x640")

        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(
            container,
            text=str(getattr(character, "name", "") or "Unnamed Character"),
            font=("Segoe UI", 13, "bold"),
        )
        header.pack(anchor=tk.W, pady=(0, 8))

        text_frame = ttk.Frame(container)
        text_frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.configure(command=self.text.yview)

        overview = ""
        get_overview = getattr(character, "GetCharacterOverviewText", None)
        if callable(get_overview):
            overview = str(get_overview(0) or "").strip()

        state = character_to_state(character)
        payload = "\n".join(
            [
                f"Name: {getattr(character, 'name', '')}",
                f"Race: {getattr(character, 'race', '')}",
                f"Level: {getattr(character, 'level', 0)}",
                "",
                "Overview",
                overview,
                "",
                "Serialized State",
                json.dumps(state, indent=2, ensure_ascii=False),
            ]
        )
        self.text.insert("1.0", payload)
        self.text.configure(state="disabled")

        ttk.Button(container, text="Close", command=self.destroy).pack(anchor=tk.E, pady=(8, 0))
        self.transient(parent)
