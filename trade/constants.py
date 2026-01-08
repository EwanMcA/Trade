from enum import Enum, auto

class TileType(Enum):
    OCEAN = auto()
    FRESH_WATER = auto()
    ARID = auto()
    GRASSLAND = auto()
    FOREST = auto()
    TUNDRA = auto()
    ROCKY = auto()

class BuildingType(Enum):
    RESIDENTIAL_LOW = auto()
    RESIDENTIAL_HIGH = auto()
    LUMBER_YARD = auto()
    DOCK = auto()
    QUARRY = auto()
    MINE = auto()
    FARM = auto()

class ResourceType(Enum):
    WOOD = auto()
    GRAIN = auto()
    FISH = auto()
    STONE = auto()
    IRON = auto()
    COAL = auto()
    TIN = auto()
    COPPER = auto()
    GOLD = auto()
    SILVER = auto()
