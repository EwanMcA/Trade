import random
from enum import Enum, auto


class TileType(Enum):
    OCEAN = auto()
    FRESH_WATER = auto()
    ARID = auto()
    GRASSLAND = auto()
    FOREST = auto()
    TUNDRA = auto()
    ROCKY = auto()

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

class Tile:
    def __init__(self, x, y, elevation, moisture, thresholds):
        self.x = x
        self.y = y
        self.elevation = elevation
        self.moisture = moisture
        self.resources = {res: 0.0 for res in ResourceType}
        self.potentials = {res: 0.0 for res in ResourceType}
        self.settlement = None
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
        self.size = 1 # Population
        self.tile.settlement = self

class WorldMap:
    def __init__(self, size=40):
        self.size = size
        self.tiles = {}
        self.settlements = []

    def get_tile(self, x, y):
        return self.tiles.get((x, y))

class WorldSimulation:
    def __init__(self, world_map, config):
        self.world_map = world_map
        self.config = config

    def simulate_turn(self):
        self._simulate_growth()
        self._spawn_new_settlements()

    def _simulate_growth(self):
        sim_cfg = self.config["simulation"]
        for s in self.world_map.settlements:
            near_water = False
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    neighbor = self.world_map.get_tile(s.tile.x + dx, s.tile.y + dy)
                    if neighbor and neighbor.has_water:
                        near_water = True
                        break
            
            if near_water and random.random() < sim_cfg["growth_chance"]:
                s.size += 1
                print(f"Settlement at {s.tile.x}, {s.tile.y} grew to size {s.size}")

    def _spawn_new_settlements(self):
        sim_cfg = self.config["simulation"]
        if random.random() < sim_cfg["spawn_chance"]:
            potential_tiles = []
            for (x, y), tile in self.world_map.tiles.items():
                if not tile.settlement and not tile.has_water:
                    has_nearby_water = False
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            neighbor = self.world_map.get_tile(x + dx, y + dy)
                            if neighbor and neighbor.has_water:
                                has_nearby_water = True
                                break
                    if has_nearby_water:
                        potential_tiles.append(tile)
            
            if potential_tiles:
                target = random.choice(potential_tiles)
                new_s = Settlement(f"City {len(self.world_map.settlements)}", target)
                self.world_map.settlements.append(new_s)
                print(f"New settlement founded at {target.x}, {target.y}")

class TurnManager:
    def __init__(self, simulation):
        self.simulation = simulation
        self.turn_count = 0
        
    def next_turn(self):
        self.turn_count += 1
        print(f"--- Turn {self.turn_count} ---")
        self.simulation.simulate_turn()
