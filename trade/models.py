import random
from .constants import TileType, ResourceType

class Building:
    def __init__(self, b_type, tile, local_pos, settlement=None):
        self.type = b_type
        self.tile = tile
        self.local_pos = local_pos # (x, y) relative to tile origin, 0-1
        self.settlement = settlement
        if settlement:
            settlement.buildings.append(self)
        self.tile.buildings.append(self)

class Tile:
    def __init__(self, x, y, elevation, moisture, thresholds):
        self.x = x
        self.y = y
        self.elevation = elevation
        self.moisture = moisture
        self.resources = {res: 0.0 for res in ResourceType}
        self.potentials = {res: 0.0 for res in ResourceType}
        self.buildings = []
        self.thresholds = thresholds
        self.type = self._determine_type()
        self._init_potentials()
        
    def _init_potentials(self):
        if self.type == TileType.FOREST:
            self.potentials[ResourceType.WOOD] = 1.0
        elif self.type == TileType.GRASSLAND:
            self.potentials[ResourceType.GRAIN] = 1.0
            self.potentials[ResourceType.WOOD] = 0.2
        elif self.type == TileType.OCEAN or self.type == TileType.FRESH_WATER:
            self.potentials[ResourceType.FISH] = 1.0
        elif self.type == TileType.ROCKY:
            self.potentials[ResourceType.STONE] = 1.0
        elif self.type == TileType.TUNDRA:
            self.potentials[ResourceType.STONE] = 0.4
            
        # Metals
        if self.type == TileType.ROCKY:
            seed = (self.x * 1337 + self.y * 42) # TODO: configurable seed
            rng = random.Random(seed)
            if rng.random() < 0.4:
                self.potentials[ResourceType.IRON] = rng.uniform(0.5, 1.0)
            if rng.random() < 0.3:
                self.potentials[ResourceType.COAL] = rng.uniform(0.5, 1.0)
            if rng.random() < 0.2:
                self.potentials[ResourceType.COPPER] = rng.uniform(0.3, 0.8)
            if rng.random() < 0.2:
                self.potentials[ResourceType.TIN] = rng.uniform(0.3, 0.8)
            if rng.random() < 0.05:
                self.potentials[ResourceType.GOLD] = rng.uniform(0.1, 0.5)
            if rng.random() < 0.05:
                self.potentials[ResourceType.SILVER] = rng.uniform(0.1, 0.5)

    def _determine_type(self):
        t = self.thresholds
        if self.elevation < t["ocean"]:
            return TileType.OCEAN
        if self.elevation > t["rocky"]:
            return TileType.ROCKY
            
        if self.elevation > t["tundra_elevation"] and self.moisture < t["tundra_moisture"]:
            return TileType.TUNDRA
            
        if self.moisture < t["arid_moisture"]:
            return TileType.ARID
        if self.moisture < t["grassland_moisture"]:
            return TileType.GRASSLAND
        return TileType.FOREST

    @property
    def has_water(self):
        return self.type in [TileType.OCEAN, TileType.FRESH_WATER]

class Settlement:
    def __init__(self, name, tile):
        self.name = name
        self.tile = tile
        self.buildings = []

    @property
    def size(self):
        return len(self.buildings)
