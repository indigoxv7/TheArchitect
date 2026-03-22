import importlib
import json
import os
import tempfile
import time
from enum import Enum
from typing import Any, Dict, Optional

from src.domain.Campaign import CampaignProgress
from src.domain.faction_functions import Faction
from src.domain.character_util import TitlePreference

LEGACY_MODULE_MAP = {
    "player_functions": "src.domain.player_functions",
    "menu_functions": "src.ui.menu",
    "Character": "src.domain.Character",
    "CharacterUtil": "src.domain.character_util",
    "Items": "src.domain.items",
    "Spells": "src.domain.Spells",
    "faction_functions": "src.domain.faction_functions",
    "GeneralSkills": "src.domain.general_skills",
    "Globals": "src.config",
    "Campaign": "src.domain.Campaign",
    "Mission": "src.domain.mission",
    "combat": "src.domain.combat",
    "character_io": "src.domain.character_io",
    "main_character_generator": "src.services.character_generation",
    "src.thearchitect.domain.player_functions": "src.domain.player_functions",
    "src.thearchitect.ui.menu_functions": "src.ui.menu",
    "src.thearchitect.domain.Campaign": "src.domain.Campaign",
    "MainCharacter": "src.domain.main_character",
    "src.thearchitect.domain.MainCharacter": "src.domain.main_character",
    "src.thearchitect.domain.Character": "src.domain.Character",
    "src.thearchitect.domain.CharacterUtil": "src.domain.character_util",
    "src.thearchitect.domain.Items": "src.domain.items",
    "src.thearchitect.domain.Spells": "src.domain.Spells",
    "src.thearchitect.domain.GeneralSkills": "src.domain.general_skills",
    "src.thearchitect.domain.Mission": "src.domain.mission",
    "src.thearchitect.domain.combat": "src.domain.combat",
}


def _normalize_module_name(module_name: str) -> str:
    return LEGACY_MODULE_MAP.get(module_name, module_name)


def _load_module(module_name: str):
    return importlib.import_module(_normalize_module_name(module_name))


class Player:
    ENERGY_REGEN_RATE_PER_SECOND = 1.0 / 60.0
    _NON_PERSISTENT_FIELDS = {"_auto_save_enabled", "_save_path", "_is_initializing"}

    intChoice: int

    def __init__(
        self,
        discord_id: int,
        nano: int = 0,
        energy: float = 100,
        titlePreference: TitlePreference = TitlePreference.Masculine,
        characters=None,
        faction: Faction = None,
        energyCap: float = 100,
        energyLastCalculatedTime: Optional[float] = None,
        inventory=None,
        missionPartyCharacterIds=None,
        campaignProgressById=None,
        playerCharacter=None,
        energyRegenRatePerSecond: float = ENERGY_REGEN_RATE_PER_SECOND,
    ):
        object.__setattr__(self, "_auto_save_enabled", False)
        object.__setattr__(self, "_save_path", None)
        object.__setattr__(self, "_is_initializing", True)

        if energyLastCalculatedTime is None:
            energyLastCalculatedTime = time.time()

        self.discordID = discord_id
        self.playerName = "PlayerName"
        self.nano = nano
        self.energy = float(energy)
        self.energyCap = energyCap
        self.energyLastCalculatedTime = energyLastCalculatedTime
        self.energyRegenRatePerSecond = energyRegenRatePerSecond
        self.titlePreference = titlePreference
        self.characters = characters if characters is not None else []
        self.faction = faction
        self.achievementTitle = ""
        self.isNewPlayer = False
        self.partyNames = ["Delta Team", "2", "3", "4"]
        self.inventory = inventory if inventory is not None else []
        self.missionPartyCharacterIds = [
            str(entry or "").strip() for entry in (missionPartyCharacterIds or []) if str(entry or "").strip()
        ]
        self.campaignProgressById = self._normalize_campaign_progress_map(campaignProgressById)
        self.playerCharacter = playerCharacter

        self.intChoice = 0

        object.__setattr__(self, "_is_initializing", False)

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)

        if name in self._NON_PERSISTENT_FIELDS or name.startswith("_"):
            return
        if getattr(self, "_is_initializing", True):
            return
        if getattr(self, "_auto_save_enabled", False):
            self.Save()

    def AttachSavePath(self, savePath: str, enableAutoSave: bool = True):
        object.__setattr__(self, "_save_path", savePath)
        object.__setattr__(self, "_auto_save_enabled", enableAutoSave)

    def SetAutoSaveEnabled(self, enabled: bool):
        object.__setattr__(self, "_auto_save_enabled", enabled)

    def Save(self):
        if not self._save_path:
            return
        save_player(self, self._save_path)

    def GetCurrentEnergy(self, currentTime: Optional[float] = None, persist: bool = True) -> int:
        if currentTime is None:
            currentTime = time.time()

        elapsed = max(0.0, currentTime - float(self.energyLastCalculatedTime))
        regenerated = elapsed * float(self.energyRegenRatePerSecond)
        newEnergy = min(float(self.energyCap), float(self.energy) + regenerated)

        object.__setattr__(self, "energy", newEnergy)
        object.__setattr__(self, "energyLastCalculatedTime", currentTime)

        if persist and getattr(self, "_auto_save_enabled", False):
            self.Save()

        return int(self.energy)

    @staticmethod
    def _normalize_campaign_progress_map(value) -> dict[str, CampaignProgress]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, CampaignProgress] = {}
        for campaign_id, progress in value.items():
            key = str(campaign_id or "").strip()
            if not key:
                continue
            if isinstance(progress, CampaignProgress):
                progress.EnsureRuntimeDefaults()
                progress.campaignId = key
                normalized[key] = progress
                continue
            if isinstance(progress, dict):
                coerced = CampaignProgress.from_dict(progress)
                coerced.campaignId = key
                normalized[key] = coerced
        return normalized

    def _ensure_runtime_defaults(self):
        if not hasattr(self, "energy"):
            self.energy = 100.0
        if not hasattr(self, "energyCap"):
            self.energyCap = 100
        if not hasattr(self, "energyLastCalculatedTime"):
            self.energyLastCalculatedTime = time.time()
        if not hasattr(self, "energyRegenRatePerSecond"):
            self.energyRegenRatePerSecond = Player.ENERGY_REGEN_RATE_PER_SECOND
        if not hasattr(self, "inventory"):
            self.inventory = []
        if not hasattr(self, "characters") or self.characters is None:
            self.characters = []
        if not hasattr(self, "missionPartyCharacterIds") or self.missionPartyCharacterIds is None:
            self.missionPartyCharacterIds = []
        elif not isinstance(self.missionPartyCharacterIds, list):
            self.missionPartyCharacterIds = [str(self.missionPartyCharacterIds)]
        else:
            self.missionPartyCharacterIds = [
                str(entry or "").strip() for entry in self.missionPartyCharacterIds if str(entry or "").strip()
            ]
        if not hasattr(self, "campaignProgressById") or self.campaignProgressById is None:
            self.campaignProgressById = {}
        self.campaignProgressById = self._normalize_campaign_progress_map(self.campaignProgressById)
        if not hasattr(self, "playerCharacter"):
            self.playerCharacter = None
        ensure_player_character_defaults = getattr(self.playerCharacter, "EnsureRuntimeDefaults", None)
        if callable(ensure_player_character_defaults):
            ensure_player_character_defaults()

        for character in self.characters:
            ensure_defaults = getattr(character, "EnsureRuntimeDefaults", None)
            if callable(ensure_defaults):
                ensure_defaults()

        object.__setattr__(self, "_is_initializing", False)
        object.__setattr__(self, "_auto_save_enabled", False)
        object.__setattr__(self, "_save_path", None)

    def _character_identity(self, character) -> str:
        return str(getattr(character, "playerInstanceId", "") or getattr(character, "name", "") or "")

    def IsCharacterInMissionParty(self, character) -> bool:
        return self._character_identity(character) in set(self.GetMissionPartyCharacterIds())

    def GetMissionPartyCharacterIds(self) -> list[str]:
        valid_ids = {
            self._character_identity(character) for character in self.characters if self._character_identity(character)
        }
        selected = [entry for entry in self.missionPartyCharacterIds if entry in valid_ids]
        if selected:
            return selected
        return [
            self._character_identity(character) for character in self.characters if self._character_identity(character)
        ]

    def SetMissionPartyCharacterIds(self, character_ids) -> list[str]:
        requested = [str(entry or "").strip() for entry in (character_ids or []) if str(entry or "").strip()]
        valid_ids = {
            self._character_identity(character) for character in self.characters if self._character_identity(character)
        }
        self.missionPartyCharacterIds = [entry for entry in requested if entry in valid_ids]
        return self.GetMissionPartyCharacterIds()

    def GetMissionPartyCharacters(self):
        selected_ids = set(self.GetMissionPartyCharacterIds())
        return [character for character in self.characters if self._character_identity(character) in selected_ids]

    def GetCampaignProgress(self, campaignId: str) -> CampaignProgress | None:
        key = str(campaignId or "").strip()
        if not key:
            return None
        return self.campaignProgressById.get(key)

    def GetCharacterText(self):
        cString = ""
        selected_ids = set(self.GetMissionPartyCharacterIds())
        for character in self.characters:
            line = (
                "**" + character.name + "** | LvL " + str(character.level) + " | (" + character.GetWoundedString() + ")"
            )
            if self._character_identity(character) in selected_ids:
                line += " | Selected for Mission"
            cString += line + "\n"
        return cString

    def GetCharacterIndexByName(self, name: str):
        for i in range(len(self.characters)):
            if self.characters[i].name == name:
                return i
        return 0

    def GetCharacterName(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.characters[characterIndex].name
        return ""

    def GetCharacterLevel(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.characters[characterIndex].level
        return ""

    def GetCharacterParty(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return (
                "Selected for Mission" if self.IsCharacterInMissionParty(self.characters[characterIndex]) else "Reserve"
            )
        return ""

    def GetCharacter(self, index: int):
        if len(self.characters) > index:
            return self.characters[index]
        return self.characters[len(self.characters) - 1]

    def GetCharacterDetailsText(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.characters[characterIndex].GetCharacterOverviewText(self.nano)
        return ""


def _import_class(classPath: str):
    moduleName, className = classPath.rsplit(".", 1)
    module = _load_module(moduleName)
    return getattr(module, className)


def _serialize_value(value: Any):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return {"__enum__": f"{value.__class__.__module__}.{value.__class__.__name__}.{value.name}"}
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, tuple):
        return {"__tuple__": [_serialize_value(v) for v in value]}
    if isinstance(value, set):
        return {"__set__": [_serialize_value(v) for v in value]}
    if isinstance(value, dict):
        return {str(k): _serialize_value(v) for k, v in value.items()}
    if hasattr(value, "__dict__"):
        state = {}
        for key, item in value.__dict__.items():
            if isinstance(value, Player) and key in Player._NON_PERSISTENT_FIELDS:
                continue
            state[key] = _serialize_value(item)
        return {
            "__class__": f"{value.__class__.__module__}.{value.__class__.__name__}",
            "__state__": state,
        }
    raise TypeError(f"Unsupported value type for serialization: {type(value)}")


def _deserialize_value(value: Any):
    if isinstance(value, list):
        return [_deserialize_value(v) for v in value]
    if isinstance(value, dict):
        if "__enum__" in value:
            enumPath = value["__enum__"]
            moduleName, className, memberName = enumPath.rsplit(".", 2)
            enumClass = getattr(_load_module(moduleName), className)
            return enumClass[memberName]
        if "__tuple__" in value:
            return tuple(_deserialize_value(v) for v in value["__tuple__"])
        if "__set__" in value:
            return set(_deserialize_value(v) for v in value["__set__"])
        if "__class__" in value and "__state__" in value:
            cls = _import_class(value["__class__"])
            obj = cls.__new__(cls)
            state = _deserialize_value(value["__state__"])
            for key, item in state.items():
                object.__setattr__(obj, key, item)
            return obj
        return {k: _deserialize_value(v) for k, v in value.items()}
    return value


def _write_json_atomic(payload: Dict[str, Any], filename: str):
    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)

    temp_fd = None
    temp_path = None
    try:
        temp_fd, temp_path = tempfile.mkstemp(dir=directory or None, prefix=".player_", suffix=".json.tmp")
        with os.fdopen(temp_fd, "w", encoding="utf-8") as file:
            temp_fd = None
            json.dump(payload, file, indent=4, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, filename)
    finally:
        if temp_fd is not None:
            os.close(temp_fd)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def save_player(player: Player, filename: str):
    payload: Dict[str, Any] = {
        "format_version": 1,
        "player_state": _serialize_value(player),
    }
    _write_json_atomic(payload, filename)


def load_player(filename: str) -> Player:
    with open(filename, "r", encoding="utf-8-sig") as file:
        raw_payload = file.read()

    if not raw_payload.strip():
        raise ValueError(f"Player save '{filename}' is empty.")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Player save '{filename}' contains invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise TypeError(f"Player save '{filename}' did not contain a JSON object.")

    playerData = payload.get("player_state", payload)
    player = _deserialize_value(playerData)
    if not isinstance(player, Player):
        raise TypeError("Loaded save did not produce a Player object.")

    player._ensure_runtime_defaults()
    player.AttachSavePath(filename, enableAutoSave=True)
    return player


