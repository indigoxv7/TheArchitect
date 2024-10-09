from abc import ABC, abstractmethod
from Character import Character
from player_functions import Player
from CharacterUtil import Attribute

command_registry = {}

def register_command(name):
    def decorator(cls):
        command_registry[name] = cls()
        return cls
    return decorator

# Command Base Class
class Command(ABC):
    @abstractmethod
    def execute(self):
        pass

# GiveMoneyCommand accessing player's intChoice attribute
@register_command('GiveNano')
class GiveNano(Command):
    def __init__(self, player: Player):
        self.player = player

    def execute(self):
        amount = self.player.intChoice  # Access current value
        self.player.nano += amount

# GiveMoneyCommand accessing player's earnedReward attribute
@register_command('IncreaseCharacterAttribute')
class IncreaseCharacterAttribute(Command):
    def __init__(self, character: Character, attribute: Attribute):
        self.character = character
        self.attribute = attribute

    def execute(self):
        self.character.IncreaseAttribute(self.attribute)