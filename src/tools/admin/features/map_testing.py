import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from src.services.mission_map import (
    MissionMapSettings,
    generate_mission_map,
    render_mission_map_image,
    save_mission_map_image,
)


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


class MapTestingFrame(ttk.Frame):
    PREVIEW_WIDTH = 900
    PREVIEW_HEIGHT = 520

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_map = None
        self.preview_photo = None

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Map Testing", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        controls = ttk.LabelFrame(self, text="Map Generation Settings")
        controls.pack(fill=tk.X, pady=6)
        self.total_nodes_var = tk.StringVar(value="60")
        self.narrowness_var = tk.StringVar(value="0.5")
        self.connectedness_var = tk.StringVar(value="0.25")
        self.dead_end_likelihood_var = tk.StringVar(value="0.7")
        self.seed_var = tk.StringVar(value="")

        for label, variable, hint in [
            ("Total Nodes", self.total_nodes_var, ""),
            ("Narrowness", self.narrowness_var, "0.0 to 1.0"),
            ("Connectedness", self.connectedness_var, "0.0 to 1.0"),
            ("Dead End Likelihood", self.dead_end_likelihood_var, "0.0 to 1.0"),
            ("Seed", self.seed_var, "Blank = random"),
        ]:
            row = ttk.Frame(controls)
            row.pack(fill=tk.X, padx=8, pady=3)
            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=variable, width=20).pack(side=tk.LEFT)
            if hint:
                ttk.Label(row, text=hint).pack(side=tk.LEFT, padx=8)

        actions = ttk.Frame(controls)
        actions.pack(fill=tk.X, padx=8, pady=(4, 8))
        ttk.Button(actions, text="Generate Map", command=self._generate_map).pack(side=tk.LEFT)
        ttk.Button(actions, text="Clear Seed", command=lambda: self.seed_var.set("")).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Save PNG...", command=self._save_png).pack(side=tk.LEFT, padx=6)

        self.summary_var = tk.StringVar(value="Generate a map to preview it here.")
        ttk.Label(self, textvariable=self.summary_var, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 6))

        preview_frame = ttk.LabelFrame(self, text="Map Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _build_settings(self) -> MissionMapSettings:
        seed_text = str(self.seed_var.get() or "").strip()
        seed = _safe_int(seed_text, 0) if seed_text else None
        return MissionMapSettings(
            total_nodes=max(1, _safe_int(self.total_nodes_var.get(), 60)),
            narrowness=_safe_float(self.narrowness_var.get(), 0.5),
            connectedness=_safe_float(self.connectedness_var.get(), 0.25),
            dead_end_likelihood=_safe_float(self.dead_end_likelihood_var.get(), 0.7),
            seed=seed,
        )

    def _render_current_map(self):
        if self.current_map is None:
            self.preview_photo = None
            self.preview_label.configure(image="")
            return

        image = render_mission_map_image(
            self.current_map,
            width=self.PREVIEW_WIDTH,
            height=self.PREVIEW_HEIGHT,
        )
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_photo)
        self.summary_var.set(
            "\n".join(
                [
                    f"Seed: {self.current_map.settings.seed}",
                    f"Nodes: {self.current_map.node_count}",
                    f"Edges: {self.current_map.edge_count}",
                    f"Grid: {self.current_map.column_count} columns x {self.current_map.row_count} rows",
                    f"Start Node: {self.current_map.start_node_id}",
                ]
            )
        )

    def _generate_map(self):
        try:
            self.current_map = generate_mission_map(self._build_settings())
        except Exception as exc:
            messagebox.showerror("Map Testing", f"Failed to generate map: {exc}")
            return

        self.seed_var.set(str(self.current_map.settings.seed))
        self._render_current_map()

    def _save_png(self):
        if self.current_map is None:
            self._generate_map()
            if self.current_map is None:
                return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Map Preview",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")],
        )
        if not path:
            return

        try:
            save_mission_map_image(
                self.current_map,
                path,
                width=self.PREVIEW_WIDTH,
                height=self.PREVIEW_HEIGHT,
            )
        except Exception as exc:
            messagebox.showerror("Map Testing", f"Failed to save map image: {exc}")
            return

        messagebox.showinfo("Map Testing", f"Saved map image to:\n{path}")
