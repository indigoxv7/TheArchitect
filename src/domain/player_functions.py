import importlib
import json
import os
import time
from enum import Enum
from typing import Any, Dict, Optional

from src.domain.faction_functions import Faction
from src.domain.CharacterUtil import TitlePreference

LEGACY_MODULE_MAP = {
    "player_functions": "src.domain.player_functions",
    "menu_functions": "src.ui.menu_functions",
    "Character": "src.domain.Character",
    "CharacterUtil": "src.domain.CharacterUtil",
    "Items": "src.domain.Items",
    "Spells": "src.domain.Spells",
    "faction_functions": "src.domain.faction_functions",
    "GeneralSkills": "src.domain.GeneralSkills",
    "Globals": "src.config.Globals",
    "src.thearchitect.domain.player_functions": "src.domain.player_functions",
    "src.thearchitect.ui.menu_functions": "src.ui.menu_functions",
}


def _normalize_module_name(module_name: str) -> str:
    return LEGACY_MODULE_MAP.get(module_name, module_name)


def _load_module(module_name: str):
    return importlib.import_module(_normalize_module_name(module_name))


class Player:
    ENERGY_REGEN_RATE_PER_SECOND = 1.0 / 60.0
    _NON_PERSISTENT_FIELDS = {"_auto_save_enabled", "_save_path", "_is_initializing"}

    intChoice: int  # a value which should be set by player choice and then is used by the menu command system to make an action.

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
        energyRegenRatePerSecond: float = ENERGY_REGEN_RATE_PER_SECOND,
    ):
        object.__setattr__(self, "_auto_save_enabled", False)
        object.__setattr__(self, "_save_path", None)
        object.__setattr__(self, "_is_initializing", True)

        if energyLastCalculatedTime is None:
            energyLastCalculatedTime = time.time()

        self.discordID = discord_id  # Discord user ID
        self.playerName = "PlayerName"  # will be filled in immediately after player creation/loading.
        self.nano = nano  # Placeholder for player's 'nano' currency or points
        # Energy allows the player to perform actions.
        self.energy = float(energy)
        self.energyCap = energyCap  # Maximum amount of energy that the player can currently store.
        self.energyLastCalculatedTime = energyLastCalculatedTime  # used to calculate regenerated energy since last check.
        self.energyRegenRatePerSecond = energyRegenRatePerSecond
        self.titlePreference = titlePreference  # use Enum TitlePreference.Masculine or TitlePreference.Feminine
        self.characters = characters if characters is not None else []  # List of character objects
        self.faction = faction
        self.achievementTitle = ""
        self.isNewPlayer = False
        self.partyNames = ["Delta Team", "2", "3", "4"]
        self.inventory = inventory if inventory is not None else []

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

    # Returns the up-to-date integer energy amount and updates the stored energy/timestamp.
    def GetCurrentEnergy(self, currentTime: Optional[float] = None, persist: bool = True) -> int:
        if currentTime is None:
            currentTime = time.time()

        elapsed = max(0.0, currentTime - float(self.energyLastCalculatedTime))
        regenerated = elapsed * float(self.energyRegenRatePerSecond)
        newEnergy = min(float(self.energyCap), float(self.energy) + regenerated)

        # Avoid double-save while updating related fields together.
        object.__setattr__(self, "energy", newEnergy)
        object.__setattr__(self, "energyLastCalculatedTime", currentTime)

        if persist and getattr(self, "_auto_save_enabled", False):
            self.Save()

        return int(self.energy)

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

        object.__setattr__(self, "_is_initializing", False)
        object.__setattr__(self, "_auto_save_enabled", False)
        object.__setattr__(self, "_save_path", None)

    def GetCharacterText(self):
        cString = ""
        for character in self.characters:
            cString += "**" + character.name + "** | LvL " + str(character.level) + " | (" + character.GetWoundedString() + ") | Party: " + self.partyNames[character.party] + "\n"
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
            return self.partyNames[self.characters[characterIndex].party]
        return ""

    # Returns the requested character index. If no such index exists, return the last character in the list.
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


def save_player(player: Player, filename: str):
    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)

    payload: Dict[str, Any] = {
        "format_version": 1,
        "player_state": _serialize_value(player),
    }

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4, ensure_ascii=False)


def load_player(filename: str) -> Player:
    with open(filename, "r", encoding="utf-8-sig") as file:
        payload = json.load(file)

    playerData = payload.get("player_state", payload)
    player = _deserialize_value(playerData)
    if not isinstance(player, Player):
        raise TypeError("Loaded save did not produce a Player object.")

    player._ensure_runtime_defaults()
    player.AttachSavePath(filename, enableAutoSave=True)
    return player





