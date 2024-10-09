import json
import pickle
from faction_functions import Faction
from CharacterUtil import TitlePreference



class Player:
    intChoice: int # a value which should be set by player choice and then is used by the menu command system to make an action.

    def __init__(self, discord_id: int, nano: int = 0, chronos: int = 0, titlePreference: TitlePreference = TitlePreference.Masculine, characters=None, faction: Faction = None):
        self.discordID = discord_id  # Discord user ID
        self.playerName = "PlayerName" # will be filled in immediately after player creation/loading.
        self.nano = nano  # Placeholder for player's 'nano' currency or points
        self.chronos = chronos  # Placeholder for player's 'chronos' currency or points
        self.titlePreference = titlePreference # use the Enum TitlePreference.Masculine or TitlePreference.Feminine
        self.characters = characters if characters is not None else []  # List of character objects
        self.faction = faction
        self.achievementTitle = ""
        self.isNewPlayer = False
        self.partyNames = ["Delta Team", "2", "3", "4"] # It would be cool to be able to name parties. "Foxtrot" "Demons" "Delta Team"

        self.intChoice = 0

    def GetCharacterText(self):
        cString = ""
        for character in self.characters:
            cString = "**" + character.name + "** │ LvL " + str(character.level) + " │ (" + character.GetWoundedString() + ") │ Party: " + self.partyNames[character.party] + "\n"
        return cString

    def GetCharacterIndexByName(self, name: str):
        for i in range(len(self.characters)):
            if self.characters[i].name == name:
                return i
        return 0

    def GetCharacterName(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.characters[characterIndex].name
        else:
            return ""

    def GetCharacterLevel(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.characters[characterIndex].level
        else:
            return ""

    def GetCharacterParty(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.partyNames[self.characters[characterIndex].party]
        else:
            return ""

    # Returns the requested character index. If no such index exists, return the last character in the list.
    def GetCharacter(self, index: int):
        if len(self.characters) > index:
            return self.characters[index]
        else:
            return self.characters[len(self.characters)-1]

    def GetCharacterDetailsText(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.characters[characterIndex].GetCharacterOverviewText(self.nano)


def save_player(player: Player, filename: str):
    with open(filename, 'wb') as file:
        pickle.dump(player, file)

def load_player(filename: str) -> Player:
    with open(filename, 'rb') as file:
        return pickle.load(file)
