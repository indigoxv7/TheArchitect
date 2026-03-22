import tkinter as tk
from tkinter import messagebox, ttk

from PIL import ImageTk

from src.domain.mission import MissionMapGenerationRange, MissionTemplate
from src.services.mission_map.node_content import (
    apply_overlay_to_node_contents,
    build_scene_description_prompt_packet,
    generate_node_content_preview,
)
from src.services.mission_map import (
    MissionMapOverlay,
    generate_all_map_features,
    generate_clue_overlay,
    generate_map_from_range,
    generate_treasure_overlay,
    place_characters_on_map,
    render_mission_map_image,
)
from src.services.mission_unit_populator import MissionUnitPopulator
from src.tools.admin.shared.character_viewer import ReadonlyCharacterViewer
from .dialogs import (
    MissionAllegianceConfigDialog,
    MissionObjectiveDialog,
    _objective_description,
    _safe_float,
    _safe_int,
)


class MissionEditorFrame(ttk.Frame):
    MAP_PREVIEW_WIDTH = 860
    MAP_PREVIEW_HEIGHT = 420

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_mission_id = None
        self.allegiance_configs_draft = []
        self.objective_draft = {}
        self.unit_populator = MissionUnitPopulator(self.app.unit_service, self.app.power_rating_service)
        self.population_preview = None
        self.preview_units = []
        self.current_map = None
        self.current_map_overlay = MissionMapOverlay()
        self.current_setting_context = None
        self.current_node_contents = {}
        self.map_preview_photo = None
        self.map_summary_var = tk.StringVar(value="Generate a map preview to inspect mission layout.")
        self.sampled_setting_var = tk.StringVar(value="No sampled setting yet.")
        self.selected_node_var = tk.StringVar(value="")
        self.generation_profile_var = tk.StringVar(value="<Default>")
        self.description_pack_var = tk.StringVar(value="<Default>")
        self._generation_profile_ids_by_label = {}
        self._description_pack_ids_by_label = {}
        map_defaults = MissionMapGenerationRange()
        self.map_range_vars = {
            "totalNodes": {
                "low": tk.StringVar(value=str(map_defaults.totalNodesLow)),
                "high": tk.StringVar(value=str(map_defaults.totalNodesHigh)),
            },
            "narrowness": {
                "low": tk.StringVar(value=str(map_defaults.narrownessLow)),
                "high": tk.StringVar(value=str(map_defaults.narrownessHigh)),
            },
            "connectedness": {
                "low": tk.StringVar(value=str(map_defaults.connectednessLow)),
                "high": tk.StringVar(value=str(map_defaults.connectednessHigh)),
            },
            "deadEndLikelihood": {
                "low": tk.StringVar(value=str(map_defaults.deadEndLikelihoodLow)),
                "high": tk.StringVar(value=str(map_defaults.deadEndLikelihoodHigh)),
            },
            "nodeJitterFraction": {
                "low": tk.StringVar(value=str(map_defaults.nodeJitterFractionLow)),
                "high": tk.StringVar(value=str(map_defaults.nodeJitterFractionHigh)),
            },
        }

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Mission Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_mission_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text="Select Mission", width=18).pack(side=tk.LEFT)
        self.pick_var = tk.StringVar(value="<New Mission>")
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        self.name_var = tk.StringVar()
        self.biome_var = tk.StringVar(value="<None>")
        self.portal_mission_var = tk.BooleanVar(value=True)
        self._biome_ids_by_label = {}
        name_row = ttk.Frame(self)
        name_row.pack(fill=tk.X, pady=2)
        ttk.Label(name_row, text="Name", width=18).pack(side=tk.LEFT)
        ttk.Entry(name_row, textvariable=self.name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        biome_row = ttk.Frame(self)
        biome_row.pack(fill=tk.X, pady=2)
        ttk.Label(biome_row, text="Biome", width=18).pack(side=tk.LEFT)
        self.biome_pick = ttk.Combobox(biome_row, state="readonly", textvariable=self.biome_var)
        self.biome_pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.biome_pick.bind("<<ComboboxSelected>>", lambda _evt: self._refresh_summary())

        portal_row = ttk.Frame(self)
        portal_row.pack(fill=tk.X, pady=2)
        ttk.Label(portal_row, text="Portal Mission", width=18).pack(side=tk.LEFT)
        ttk.Checkbutton(portal_row, variable=self.portal_mission_var).pack(side=tk.LEFT)

        terrain_pool_row = ttk.Frame(self)
        terrain_pool_row.pack(fill=tk.BOTH, expand=False, pady=2)
        ttk.Label(terrain_pool_row, text="Terrain Pool IDs", width=18).pack(side=tk.LEFT, anchor="n")
        self.terrain_pool_text = tk.Text(terrain_pool_row, height=3, wrap=tk.WORD)
        self.terrain_pool_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        climate_pool_row = ttk.Frame(self)
        climate_pool_row.pack(fill=tk.BOTH, expand=False, pady=2)
        ttk.Label(climate_pool_row, text="Climate Pool IDs", width=18).pack(side=tk.LEFT, anchor="n")
        self.climate_pool_text = tk.Text(climate_pool_row, height=3, wrap=tk.WORD)
        self.climate_pool_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        generation_profile_row = ttk.Frame(self)
        generation_profile_row.pack(fill=tk.X, pady=2)
        ttk.Label(generation_profile_row, text="Generation Profile", width=18).pack(side=tk.LEFT)
        self.generation_profile_pick = ttk.Combobox(generation_profile_row, state="readonly", textvariable=self.generation_profile_var)
        self.generation_profile_pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.generation_profile_pick.bind("<<ComboboxSelected>>", lambda _evt: self._refresh_summary())

        description_pack_row = ttk.Frame(self)
        description_pack_row.pack(fill=tk.X, pady=2)
        ttk.Label(description_pack_row, text="Description Pack", width=18).pack(side=tk.LEFT)
        self.description_pack_pick = ttk.Combobox(description_pack_row, state="readonly", textvariable=self.description_pack_var)
        self.description_pack_pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.description_pack_pick.bind("<<ComboboxSelected>>", lambda _evt: self._refresh_summary())

        objective_row = ttk.Frame(self)
        objective_row.pack(fill=tk.X, pady=4)
        ttk.Label(objective_row, text="Objective", width=18).pack(side=tk.LEFT)
        self.objective_label_var = tk.StringVar(value="<No Objective>")
        ttk.Entry(objective_row, textvariable=self.objective_label_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(objective_row, text="Edit Objective", command=self._edit_objective).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(objective_row, text="Clear", command=self._clear_objective).pack(side=tk.LEFT, padx=(6, 0))

        allegiance_frame = ttk.LabelFrame(self, text="Mission Allegiances")
        allegiance_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.allegiance_listbox = tk.Listbox(allegiance_frame, height=12)
        self.allegiance_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        actions = ttk.Frame(allegiance_frame)
        actions.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(actions, text="Add Allegiance", command=self._add_allegiance_config).pack(side=tk.LEFT)
        ttk.Button(actions, text="Edit Selected", command=self._edit_selected_allegiance_config).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(actions, text="Remove Selected", command=self._remove_selected_allegiance_config).pack(side=tk.LEFT)

        preview_frame = ttk.LabelFrame(self, text="Unit Population Preview")
        preview_frame.pack(fill=tk.BOTH, expand=False, pady=6)
        preview_actions = ttk.Frame(preview_frame)
        preview_actions.pack(fill=tk.X, padx=6, pady=(6, 0))
        ttk.Button(preview_actions, text="Generate Example Units", command=self._generate_population_preview).pack(
            side=tk.LEFT
        )
        ttk.Button(preview_actions, text="View Unit", command=self._view_selected_preview_unit).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(preview_actions, text="Clear Preview", command=self._clear_population_preview).pack(side=tk.LEFT)

        self.preview_summary = tk.Text(preview_frame, height=7, wrap=tk.WORD)
        self.preview_summary.pack(fill=tk.X, padx=6, pady=6)

        preview_list_frame = ttk.Frame(preview_frame)
        preview_list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        preview_scrollbar = ttk.Scrollbar(preview_list_frame, orient=tk.VERTICAL)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_listbox = tk.Listbox(
            preview_list_frame,
            height=10,
            yscrollcommand=preview_scrollbar.set,
        )
        self.preview_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scrollbar.configure(command=self.preview_listbox.yview)
        self.preview_listbox.bind("<Double-Button-1>", lambda _evt: self._view_selected_preview_unit())

        map_frame = ttk.LabelFrame(self, text="Map Generator Settings")
        map_frame.pack(fill=tk.BOTH, expand=False, pady=6)

        map_header = ttk.Frame(map_frame)
        map_header.pack(fill=tk.X, padx=6, pady=(6, 2))
        ttk.Label(map_header, text="Field", width=20).pack(side=tk.LEFT)
        ttk.Label(map_header, text="Low", width=12).pack(side=tk.LEFT)
        ttk.Label(map_header, text="High", width=12).pack(side=tk.LEFT)
        ttk.Label(map_header, text="Notes").pack(side=tk.LEFT, padx=8)

        for label, key, hint in [
            ("Total Nodes", "totalNodes", "Integer range"),
            ("Narrowness", "narrowness", "0.0 to 1.0"),
            ("Connectedness", "connectedness", "0.0 to 1.0"),
            ("Dead End Likelihood", "deadEndLikelihood", "0.0 to 1.0"),
            ("Node Jitter Fraction", "nodeJitterFraction", "0.0 to 1.0"),
        ]:
            row = ttk.Frame(map_frame)
            row.pack(fill=tk.X, padx=6, pady=2)
            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=self.map_range_vars[key]["low"], width=12).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=self.map_range_vars[key]["high"], width=12).pack(side=tk.LEFT, padx=(6, 0))
            ttk.Label(row, text=hint).pack(side=tk.LEFT, padx=8)

        map_actions = ttk.Frame(map_frame)
        map_actions.pack(fill=tk.X, padx=6, pady=(8, 4))
        ttk.Button(map_actions, text="Preview Map", command=self._generate_map_preview).pack(side=tk.LEFT)
        ttk.Button(map_actions, text="Place Characters", command=self._place_characters_on_map).pack(side=tk.LEFT, padx=6)
        ttk.Button(map_actions, text="Generate Treasure", command=self._generate_treasure_on_map).pack(side=tk.LEFT, padx=6)
        ttk.Button(map_actions, text="Generate Clues", command=self._generate_clues_on_map).pack(side=tk.LEFT, padx=6)
        ttk.Button(map_actions, text="Generate All", command=self._generate_all_map_features).pack(side=tk.LEFT, padx=6)

        ttk.Label(map_frame, textvariable=self.map_summary_var, justify=tk.LEFT).pack(fill=tk.X, padx=6, pady=(0, 6))
        self.map_preview_label = ttk.Label(map_frame)
        self.map_preview_label.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        node_preview_frame = ttk.LabelFrame(self, text="Node Content Preview")
        node_preview_frame.pack(fill=tk.BOTH, expand=False, pady=6)
        ttk.Label(node_preview_frame, textvariable=self.sampled_setting_var, justify=tk.LEFT).pack(fill=tk.X, padx=6, pady=(6, 4))

        node_actions = ttk.Frame(node_preview_frame)
        node_actions.pack(fill=tk.X, padx=6, pady=(0, 4))
        ttk.Button(node_actions, text="Generate Node Content", command=self._generate_node_content_preview).pack(side=tk.LEFT)
        ttk.Button(node_actions, text="Regenerate Selected Node", command=self._regenerate_selected_node_content).pack(side=tk.LEFT, padx=6)
        ttk.Button(node_actions, text="Generate OpenAI For Selected", command=self._generate_openai_for_selected_node).pack(side=tk.LEFT, padx=6)

        node_pick_row = ttk.Frame(node_preview_frame)
        node_pick_row.pack(fill=tk.X, padx=6, pady=(0, 4))
        ttk.Label(node_pick_row, text="Selected Node", width=18).pack(side=tk.LEFT)
        self.selected_node_pick = ttk.Combobox(node_pick_row, state="readonly", textvariable=self.selected_node_var)
        self.selected_node_pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.selected_node_pick.bind("<<ComboboxSelected>>", lambda _evt: self._render_selected_node_preview())

        self.node_summary_text = tk.Text(node_preview_frame, height=8, wrap=tk.WORD)
        self.node_summary_text.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.node_local_text = tk.Text(node_preview_frame, height=6, wrap=tk.WORD)
        self.node_local_text.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.node_openai_text = tk.Text(node_preview_frame, height=6, wrap=tk.WORD)
        self.node_openai_text.pack(fill=tk.X, padx=6, pady=(0, 6))

        self.summary = tk.Text(self, height=14, wrap=tk.WORD)
        self.summary.pack(fill=tk.BOTH, expand=False, pady=6)
        ttk.Button(self, text="Save Mission", command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _clear_form(self):
        self.current_mission_id = None
        self.name_var.set("")
        self.biome_var.set("<None>")
        self.objective_draft = {}
        self.portal_mission_var.set(True)
        self.objective_label_var.set("<No Objective>")
        self.allegiance_configs_draft = []
        self._set_text_widget(self.terrain_pool_text, "")
        self._set_text_widget(self.climate_pool_text, "")
        self._set_generation_profile_selection("")
        self._set_description_pack_selection("")
        self._load_map_generation_range(MissionMapGenerationRange())
        self._clear_population_preview()
        self._reset_map_preview_state(clear_map=True)
        self._clear_node_content_preview()
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _refresh_biome_options(self):
        labels = ["<None>"]
        self._biome_ids_by_label = {}
        for biome in self.app.environment_service.list_biomes():
            label = self.app.environment_service.get_biome_label(biome)
            labels.append(label)
            self._biome_ids_by_label[label] = biome.biomeId

        selected_biome_id = self._selected_biome_id()
        self.biome_pick["values"] = labels
        self._set_biome_selection(selected_biome_id)

    def _selected_biome_id(self):
        selected = self.biome_var.get().strip()
        if not selected or selected == "<None>":
            return ""
        if selected in self._biome_ids_by_label:
            return self._biome_ids_by_label[selected]
        if selected.endswith("]") and "[" in selected:
            return selected[selected.rfind("[") + 1 : -1].strip()
        return selected

    def _set_biome_selection(self, biome_id):
        biome_id = str(biome_id or "").strip()
        if not biome_id:
            self.biome_var.set("<None>")
            return

        biome = self.app.environment_service.get_biome_by_id(biome_id)
        if biome is None:
            self.biome_var.set("<None>")
            return

        label = self.app.environment_service.get_biome_label(biome)
        self._biome_ids_by_label[label] = biome.biomeId
        self.biome_var.set(label)

    @staticmethod
    def _set_text_widget(widget, value: str):
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, str(value or ""))

    @staticmethod
    def _parse_id_lines(text: str) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()
        for raw_line in str(text or "").replace(",", "\n").splitlines():
            line = str(raw_line or "").strip()
            if not line:
                continue
            if line.endswith("]") and "[" in line:
                line = line[line.rfind("[") + 1 : -1].strip()
            if not line or line.lower() in seen:
                continue
            seen.add(line.lower())
            values.append(line)
        return values

    def _refresh_generation_profile_options(self):
        labels = ["<Default>"]
        self._generation_profile_ids_by_label = {}
        for profile in self.app.environment_service.list_generation_profiles():
            label = self.app.environment_service.get_generation_profile_label(profile)
            labels.append(label)
            self._generation_profile_ids_by_label[label] = profile.generationProfileId
        self.generation_profile_pick["values"] = labels
        if self.generation_profile_var.get() not in labels:
            self.generation_profile_var.set("<Default>")

    def _selected_generation_profile_id(self):
        selected = self.generation_profile_var.get().strip()
        if not selected or selected == "<Default>":
            return ""
        return self._generation_profile_ids_by_label.get(selected, self._parse_id_lines(selected)[0] if self._parse_id_lines(selected) else selected)

    def _set_generation_profile_selection(self, generation_profile_id: str):
        generation_profile_id = str(generation_profile_id or "").strip()
        if not generation_profile_id:
            self.generation_profile_var.set("<Default>")
            return
        profile = self.app.environment_service.get_generation_profile_by_id(generation_profile_id)
        if profile is None:
            self.generation_profile_var.set("<Default>")
            return
        label = self.app.environment_service.get_generation_profile_label(profile)
        self._generation_profile_ids_by_label[label] = profile.generationProfileId
        self.generation_profile_var.set(label)

    def _refresh_description_pack_options(self):
        labels = ["<Default>"]
        self._description_pack_ids_by_label = {}
        for pack in self.app.environment_service.list_description_packs():
            label = self.app.environment_service.get_description_pack_label(pack)
            labels.append(label)
            self._description_pack_ids_by_label[label] = pack.descriptionPackId
        self.description_pack_pick["values"] = labels
        if self.description_pack_var.get() not in labels:
            self.description_pack_var.set("<Default>")

    def _selected_description_pack_id(self):
        selected = self.description_pack_var.get().strip()
        if not selected or selected == "<Default>":
            return ""
        return self._description_pack_ids_by_label.get(selected, self._parse_id_lines(selected)[0] if self._parse_id_lines(selected) else selected)

    def _set_description_pack_selection(self, description_pack_id: str):
        description_pack_id = str(description_pack_id or "").strip()
        if not description_pack_id:
            self.description_pack_var.set("<Default>")
            return
        pack = self.app.environment_service.get_description_pack_by_id(description_pack_id)
        if pack is None:
            self.description_pack_var.set("<Default>")
            return
        label = self.app.environment_service.get_description_pack_label(pack)
        self._description_pack_ids_by_label[label] = pack.descriptionPackId
        self.description_pack_var.set(label)

    def _clear_node_content_preview(self):
        self.current_setting_context = None
        self.current_node_contents = {}
        self.sampled_setting_var.set("No sampled setting yet.")
        self.selected_node_var.set("")
        self.selected_node_pick["values"] = []
        for widget in (self.node_summary_text, self.node_local_text, self.node_openai_text):
            self._set_text_widget(widget, "")

    def _refresh_node_selector(self):
        values = [str(node_id) for node_id in sorted(self.current_node_contents.keys())]
        self.selected_node_pick["values"] = values
        if values and self.selected_node_var.get() not in values:
            self.selected_node_var.set(values[0])
        elif not values:
            self.selected_node_var.set("")

    def _selected_node_id(self):
        text = str(self.selected_node_var.get() or "").strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def _render_selected_node_preview(self):
        node_id = self._selected_node_id()
        node_content = self.current_node_contents.get(node_id)
        if self.current_setting_context is None or node_content is None:
            for widget in (self.node_summary_text, self.node_local_text, self.node_openai_text):
                self._set_text_widget(widget, "")
            return
        summary_lines = [
            f"Node {node_id}",
            f"Scene: {node_content.sceneDisplayName or '<None>'}",
            f"Battle Terrain: {node_content.battleTerrainLabel or '<None>'}",
            f"Role: {node_content.roleName} [{node_content.roleId}]",
            f"Features: {', '.join(feature.name for feature in node_content.featureStates) or '<None>'}",
            f"Hooks: {', '.join(hook.name for hook in node_content.hookStates) or '<None>'}",
            f"Hazards: {', '.join(node_content.hazardTags) or '<None>'}",
            f"Affordances: {', '.join(node_content.affordanceTags) or '<None>'}",
            f"Canonical Tags: {', '.join(node_content.canonicalTags) or '<None>'}",
            "Visible Summary:",
            *(f"- {line}" for line in node_content.visibleSummaryLines[:6]),
        ]
        self._set_text_widget(self.node_summary_text, "\n".join(summary_lines))
        self._set_text_widget(self.node_local_text, node_content.localDescription or "<No local description>")
        self._set_text_widget(self.node_openai_text, node_content.openAIDescription or "<No OpenAI description cached>")

    def _filtered_missions(self):
        query = self.search_var.get().strip().lower()
        return [
            mission
            for mission in self.app.mission_service.list_missions()
            if not query or query in self.app.mission_service.get_mission_label(mission).lower()
        ]

    def refresh_mission_list(self, reset_form):
        self._refresh_biome_options()
        self._refresh_generation_profile_options()
        self._refresh_description_pack_options()
        labels = ["<New Mission>"] + [
            self.app.mission_service.get_mission_label(mission) for mission in self._filtered_missions()
        ]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set("<New Mission>")
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set("<New Mission>")

    def _on_pick(self, _evt=None):
        selected = self.pick.get().strip()
        if selected == "<New Mission>":
            self._clear_form()
            return
        mission_id = self.app.mission_service.parse_mission_id_from_label(selected)
        mission = self.app.mission_service.get_mission_by_id(mission_id)
        if mission is None:
            return
        mission_data = mission.to_dict()
        self.current_mission_id = mission.missionId
        self.name_var.set(str(mission.name or ""))
        self._set_biome_selection(mission_data.get("biomeId", ""))
        self.portal_mission_var.set(bool(mission_data.get("portalMission", True)))
        self._set_text_widget(self.terrain_pool_text, "\n".join(mission_data.get("terrainPoolIds", []) or []))
        self._set_text_widget(self.climate_pool_text, "\n".join(mission_data.get("climatePoolIds", []) or []))
        self._set_generation_profile_selection(mission_data.get("nodeGenerationProfileId", ""))
        self._set_description_pack_selection(mission_data.get("descriptionPackId", ""))
        self.objective_draft = dict(mission_data.get("objective", {}) or {})
        self.objective_label_var.set(_objective_description(self.objective_draft))
        self.allegiance_configs_draft = [dict(entry) for entry in mission_data.get("allegianceConfigs", [])]
        self._load_map_generation_range(mission_data.get("mapGenerationRange"))
        self._clear_population_preview()
        self._reset_map_preview_state(clear_map=True)
        self._clear_node_content_preview()
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _edit_objective(self):
        MissionObjectiveDialog(self, self.app, self.objective_draft, self._set_objective)

    def _set_objective(self, payload):
        self.objective_draft = dict(payload or {})
        self.objective_label_var.set(_objective_description(self.objective_draft))
        self._clear_population_preview()
        self._refresh_summary()

    def _clear_objective(self):
        self._set_objective({})

    def _allegiance_config_label(self, payload):
        allegiance_id = str(payload.get("allegianceId", "") or "").strip()
        allegiance = self.app.allegiance_service.get_allegiance_by_id(allegiance_id)
        allegiance_label = (
            self.app.allegiance_service.get_allegiance_label(allegiance)
            if allegiance is not None
            else f"Unknown [{allegiance_id}]"
        )
        unit_count = len(payload.get("unitOptions", []) or [])
        return f"{allegiance_label} | PP {int(payload.get('powerPointCap', 0) or 0)} | Lv {int(payload.get('levelMin', 0) or 0)}-{int(payload.get('levelMax', 0) or 0)} | Cluster {float(payload.get('clusterProbability', 0.0) or 0.0):.2f} +/- {float(payload.get('clusterProbabilityVariance', 0.0) or 0.0):.2f} | {unit_count} units"

    def _unit_option_summary(self, payload):
        unit_id = str(payload.get("unitId", "") or "").strip()
        unit = self.app.unit_service.get_unit_by_id(unit_id)
        unit_label = self.app.unit_service.get_unit_label(unit) if unit is not None else f"Unknown [{unit_id}]"
        capacity_min = payload.get("capacityMin")
        capacity_max = payload.get("capacityMax")
        if capacity_min is None and capacity_max is None:
            capacity_text = "No min/max"
        else:
            capacity_text = f"Min {'None' if capacity_min is None else capacity_min} / Max {'None' if capacity_max is None else capacity_max}"
        elite_text = f"Elite {float(payload.get('eliteChance', 0.0) or 0.0) * 100.0:.0f}%"
        return f"{unit_label} | {capacity_text} | {elite_text} | {'Boss' if payload.get('isBoss') else 'Regular'}"

    def _refresh_allegiance_listbox(self):
        self.allegiance_listbox.delete(0, tk.END)
        for payload in self.allegiance_configs_draft:
            self.allegiance_listbox.insert(tk.END, self._allegiance_config_label(payload))

    def _refresh_summary(self):
        biome_id = self._selected_biome_id()
        biome = self.app.environment_service.get_biome_by_id(biome_id) if biome_id else None
        biome_text = self.app.environment_service.get_biome_label(biome) if biome is not None else "<None>"
        lines = [
            f"Mission: {self.name_var.get().strip() or '<Unnamed Mission>'}",
            f"Mission ID: {self.current_mission_id or '<Unsaved>'}",
            f"Biome: {biome_text}",
            f"Terrain Pool IDs: {', '.join(self._parse_id_lines(self.terrain_pool_text.get('1.0', tk.END))) or '<Biome Default>'}",
            f"Climate Pool IDs: {', '.join(self._parse_id_lines(self.climate_pool_text.get('1.0', tk.END))) or '<Biome Default>'}",
            f"Generation Profile: {self.generation_profile_var.get().strip() or '<Default>'}",
            f"Description Pack: {self.description_pack_var.get().strip() or '<Default>'}",
            f"Portal Mission: {'Yes' if self.portal_mission_var.get() else 'No'}",
            f"Map Generation: {self._map_generation_summary_text()}",
            f"Objective: {_objective_description(self.objective_draft)}",
            "",
            "Mission Allegiances:",
        ]
        if not self.allegiance_configs_draft:
            lines.append("<None>")
        else:
            for index, payload in enumerate(self.allegiance_configs_draft, start=1):
                lines.append(f"{index}. {self._allegiance_config_label(payload)}")
                for unit_payload in payload.get("unitOptions", []) or []:
                    lines.append(f"   - {self._unit_option_summary(unit_payload)}")
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, "\n".join(lines))

    def _selected_allegiance_index(self):
        selection = self.allegiance_listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        return index if 0 <= index < len(self.allegiance_configs_draft) else None

    def _add_allegiance_config(self):
        exclude_ids = [entry.get("allegianceId") for entry in self.allegiance_configs_draft]
        MissionAllegianceConfigDialog(
            self, self.app, None, self._append_allegiance_config, exclude_allegiance_ids=exclude_ids
        )

    def _append_allegiance_config(self, payload):
        allegiance_id = str(payload.get("allegianceId", "") or "").strip()
        if allegiance_id in {
            str(entry.get("allegianceId", "") or "").strip() for entry in self.allegiance_configs_draft
        }:
            messagebox.showerror("Mission Editor", "That allegiance is already included in this mission.")
            return
        self.allegiance_configs_draft.append(payload)
        self._clear_population_preview()
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _edit_selected_allegiance_config(self):
        index = self._selected_allegiance_index()
        if index is None:
            messagebox.showerror("Mission Editor", "Select a mission allegiance to edit.")
            return
        exclude_ids = [
            entry.get("allegianceId")
            for position, entry in enumerate(self.allegiance_configs_draft)
            if position != index
        ]
        MissionAllegianceConfigDialog(
            self,
            self.app,
            dict(self.allegiance_configs_draft[index]),
            lambda payload: self._replace_allegiance_config(index, payload),
            exclude_allegiance_ids=exclude_ids,
        )

    def _replace_allegiance_config(self, index, payload):
        allegiance_id = str(payload.get("allegianceId", "") or "").strip()
        other_ids = {
            str(entry.get("allegianceId", "") or "").strip()
            for position, entry in enumerate(self.allegiance_configs_draft)
            if position != index
        }
        if allegiance_id in other_ids:
            messagebox.showerror("Mission Editor", "That allegiance is already included in this mission.")
            return
        self.allegiance_configs_draft[index] = payload
        self._clear_population_preview()
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _remove_selected_allegiance_config(self):
        index = self._selected_allegiance_index()
        if index is None:
            return
        self.allegiance_configs_draft.pop(index)
        self._clear_population_preview()
        self._refresh_allegiance_listbox()
        self._refresh_summary()

    def _build_preview_template(self):
        objective_payload = (
            dict(self.objective_draft)
            if self.objective_draft
            else {
                "objectiveType": "SURVIVAL",
                "requiredHoursSurvived": 1.0,
            }
        )
        return MissionTemplate.from_dict(
            {
                "name": str(self.name_var.get() or "").strip() or "Mission Preview",
                "biomeId": self._selected_biome_id(),
                "portalMission": bool(self.portal_mission_var.get()),
                "terrainPoolIds": self._parse_id_lines(self.terrain_pool_text.get("1.0", tk.END)),
                "climatePoolIds": self._parse_id_lines(self.climate_pool_text.get("1.0", tk.END)),
                "nodeGenerationProfileId": self._selected_generation_profile_id(),
                "descriptionPackId": self._selected_description_pack_id(),
                "mapGenerationRange": self._build_map_generation_range_payload(),
                "objective": objective_payload,
                "allegianceConfigs": list(self.allegiance_configs_draft),
            }
        )

    def _preview_unit_label(self, populated_unit):
        allegiance = self.app.allegiance_service.get_allegiance_by_id(populated_unit.allegianceId)
        allegiance_label = (
            self.app.allegiance_service.get_allegiance_label(allegiance)
            if allegiance is not None
            else f"Unknown [{populated_unit.allegianceId}]"
        )
        flags = []
        if populated_unit.isRequired:
            flags.append("required")
        if populated_unit.isBoss:
            flags.append("boss")
        elif populated_unit.isElite:
            flags.append("elite")
        flag_text = f" | {', '.join(flags)}" if flags else ""
        return (
            f"{getattr(populated_unit.character, 'name', 'Unit')} | {allegiance_label}"
            f" | {populated_unit.pointsSpent} PP{flag_text}"
        )

    def _refresh_population_preview(self):
        self.preview_summary.configure(state="normal")
        self.preview_summary.delete("1.0", tk.END)
        self.preview_listbox.delete(0, tk.END)

        if self.population_preview is None:
            self.preview_summary.insert(
                tk.END,
                "No preview generated yet. Use 'Generate Example Units' to sample units from the current mission draft.",
            )
            self.preview_summary.configure(state="disabled")
            return

        lines = [
            f"Mission: {self.population_preview.missionName}",
            f"Total Points Spent: {self.population_preview.totalPointsSpent}",
            f"Total Unused Points: {self.population_preview.totalUnusedPoints}",
            "",
        ]
        for result in self.population_preview.allegiances:
            allegiance = self.app.allegiance_service.get_allegiance_by_id(result.allegianceId)
            allegiance_label = (
                self.app.allegiance_service.get_allegiance_label(allegiance)
                if allegiance is not None
                else f"Unknown [{result.allegianceId}]"
            )
            lines.append(
                f"{allegiance_label}: spent {result.pointsSpent}/{result.powerPointCap} PP, unused {result.unusedPoints} PP"
            )
            for group in result.groups:
                lines.append(f"  - {group.unitLabel}: {group.count} generated, {group.pointsSpent} PP")
            if not result.groups:
                lines.append("  - No units generated")

        self.preview_summary.insert(tk.END, "\n".join(lines))
        self.preview_units = list(self.population_preview.generatedUnits)
        for populated_unit in self.preview_units:
            self.preview_listbox.insert(tk.END, self._preview_unit_label(populated_unit))
        self.preview_summary.configure(state="disabled")

    def _clear_population_preview(self):
        self.population_preview = None
        self.preview_units = []
        self._clear_character_and_clue_overlays()
        if hasattr(self, "preview_summary") and hasattr(self, "preview_listbox"):
            self._refresh_population_preview()

    def _generate_population_preview(self):
        if not self.allegiance_configs_draft:
            messagebox.showerror("Mission Editor", "Add at least one mission allegiance before generating a preview.")
            return
        try:
            preview_template = self._build_preview_template()
            self.population_preview = self.unit_populator.populate(preview_template)
            self._clear_character_and_clue_overlays()
            self._refresh_population_preview()
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to generate mission units: {exc}")

    def _selected_preview_unit(self):
        selection = self.preview_listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        return self.preview_units[index] if 0 <= index < len(self.preview_units) else None

    def _load_map_generation_range(self, payload):
        map_range = payload if isinstance(payload, MissionMapGenerationRange) else MissionMapGenerationRange.from_dict(payload)
        self.map_range_vars["totalNodes"]["low"].set(str(map_range.totalNodesLow))
        self.map_range_vars["totalNodes"]["high"].set(str(map_range.totalNodesHigh))
        self.map_range_vars["narrowness"]["low"].set(str(map_range.narrownessLow))
        self.map_range_vars["narrowness"]["high"].set(str(map_range.narrownessHigh))
        self.map_range_vars["connectedness"]["low"].set(str(map_range.connectednessLow))
        self.map_range_vars["connectedness"]["high"].set(str(map_range.connectednessHigh))
        self.map_range_vars["deadEndLikelihood"]["low"].set(str(map_range.deadEndLikelihoodLow))
        self.map_range_vars["deadEndLikelihood"]["high"].set(str(map_range.deadEndLikelihoodHigh))
        self.map_range_vars["nodeJitterFraction"]["low"].set(str(map_range.nodeJitterFractionLow))
        self.map_range_vars["nodeJitterFraction"]["high"].set(str(map_range.nodeJitterFractionHigh))

    def _build_map_generation_range_payload(self):
        return {
            "totalNodesLow": max(1, _safe_int(self.map_range_vars["totalNodes"]["low"].get().strip() or 60, 60)),
            "totalNodesHigh": max(1, _safe_int(self.map_range_vars["totalNodes"]["high"].get().strip() or 60, 60)),
            "narrownessLow": _safe_float(self.map_range_vars["narrowness"]["low"].get().strip() or 0.5, 0.5),
            "narrownessHigh": _safe_float(self.map_range_vars["narrowness"]["high"].get().strip() or 0.5, 0.5),
            "connectednessLow": _safe_float(self.map_range_vars["connectedness"]["low"].get().strip() or 0.25, 0.25),
            "connectednessHigh": _safe_float(self.map_range_vars["connectedness"]["high"].get().strip() or 0.25, 0.25),
            "deadEndLikelihoodLow": _safe_float(self.map_range_vars["deadEndLikelihood"]["low"].get().strip() or 0.7, 0.7),
            "deadEndLikelihoodHigh": _safe_float(self.map_range_vars["deadEndLikelihood"]["high"].get().strip() or 0.7, 0.7),
            "nodeJitterFractionLow": _safe_float(self.map_range_vars["nodeJitterFraction"]["low"].get().strip() or 0.45, 0.45),
            "nodeJitterFractionHigh": _safe_float(self.map_range_vars["nodeJitterFraction"]["high"].get().strip() or 0.45, 0.45),
        }

    def _build_map_generation_range(self) -> MissionMapGenerationRange:
        return MissionMapGenerationRange.from_dict(self._build_map_generation_range_payload())

    def _map_generation_summary_text(self) -> str:
        return self._build_map_generation_range().summary()

    def _reset_map_preview_state(self, clear_map: bool = False):
        if clear_map:
            self.current_map = None
            self.map_preview_photo = None
        self.current_map_overlay = MissionMapOverlay()
        self._clear_node_content_preview()
        self._render_current_map_preview()

    def _clear_character_and_clue_overlays(self):
        self.current_map_overlay.unitsByNode = {}
        self.current_map_overlay.clueTargetNodeByNode = {}
        self._refresh_node_content_preview_from_current_state()

    def _render_current_map_preview(self):
        if self.current_map is None:
            self.map_preview_photo = None
            self.map_preview_label.configure(image="")
            self.map_summary_var.set("Generate a map preview to inspect mission layout.")
            return

        image = render_mission_map_image(
            self.current_map,
            width=self.MAP_PREVIEW_WIDTH,
            height=self.MAP_PREVIEW_HEIGHT,
            overlay=self.current_map_overlay,
        )
        self.map_preview_photo = ImageTk.PhotoImage(image)
        self.map_preview_label.configure(image=self.map_preview_photo)
        setting_summary = "No sampled setting yet."
        if self.current_setting_context is not None:
            setting_summary = (
                f"Sampled Setting: {self.current_setting_context.biomeName} | "
                f"{self.current_setting_context.terrainName} | {self.current_setting_context.climateName}"
            )
        self.map_summary_var.set(
            "\n".join(
                [
                    f"Seed: {self.current_map.settings.seed}",
                    f"Actual Settings: nodes {self.current_map.settings.total_nodes}, narrowness {self.current_map.settings.narrowness:.2f}, connectedness {self.current_map.settings.connectedness:.2f}, dead ends {self.current_map.settings.dead_end_likelihood:.2f}, jitter {self.current_map.settings.node_jitter_fraction:.2f}",
                    setting_summary,
                    f"Node Content: {len(self.current_node_contents)} nodes generated",
                    f"Characters: {self.current_map_overlay.totalPlacedCharacters} across {len(self.current_map_overlay.characterCountByNode)} nodes",
                    f"Treasure: {len(self.current_map_overlay.nanoByNode)} nodes, {self.current_map_overlay.totalNano} Nano total",
                    f"Clues: {len(self.current_map_overlay.clueTargetNodeByNode)} nodes",
                ]
            )
        )

    def _refresh_node_content_preview_from_current_state(self):
        if self.current_map is None:
            self._clear_node_content_preview()
            self._render_current_map_preview()
            return
        try:
            setting_context, node_contents = generate_node_content_preview(
                self.app.environment_service,
                self.current_map,
                self._build_preview_template(),
                seed=self.current_map.settings.seed,
            )
            self.current_setting_context = setting_context
            self.current_node_contents = apply_overlay_to_node_contents(node_contents, self.current_map_overlay)
            self.sampled_setting_var.set(
                f"Sampled Setting: {setting_context.biomeName} | {setting_context.terrainName} | {setting_context.climateName}"
            )
            self._refresh_node_selector()
            self._render_selected_node_preview()
        except Exception as exc:
            self._clear_node_content_preview()
            messagebox.showerror("Mission Editor", f"Failed to generate node content preview: {exc}")
        self._render_current_map_preview()

    def _generate_node_content_preview(self):
        if not self._ensure_current_map():
            return
        self._refresh_node_content_preview_from_current_state()

    def _regenerate_selected_node_content(self):
        selected_node_id = self._selected_node_id()
        if not self._ensure_current_map():
            return
        self._refresh_node_content_preview_from_current_state()
        if selected_node_id is not None:
            self.selected_node_var.set(str(selected_node_id))
        self._render_selected_node_preview()

    def _generate_openai_for_selected_node(self):
        node_id = self._selected_node_id()
        if node_id is None:
            messagebox.showerror("Mission Editor", "Select a node first.")
            return
        if self.current_setting_context is None or node_id not in self.current_node_contents:
            messagebox.showerror("Mission Editor", "Generate node content first.")
            return
        if getattr(self.app, "openai_service", None) is None or not self.app.openai_service.is_configured():
            messagebox.showerror("Mission Editor", "OpenAI is not configured.")
            return
        try:
            prompt_packet = build_scene_description_prompt_packet(
                self.current_setting_context,
                self.current_node_contents[node_id],
            )
            self.current_node_contents[node_id].openAIDescription = self.app.openai_service.describe_scene(prompt_packet)
            self._render_selected_node_preview()
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to generate OpenAI description: {exc}")

    def _ensure_current_map(self) -> bool:
        if self.current_map is not None:
            return True
        self._generate_map_preview()
        return self.current_map is not None

    def _ensure_population_preview(self) -> bool:
        if self.population_preview is not None:
            return True
        self._generate_population_preview()
        return self.population_preview is not None

    def _generate_map_preview(self):
        try:
            self.current_map = generate_map_from_range(self._build_map_generation_range())
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to generate mission map: {exc}")
            return
        self.current_map_overlay = MissionMapOverlay()
        self._refresh_node_content_preview_from_current_state()

    def _place_characters_on_map(self):
        if not self._ensure_population_preview() or not self._ensure_current_map():
            return
        try:
            self.current_map_overlay = place_characters_on_map(
                self.current_map,
                self._build_preview_template(),
                self.population_preview,
                existing_overlay=self.current_map_overlay,
            )
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to place characters on the map: {exc}")
            return
        self._refresh_node_content_preview_from_current_state()

    def _generate_treasure_on_map(self):
        if not self._ensure_current_map():
            return
        try:
            self.current_map_overlay = generate_treasure_overlay(
                self.current_map,
                existing_overlay=self.current_map_overlay,
            )
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to generate treasure: {exc}")
            return
        self._refresh_node_content_preview_from_current_state()

    def _generate_clues_on_map(self):
        if not self._ensure_current_map():
            return
        try:
            self.current_map_overlay = generate_clue_overlay(
                self.current_map,
                existing_overlay=self.current_map_overlay,
            )
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to generate clues: {exc}")
            return
        self._refresh_node_content_preview_from_current_state()

    def _generate_all_map_features(self):
        if not self._ensure_population_preview() or not self._ensure_current_map():
            return
        try:
            self.current_map_overlay = generate_all_map_features(
                self.current_map,
                self._build_preview_template(),
                self.population_preview,
                existing_overlay=self.current_map_overlay,
            )
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to generate mission map features: {exc}")
            return
        self._refresh_node_content_preview_from_current_state()

    def _view_selected_preview_unit(self):
        populated_unit = self._selected_preview_unit()
        if populated_unit is None:
            messagebox.showerror("Mission Editor", "Select a generated unit to view.")
            return
        ReadonlyCharacterViewer(self, populated_unit.character, title=f"Unit Preview - {populated_unit.character.name}")

    def _save(self):
        payload = {
            "name": str(self.name_var.get() or "").strip(),
            "biomeId": self._selected_biome_id(),
            "portalMission": bool(self.portal_mission_var.get()),
            "terrainPoolIds": self._parse_id_lines(self.terrain_pool_text.get("1.0", tk.END)),
            "climatePoolIds": self._parse_id_lines(self.climate_pool_text.get("1.0", tk.END)),
            "nodeGenerationProfileId": self._selected_generation_profile_id(),
            "descriptionPackId": self._selected_description_pack_id(),
            "mapGenerationRange": self._build_map_generation_range_payload(),
            "objective": dict(self.objective_draft),
            "allegianceConfigs": list(self.allegiance_configs_draft),
        }
        if not payload["name"]:
            messagebox.showerror("Mission Editor", "Mission name is required.")
            return
        if not payload["objective"]:
            messagebox.showerror("Mission Editor", "Mission objective is required.")
            return
        try:
            mission = (
                self.app.mission_service.edit_mission_from_patch(self.current_mission_id, payload)
                if self.current_mission_id
                else self.app.mission_service.create_mission_from_dict(payload)
            )
            messagebox.showinfo("Mission Editor", "Mission saved.")
            self.refresh_mission_list(reset_form=False)
            self.pick_var.set(self.app.mission_service.get_mission_label(mission))
            self.current_mission_id = mission.missionId
            mission_data = mission.to_dict()
            self._set_biome_selection(mission_data.get("biomeId", ""))
            self.portal_mission_var.set(bool(mission_data.get("portalMission", True)))
            self._set_text_widget(self.terrain_pool_text, "\n".join(mission_data.get("terrainPoolIds", []) or []))
            self._set_text_widget(self.climate_pool_text, "\n".join(mission_data.get("climatePoolIds", []) or []))
            self._set_generation_profile_selection(mission_data.get("nodeGenerationProfileId", ""))
            self._set_description_pack_selection(mission_data.get("descriptionPackId", ""))
            self.objective_draft = dict(mission_data.get("objective", {}) or {})
            self.objective_label_var.set(_objective_description(self.objective_draft))
            self.allegiance_configs_draft = [dict(entry) for entry in mission_data.get("allegianceConfigs", [])]
            self._load_map_generation_range(mission_data.get("mapGenerationRange"))
            self._reset_map_preview_state(clear_map=True)
            self._refresh_allegiance_listbox()
            self._refresh_summary()
        except Exception as exc:
            messagebox.showerror("Mission Editor", f"Failed to save mission: {exc}")
