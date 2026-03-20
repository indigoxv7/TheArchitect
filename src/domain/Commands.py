from abc import ABC, abstractmethod

from src.domain.Character import Character
from src.domain.character_util import Attribute
from src.domain.player_functions import Player

command_registry = {}


def register_command(name):
    def decorator(cls):
        command_registry[name] = cls()
        return cls

    return decorator


class Command(ABC):
    @abstractmethod
    def execute(self):
        pass


@register_command("GiveNano")
class GiveNano(Command):
    def __init__(self, player: Player):
        self.player = player

    def execute(self):
        amount = self.player.intChoice
        self.player.nano += amount


@register_command("IncreaseCharacterAttribute")
class IncreaseCharacterAttribute(Command):
    def __init__(self, character: Character, attribute: Attribute):
        self.character = character
        self.attribute = attribute

    def execute(self):
        self.character.IncreaseAttribute(self.attribute)
