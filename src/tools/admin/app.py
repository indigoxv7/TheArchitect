import tkinter as tk
from dataclasses import fields
from tkinter import ttk

from src.tools.admin.context import AdminServices
from src.tools.admin.features.achievements import AchievementBookFrame
from src.tools.admin.features.allegiances import AllegianceEditorFrame
from src.tools.admin.features.campaigns.frame import CampaignEditorFrame
from src.tools.admin.features.characters.frame import CharacterEditorFrame
from src.tools.admin.features.combat_simulator import CombatSimulatorFrame
from src.tools.admin.features.environment.frame import EnvironmentEditorFrame
from src.tools.admin.features.items import ItemEditorFrame
from src.tools.admin.features.main_character_memory import MainCharacterMemoryFrame
from src.tools.admin.features.missions.frame import MissionEditorFrame
from src.tools.admin.features.players import PlayerEditorFrame
from src.tools.admin.features.races import RaceEditorFrame
from src.tools.admin.features.spells import SpellEditorFrame
from src.tools.admin.features.units.frame import UnitEditorFrame
from src.tools.admin.features.variable_tuning import VariableTuningFrame
from src.tools.admin.shared.scrolling import ScrollableEditorHost


class AdminEditorApp:
    def __init__(
        self,
        spell_service,
        item_service,
        character_service,
        achievement_service,
        player_service,
        race_service,
        unit_service,
        allegiance_service,
        mission_service,
        campaign_service,
        environment_service,
        memory_service,
        power_rating_service,
        combat_simulator_service,
    ):
        self.services = AdminServices(
            spell_service=spell_service,
            item_service=item_service,
            character_service=character_service,
            achievement_service=achievement_service,
            player_service=player_service,
            race_service=race_service,
            unit_service=unit_service,
            allegiance_service=allegiance_service,
            mission_service=mission_service,
            campaign_service=campaign_service,
            environment_service=environment_service,
            memory_service=memory_service,
            power_rating_service=power_rating_service,
            combat_simulator_service=combat_simulator_service,
        )
        for field in fields(AdminServices):
            setattr(self, field.name, getattr(self.services, field.name))

        self.root = tk.Tk()
        self.root.title("TheArchitect Admin Editor")
        self.root.geometry("950x800")

        self.container = ttk.Frame(self.root, padding=12)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.home_frame = ttk.Frame(self.container)
        self.spell_frame = ScrollableEditorHost(self.container, SpellEditorFrame, self)
        self.item_frame = ScrollableEditorHost(self.container, ItemEditorFrame, self)
        self.character_frame = ScrollableEditorHost(self.container, CharacterEditorFrame, self)
        self.player_frame = ScrollableEditorHost(self.container, PlayerEditorFrame, self)
        self.achievement_frame = ScrollableEditorHost(self.container, AchievementBookFrame, self)
        self.race_frame = ScrollableEditorHost(self.container, RaceEditorFrame, self)
        self.unit_frame = ScrollableEditorHost(self.container, UnitEditorFrame, self)
        self.allegiance_frame = ScrollableEditorHost(self.container, AllegianceEditorFrame, self)
        self.mission_frame = ScrollableEditorHost(self.container, MissionEditorFrame, self)
        self.campaign_frame = ScrollableEditorHost(self.container, CampaignEditorFrame, self)
        self.environment_frame = ScrollableEditorHost(self.container, EnvironmentEditorFrame, self)
        self.variable_tuning_frame = ScrollableEditorHost(self.container, VariableTuningFrame, self)
        self.memory_frame = ScrollableEditorHost(self.container, MainCharacterMemoryFrame, self)
        self.combat_simulator_frame = ScrollableEditorHost(self.container, CombatSimulatorFrame, self)

        self._frames = [
            self.home_frame,
            self.spell_frame,
            self.item_frame,
            self.character_frame,
            self.player_frame,
            self.achievement_frame,
            self.race_frame,
            self.unit_frame,
            self.allegiance_frame,
            self.mission_frame,
            self.campaign_frame,
            self.environment_frame,
            self.variable_tuning_frame,
            self.memory_frame,
            self.combat_simulator_frame,
        ]

        self._build_home()
        self.show_home()

    def _build_home(self):
        ttk.Label(self.home_frame, text="Admin Editor Menu", font=("Segoe UI", 16, "bold")).pack(pady=20)
        buttons = [
            ("Edit Spells", self.show_spell_editor),
            ("Edit Items", self.show_item_editor),
            ("Edit Characters", self.show_character_editor),
            ("Edit Players", self.show_player_editor),
            ("Edit Achievements", self.show_achievement_editor),
            ("Edit Races", self.show_race_editor),
            ("Edit Units", self.show_unit_editor),
            ("Edit Allegiances", self.show_allegiance_editor),
            ("Edit Missions", self.show_mission_editor),
            ("Edit Campaigns", self.show_campaign_editor),
            ("Edit Environment", self.show_environment_editor),
            ("Variable Tuning", self.show_variable_tuning_editor),
            ("Main Character Memory", self.show_memory_editor),
            ("Combat Simulator", self.show_combat_simulator),
        ]
        for label, callback in buttons:
            ttk.Button(self.home_frame, text=label, command=callback).pack(fill=tk.X, pady=6)

    def _show(self, frame):
        for child in self._frames:
            child.pack_forget()
        frame.pack(fill=tk.BOTH, expand=True)
        if hasattr(frame, "scroll_to_top"):
            self.root.after_idle(frame.scroll_to_top)
        content = getattr(frame, "content", frame)
        if hasattr(content, "on_show"):
            content.on_show()

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

    def show_unit_editor(self):
        self.unit_frame.refresh_race_list(reset_selection=True)
        self._show(self.unit_frame)

    def show_allegiance_editor(self):
        self.allegiance_frame.refresh_allegiance_list(reset_form=True)
        self._show(self.allegiance_frame)

    def show_mission_editor(self):
        self.mission_frame.refresh_mission_list(reset_form=True)
        self._show(self.mission_frame)

    def show_campaign_editor(self):
        self.campaign_frame.refresh_campaign_list(reset_form=True)
        self._show(self.campaign_frame)

    def show_environment_editor(self):
        self.environment_frame.refresh_all(reset_forms=True)
        self._show(self.environment_frame)

    def show_variable_tuning_editor(self):
        self.variable_tuning_frame.reload_from_disk(show_message=False)
        self._show(self.variable_tuning_frame)

    def show_memory_editor(self):
        self.memory_frame.refresh_player_list(reset_form=True)
        self._show(self.memory_frame)

    def show_combat_simulator(self):
        self._show(self.combat_simulator_frame)

    def run(self):
        self.root.mainloop()
