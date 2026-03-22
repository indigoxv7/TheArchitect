from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox, ttk

from src.domain.location_content import (
    CompatibilitySelectionMode,
    HookType,
    IncompatibilityMode,
    SceneDescriptionMode,
)
from .dialogs import (
    format_json_dict,
    format_text_lines,
    format_weighted_fragments,
    parse_json_dict,
    parse_tag_lines,
    parse_text_lines,
    parse_weighted_fragments,
    safe_float,
    safe_int,
)


ID_PATTERN = re.compile(r"\[([^\]]+)\]\s*$")


class _CatalogTabBase(ttk.Frame):
    SELECT_LABEL = "Select Entry"
    BLANK_LABEL = "<New Entry>"
    SAVE_LABEL = "Save"
    LIST_METHOD = ""
    GET_METHOD = ""
    CREATE_METHOD = ""
    EDIT_METHOD = ""
    LABEL_METHOD = ""
    FIELD_SPECS: list[dict] = []
    HELP_TEXT = ""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_id = ""
        self.widgets: dict[str, object] = {}
        self.pick_var = tk.StringVar(value=self.BLANK_LABEL)
        self.search_var = tk.StringVar()

        search_row = ttk.Frame(self)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search", width=18).pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_list(reset_form=False))

        pick_row = ttk.Frame(self)
        pick_row.pack(fill=tk.X, pady=4)
        ttk.Label(pick_row, text=self.SELECT_LABEL, width=18).pack(side=tk.LEFT)
        self.pick = ttk.Combobox(pick_row, state="readonly", textvariable=self.pick_var)
        self.pick.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pick.bind("<<ComboboxSelected>>", self._on_pick)

        if self.HELP_TEXT:
            ttk.Label(self, text=self.HELP_TEXT, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 6))

        for spec in self.FIELD_SPECS:
            self._build_field(spec)

        ttk.Button(self, text=self.SAVE_LABEL, command=self._save).pack(fill=tk.X, pady=8)
        self._clear_form()

    def _build_field(self, spec: dict):
        kind = spec.get("kind", "entry")
        label = spec["label"]
        name = spec["name"]
        height = int(spec.get("height", 4) or 4)
        values = list(spec.get("values", []))

        row = ttk.Frame(self)
        row.pack(fill=tk.BOTH, expand=(kind in {"text", "tags", "lines", "json", "fragments"}), pady=2)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT, anchor="n")

        if kind == "enum":
            var = tk.StringVar(value=values[0] if values else "")
            widget = ttk.Combobox(row, state="readonly", values=values, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.widgets[name] = var
            return

        if kind in {"entry", "float", "int"}:
            var = tk.StringVar()
            widget = ttk.Entry(row, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.widgets[name] = var
            return

        text_widget = tk.Text(row, height=height, wrap=tk.WORD)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.widgets[name] = text_widget

    def _service_method(self, name: str):
        return getattr(self.app.environment_service, name)

    def _list_entries(self):
        return list(self._service_method(self.LIST_METHOD)())

    def _get_entry(self, identifier: str):
        return self._service_method(self.GET_METHOD)(identifier)

    def _label_entry(self, entry) -> str:
        return self._service_method(self.LABEL_METHOD)(entry)

    @staticmethod
    def _parse_id(label: str) -> str:
        text = str(label or "").strip()
        match = ID_PATTERN.search(text)
        if match:
            return match.group(1).strip()
        return text

    def _filtered_entries(self):
        query = str(self.search_var.get() or "").strip().lower()
        result = []
        for entry in self._list_entries():
            label = self._label_entry(entry)
            if query and query not in label.lower():
                continue
            result.append((self._parse_id(label), label))
        return result

    def refresh_list(self, reset_form: bool):
        labels = [self.BLANK_LABEL] + [label for _entry_id, label in self._filtered_entries()]
        self.pick["values"] = labels
        if reset_form:
            self.pick_var.set(self.BLANK_LABEL)
            self._clear_form()
        elif self.pick_var.get() not in labels:
            self.pick_var.set(self.BLANK_LABEL)

    def _widget_set(self, name: str, value):
        widget = self.widgets[name]
        if isinstance(widget, tk.StringVar):
            widget.set(str(value or ""))
            return
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, str(value or ""))

    def _widget_get(self, name: str) -> str:
        widget = self.widgets[name]
        if isinstance(widget, tk.StringVar):
            return str(widget.get() or "")
        return widget.get("1.0", tk.END).strip()

    def _clear_form(self):
        self.current_id = ""
        for spec in self.FIELD_SPECS:
            name = spec["name"]
            kind = spec.get("kind", "entry")
            default = spec.get("default", [] if kind in {"tags", "lines", "fragments"} else {})
            if kind == "enum":
                values = list(spec.get("values", []))
                self._widget_set(name, default or (values[0] if values else ""))
            elif kind == "json":
                self._widget_set(name, format_json_dict(default if isinstance(default, dict) else {}))
            elif kind == "fragments":
                self._widget_set(name, format_weighted_fragments(default if isinstance(default, list) else []))
            elif kind in {"tags", "lines", "ids"}:
                self._widget_set(name, format_text_lines(default if isinstance(default, list) else []))
            else:
                self._widget_set(name, default if default not in (None, {}) else "")

    def _load_existing(self, identifier: str):
        entry = self._get_entry(identifier)
        if entry is None:
            return
        payload = entry.to_dict() if hasattr(entry, "to_dict") else {}
        self.current_id = identifier
        for spec in self.FIELD_SPECS:
            name = spec["name"]
            kind = spec.get("kind", "entry")
            value = payload.get(name, spec.get("default", ""))
            if kind == "json":
                self._widget_set(name, format_json_dict(value if isinstance(value, dict) else {}))
            elif kind == "fragments":
                self._widget_set(name, format_weighted_fragments(value if isinstance(value, list) else []))
            elif kind in {"tags", "lines", "ids"}:
                self._widget_set(name, format_text_lines(value if isinstance(value, list) else []))
            else:
                self._widget_set(name, value)

    def _on_pick(self, _event=None):
        selected = str(self.pick_var.get() or "").strip()
        if selected == self.BLANK_LABEL:
            self._clear_form()
            return
        identifier = self._parse_id(selected)
        self._load_existing(identifier)

    def _collect_payload(self) -> dict:
        payload = {}
        for spec in self.FIELD_SPECS:
            name = spec["name"]
            kind = spec.get("kind", "entry")
            raw = self._widget_get(name)
            if kind == "entry":
                payload[name] = raw.strip()
            elif kind == "text":
                payload[name] = raw
            elif kind == "int":
                payload[name] = safe_int(raw, spec.get("default", 0))
            elif kind == "float":
                payload[name] = safe_float(raw, spec.get("default", 0.0))
            elif kind == "tags":
                payload[name] = parse_tag_lines(raw)
            elif kind in {"lines", "ids"}:
                payload[name] = parse_text_lines(raw)
            elif kind == "json":
                payload[name] = parse_json_dict(raw)
            elif kind == "enum":
                payload[name] = raw.strip()
            elif kind == "fragments":
                payload[name] = parse_weighted_fragments(raw)
            else:
                payload[name] = raw
        return payload

    def _save(self):
        try:
            payload = self._collect_payload()
        except Exception as exc:
            messagebox.showerror(self.SELECT_LABEL, f"Invalid form values: {exc}")
            return
        if not str(payload.get("name", "") or "").strip():
            messagebox.showerror(self.SELECT_LABEL, "Name is required.")
            return
        try:
            if self.current_id:
                entry = self._service_method(self.EDIT_METHOD)(self.current_id, payload)
                self.current_id = self._parse_id(self._label_entry(entry))
            else:
                entry = self._service_method(self.CREATE_METHOD)(payload)
                self.current_id = self._parse_id(self._label_entry(entry))
            self.refresh_list(reset_form=False)
            self.pick_var.set(self._label_entry(entry))
            messagebox.showinfo(self.SELECT_LABEL, "Saved.")
        except Exception as exc:
            messagebox.showerror(self.SELECT_LABEL, f"Failed to save entry: {exc}")


class TerrainTab(_CatalogTabBase):
    SELECT_LABEL = "Select Terrain"
    SAVE_LABEL = "Save Terrain"
    LIST_METHOD = "list_terrains"
    GET_METHOD = "get_terrain_by_id"
    CREATE_METHOD = "create_terrain_from_dict"
    EDIT_METHOD = "edit_terrain_from_patch"
    LABEL_METHOD = "get_terrain_label"
    FIELD_SPECS = [
        {"name": "name", "label": "Name", "kind": "entry"},
        {"name": "description", "label": "Description", "kind": "text", "height": 4},
        {"name": "canonicalTags", "label": "Canonical Tags", "kind": "tags", "height": 3},
        {"name": "landformTags", "label": "Landform Tags", "kind": "tags", "height": 3},
        {"name": "traversalTags", "label": "Traversal Tags", "kind": "tags", "height": 3},
        {"name": "visibilityTags", "label": "Visibility Tags", "kind": "tags", "height": 3},
        {"name": "wetnessTags", "label": "Wetness Tags", "kind": "tags", "height": 3},
        {"name": "obstacleTags", "label": "Obstacle Tags", "kind": "tags", "height": 3},
    ]


class ClimateTab(_CatalogTabBase):
    SELECT_LABEL = "Select Climate"
    SAVE_LABEL = "Save Climate"
    LIST_METHOD = "list_climates"
    GET_METHOD = "get_climate_by_id"
    CREATE_METHOD = "create_climate_from_dict"
    EDIT_METHOD = "edit_climate_from_patch"
    LABEL_METHOD = "get_climate_label"
    FIELD_SPECS = [
        {"name": "name", "label": "Name", "kind": "entry"},
        {"name": "temperature", "label": "Temperature", "kind": "entry"},
        {"name": "humidity", "label": "Humidity", "kind": "entry"},
        {"name": "description", "label": "Description", "kind": "text", "height": 4},
        {"name": "canonicalTags", "label": "Canonical Tags", "kind": "tags", "height": 3},
        {"name": "weatherTags", "label": "Weather Tags", "kind": "tags", "height": 3},
        {"name": "floodTags", "label": "Flood Tags", "kind": "tags", "height": 3},
        {"name": "fogTags", "label": "Fog Tags", "kind": "tags", "height": 3},
        {"name": "seasonalityTags", "label": "Seasonality Tags", "kind": "tags", "height": 3},
    ]


class BiomeTab(_CatalogTabBase):
    SELECT_LABEL = "Select Biome"
    SAVE_LABEL = "Save Biome"
    LIST_METHOD = "list_biomes"
    GET_METHOD = "get_biome_by_id"
    CREATE_METHOD = "create_biome_from_dict"
    EDIT_METHOD = "edit_biome_from_patch"
    LABEL_METHOD = "get_biome_label"
    FIELD_SPECS = [
        {"name": "name", "label": "Name", "kind": "entry"},
        {"name": "description", "label": "Description", "kind": "text", "height": 4},
        {"name": "terrainCompatibilityMode", "label": "Terrain Mode", "kind": "enum", "values": [entry.name for entry in CompatibilitySelectionMode]},
        {"name": "compatibleTerrainIds", "label": "Compatible Terrain IDs", "kind": "ids", "height": 4},
        {"name": "terrainIncompatibilityMode", "label": "Terrain Exclusions", "kind": "enum", "values": [entry.name for entry in IncompatibilityMode]},
        {"name": "incompatibleTerrainIds", "label": "Incompatible Terrain IDs", "kind": "ids", "height": 4},
        {"name": "climateCompatibilityMode", "label": "Climate Mode", "kind": "enum", "values": [entry.name for entry in CompatibilitySelectionMode]},
        {"name": "compatibleClimateIds", "label": "Compatible Climate IDs", "kind": "ids", "height": 4},
        {"name": "climateIncompatibilityMode", "label": "Climate Exclusions", "kind": "enum", "values": [entry.name for entry in IncompatibilityMode]},
        {"name": "incompatibleClimateIds", "label": "Incompatible Climate IDs", "kind": "ids", "height": 4},
        {"name": "canonicalBaseTags", "label": "Canonical Base Tags", "kind": "tags", "height": 3},
        {"name": "civilizationPriors", "label": "Civilization Priors", "kind": "tags", "height": 3},
        {"name": "threatPriors", "label": "Threat Priors", "kind": "tags", "height": 3},
        {"name": "resourcePriors", "label": "Resource Priors", "kind": "tags", "height": 3},
        {"name": "mythicPriors", "label": "Mythic Priors", "kind": "tags", "height": 3},
        {"name": "ecologyPriors", "label": "Ecology Priors", "kind": "tags", "height": 3},
    ]


class NodeRoleTab(_CatalogTabBase):
    SELECT_LABEL = "Select Node Role"
    SAVE_LABEL = "Save Node Role"
    LIST_METHOD = "list_node_roles"
    GET_METHOD = "get_node_role_by_id"
    CREATE_METHOD = "create_node_role_from_dict"
    EDIT_METHOD = "edit_node_role_from_patch"
    LABEL_METHOD = "get_node_role_label"
    FIELD_SPECS = [
        {"name": "name", "label": "Name", "kind": "entry"},
        {"name": "description", "label": "Description", "kind": "text", "height": 4},
        {"name": "weight", "label": "Weight", "kind": "float", "default": 1.0},
        {"name": "roleTags", "label": "Role Tags", "kind": "tags", "height": 3},
        {"name": "requiredTags", "label": "Required Tags", "kind": "tags", "height": 3},
        {"name": "excludedTags", "label": "Excluded Tags", "kind": "tags", "height": 3},
        {"name": "desiredAffordanceTags", "label": "Desired Affordances", "kind": "tags", "height": 3},
        {"name": "desiredHazardTags", "label": "Desired Hazards", "kind": "tags", "height": 3},
        {"name": "desiredHookTypes", "label": "Desired Hook Types", "kind": "lines", "height": 3},
        {"name": "minFeatures", "label": "Min Features", "kind": "int", "default": 1},
        {"name": "maxFeatures", "label": "Max Features", "kind": "int", "default": 3},
    ]


class FeatureTab(_CatalogTabBase):
    SELECT_LABEL = "Select Feature"
    SAVE_LABEL = "Save Feature"
    LIST_METHOD = "list_feature_templates"
    GET_METHOD = "get_feature_template_by_id"
    CREATE_METHOD = "create_feature_template_from_dict"
    EDIT_METHOD = "edit_feature_template_from_patch"
    LABEL_METHOD = "get_feature_label"
    FIELD_SPECS = [
        {"name": "name", "label": "Name", "kind": "entry"},
        {"name": "category", "label": "Category", "kind": "entry"},
        {"name": "description", "label": "Description", "kind": "text", "height": 4},
        {"name": "weight", "label": "Weight", "kind": "float", "default": 1.0},
        {"name": "requiredTags", "label": "Required Tags", "kind": "tags", "height": 3},
        {"name": "excludedTags", "label": "Excluded Tags", "kind": "tags", "height": 3},
        {"name": "tags", "label": "Tags", "kind": "tags", "height": 3},
        {"name": "affordanceTags", "label": "Affordance Tags", "kind": "tags", "height": 3},
        {"name": "hazardTags", "label": "Hazard Tags", "kind": "tags", "height": 3},
        {"name": "memoryTags", "label": "Memory Tags", "kind": "tags", "height": 3},
        {"name": "visibleTags", "label": "Visible Tags", "kind": "tags", "height": 3},
        {"name": "hookTypeSuggestions", "label": "Hook Suggestions", "kind": "lines", "height": 3},
        {"name": "metrics", "label": "Metrics JSON", "kind": "json", "height": 5, "default": {}},
        {"name": "payload", "label": "Payload JSON", "kind": "json", "height": 5, "default": {}},
        {"name": "localDescriptionHints", "label": "Local Description Hints", "kind": "lines", "height": 4},
    ]


class HookTab(_CatalogTabBase):
    SELECT_LABEL = "Select Hook"
    SAVE_LABEL = "Save Hook"
    LIST_METHOD = "list_hook_templates"
    GET_METHOD = "get_hook_template_by_id"
    CREATE_METHOD = "create_hook_template_from_dict"
    EDIT_METHOD = "edit_hook_template_from_patch"
    LABEL_METHOD = "get_hook_label"
    FIELD_SPECS = [
        {"name": "name", "label": "Name", "kind": "entry"},
        {"name": "hookType", "label": "Hook Type", "kind": "enum", "values": [entry.name for entry in HookType]},
        {"name": "description", "label": "Description", "kind": "text", "height": 4},
        {"name": "weight", "label": "Weight", "kind": "float", "default": 1.0},
        {"name": "requiredTags", "label": "Required Tags", "kind": "tags", "height": 3},
        {"name": "excludedTags", "label": "Excluded Tags", "kind": "tags", "height": 3},
        {"name": "tags", "label": "Tags", "kind": "tags", "height": 3},
        {"name": "memoryTags", "label": "Memory Tags", "kind": "tags", "height": 3},
        {"name": "visibleText", "label": "Visible Text", "kind": "text", "height": 4},
        {"name": "payload", "label": "Payload JSON", "kind": "json", "height": 5, "default": {}},
    ]


class DescriptionPackTab(_CatalogTabBase):
    SELECT_LABEL = "Select Description Pack"
    SAVE_LABEL = "Save Description Pack"
    LIST_METHOD = "list_description_packs"
    GET_METHOD = "get_description_pack_by_id"
    CREATE_METHOD = "create_description_pack_from_dict"
    EDIT_METHOD = "edit_description_pack_from_patch"
    LABEL_METHOD = "get_description_pack_label"
    HELP_TEXT = "Fragment format: text || weight || required tags || excluded tags"
    FIELD_SPECS = [
        {"name": "name", "label": "Name", "kind": "entry"},
        {"name": "description", "label": "Description", "kind": "text", "height": 4},
        {"name": "openaiHint", "label": "OpenAI Hint", "kind": "text", "height": 4},
        {"name": "openingFragments", "label": "Opening Fragments", "kind": "fragments", "height": 5},
        {"name": "landmarkFragments", "label": "Landmark Fragments", "kind": "fragments", "height": 5},
        {"name": "atmosphereFragments", "label": "Atmosphere Fragments", "kind": "fragments", "height": 5},
        {"name": "hazardFragments", "label": "Hazard Fragments", "kind": "fragments", "height": 5},
        {"name": "affordanceFragments", "label": "Affordance Fragments", "kind": "fragments", "height": 5},
        {"name": "closingFragments", "label": "Closing Fragments", "kind": "fragments", "height": 5},
    ]


class GenerationProfileTab(_CatalogTabBase):
    SELECT_LABEL = "Select Generation Profile"
    SAVE_LABEL = "Save Generation Profile"
    LIST_METHOD = "list_generation_profiles"
    GET_METHOD = "get_generation_profile_by_id"
    CREATE_METHOD = "create_generation_profile_from_dict"
    EDIT_METHOD = "edit_generation_profile_from_patch"
    LABEL_METHOD = "get_generation_profile_label"
    FIELD_SPECS = [
        {"name": "name", "label": "Name", "kind": "entry"},
        {"name": "description", "label": "Description", "kind": "text", "height": 4},
        {"name": "rendererMode", "label": "Renderer Mode", "kind": "enum", "values": [entry.name for entry in SceneDescriptionMode]},
        {"name": "roleWeights", "label": "Role Weights JSON", "kind": "json", "height": 5, "default": {}},
        {"name": "minFeatures", "label": "Min Features", "kind": "int", "default": 1},
        {"name": "maxFeatures", "label": "Max Features", "kind": "int", "default": 3},
        {"name": "minHooks", "label": "Min Hooks", "kind": "int", "default": 0},
        {"name": "maxHooks", "label": "Max Hooks", "kind": "int", "default": 2},
        {"name": "antiRepetitionStrength", "label": "Anti-Repetition", "kind": "float", "default": 0.4},
        {"name": "hazardBias", "label": "Hazard Bias", "kind": "float", "default": 1.0},
        {"name": "affordanceBias", "label": "Affordance Bias", "kind": "float", "default": 1.0},
        {"name": "hookBias", "label": "Hook Bias", "kind": "float", "default": 1.0},
    ]


class EnvironmentEditorFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side=tk.LEFT)
        ttk.Label(top, text="Location Content Editor", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=10)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.terrain_tab = TerrainTab(notebook, app)
        self.climate_tab = ClimateTab(notebook, app)
        self.biome_tab = BiomeTab(notebook, app)
        self.role_tab = NodeRoleTab(notebook, app)
        self.feature_tab = FeatureTab(notebook, app)
        self.hook_tab = HookTab(notebook, app)
        self.description_tab = DescriptionPackTab(notebook, app)
        self.profile_tab = GenerationProfileTab(notebook, app)

        notebook.add(self.terrain_tab, text="Terrains")
        notebook.add(self.climate_tab, text="Climates")
        notebook.add(self.biome_tab, text="Biomes")
        notebook.add(self.role_tab, text="Node Roles")
        notebook.add(self.feature_tab, text="Features")
        notebook.add(self.hook_tab, text="Hooks")
        notebook.add(self.description_tab, text="Description Packs")
        notebook.add(self.profile_tab, text="Generation Profiles")

    def refresh_all(self, reset_forms: bool):
        for tab in (
            self.terrain_tab,
            self.climate_tab,
            self.biome_tab,
            self.role_tab,
            self.feature_tab,
            self.hook_tab,
            self.description_tab,
            self.profile_tab,
        ):
            tab.refresh_list(reset_form=reset_forms)
