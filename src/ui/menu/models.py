from enum import Enum


class MenuState(Enum):
    DEFAULT = 0
    NEW_PLAYER = 1
    MAIN = 2
    CHARACTER = 3


class MenuContext:
    def __init__(self):
        self.menuState = MenuState.MAIN
        self.character = None
        self.spellDraft = {}
        self.spellDraftActive = False
        self.spellDraftSourceName = None
        self.itemDraft = {}
        self.itemDraftActive = False
        self.itemDraftSourceName = None
        self.itemDraftSourceId = None
        self.attributesDraft = {}
        self.attributesDraftActive = False
        self.gearDraft = {}
        self.gearDraftActive = False
        self.bonusDraft = {}
        self.bonusDraftActive = False
        self.achievementDraft = {}
        self.achievementDraftActive = False


class ContextButton:
    def __init__(self, name: str, count: int, target: "Menu" = None, warningText: str = ""):
        self.name = name
        self.count = count
        self.target = target
        self.warningText = warningText


class Menu:
    def __init__(
        self,
        myOptionText,
        bodyText,
        uniqueName,
        parent=None,
        myEmoji=None,
        imageURL=None,
        menuState: MenuState = MenuState.DEFAULT,
        contextButtons: list[ContextButton] = None,
        developerOnly: bool = False,
    ):
        self.myOptionText = myOptionText
        self.myEmoji = myEmoji
        self.uniqueName = uniqueName
        self.bodyText = bodyText
        self.parent = parent
        self.Options = []
        self.imageURL = imageURL
        self.menuState = menuState
        self.contextButtons = contextButtons
        self.developerOnly = developerOnly

    def add_option(self, menu):
        menu.parent = self
        self.Options.append(menu)
