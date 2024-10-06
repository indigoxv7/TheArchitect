from enum import auto, Enum

class BuildingType(Enum):
    FACTION_HALL = 0
    WAREHOUSE = 1
    SMITHY = 2
    QUARRY = 3
    WELL = 4
    BUNKHOUSES = 5
    FARM = 6
    ALCHEMIST_WORKSHOP = 7

class FactionRole(Enum):
    CHANCELLOR = 0
    CONSTRUCTOR = 1
    BLACKSMITH = 2
    CHEF = 3
    ALCHEMIST = 4
    FARMER = 5

class MissionPolicy(Enum):
    SAFE = 0
    AGGRESSIVE = 1
    BALANCED = 2

class MasculineTitles(Enum):
    Lord = 0
    Duke = 1
    Marquess = 2
    Count = 3
    Viscount = 4
    Baron = 5
    Alderman = 6

class FeminineTitles(Enum):
    Lady = 0
    Duchess = 1
    Marchioness = 2
    Countess = 3
    Viscountess = 4
    Baroness = 5
    Alderwoman = 6




class Faction:
    def __init__(self, name: str, player):
        self.name = name
        self.factionFounded = False # players have to found their faction before they can use it.
        self.player = player
        self.title = ""
        self.score = 0
        self.members = []
        self.buildings = {}
        self.resources = {
            "stone": 0,
            "water": 0,
            "food": 0,
            # Add other resources as needed
        }
        self.population_capacity = 0
        self.current_population = 0
        self.mission_policy = MissionPolicy.BALANCED

    def add_building(self, building_type: BuildingType, level: int = 1):
        if building_type in self.buildings:
            raise ValueError(f"{building_type.name} already exists in the faction.")
        building = Building(building_type, level)
        self.buildings[building_type] = building
        self.update_population_capacity()

    def upgrade_building(self, building_type: BuildingType):
        if building_type not in self.buildings:
            raise ValueError(f"{building_type.name} does not exist in the faction.")
        self.buildings[building_type].upgrade()
        self.update_population_capacity()

    def update_population_capacity(self):
        faction_hall = self.buildings.get(BuildingType.FACTION_HALL)
        if faction_hall:
            self.population_capacity = faction_hall.get_population_capacity()

    def add_member(self, member):
        if self.current_population >= self.population_capacity:
            raise ValueError("Faction is at full capacity.")
        self.members.append(member)
        self.current_population += 1

    def assign_role(self, member, role: FactionRole):
        if role not in FactionRole:
            raise ValueError(f"{role.name} is not a valid role.")
        member.role = role




class Building:
    def __init__(self, building_type: BuildingType, level: int = 1):
        self.building_type = building_type
        self.level = level
        self.prerequisites = self.get_prerequisites()
        self.capacity = self.get_capacity()

    def upgrade(self):
        self.level += 1
        self.prerequisites = self.get_prerequisites()
        self.capacity = self.get_capacity()

    def get_prerequisites(self):
        prerequisites = {}
        if self.building_type == BuildingType.BUNKHOUSES:
            prerequisites = {BuildingType.WELL: 1}
        # Add more prerequisites logic based on building type and level
        return prerequisites

    def get_capacity(self):
        if self.building_type == BuildingType.FACTION_HALL:
            if self.level == 1:
                return 100
            elif self.level == 2:
                return 500
            elif self.level == 3:
                return 1000
            elif self.level == 4:
                return 10000
        # Add more capacity logic based on building type and level
        return 0

    def get_population_capacity(self):
        if self.building_type == BuildingType.FACTION_HALL:
            return self.capacity
        return 0


class Member:
    def __init__(self, name: str, role: FactionRole = None):
        self.name = name
        self.role = role
        self.is_combat_class = False

    def assign_role(self, role: FactionRole):
        self.role = role
