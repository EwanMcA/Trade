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

class BuildingType(Enum):
    RESIDENTIAL = auto()

class Building:
    def __init__(self, b_type, tile, local_pos, settlement=None):
        self.type = b_type
        self.tile = tile
        self.local_pos = local_pos # (x, y) relative to tile origin, 0-1
        self.settlement = settlement
        if settlement:
            settlement.buildings.append(self)
        self.tile.buildings.append(self)

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
        # self._spawn_new_settlements()

    def _simulate_growth(self):
        sim_cfg = self.config["simulation"]
        base_growth = sim_cfg.get("growth_chance")
        water_bonus = sim_cfg.get("water_growth_bonus")
        cluster_bonus = sim_cfg.get("cluster_bonus")
        
        for (x, y), tile in self.world_map.tiles.items():
            if tile.has_water:
                continue
                
            chance = base_growth
            
            # Water bonus
            has_nearby_water = False
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nb = self.world_map.get_tile(x + dx, y + dy)
                    if nb and nb.has_water:
                        has_nearby_water = True
                        break
                if has_nearby_water: break
            
            if has_nearby_water:
                chance += water_bonus
                
            # Clustering bonus
            nearby_buildings = 0
            for dx in [-6, 0, 6]:
                for dy in [-6, 0, 6]:
                    nb = self.world_map.get_tile(x + dx, y + dy)
                    if nb:
                        nearby_buildings += len(nb.buildings)
            
            chance += nearby_buildings * cluster_bonus
            
            if random.random() < chance:
                # Find nearby settlement to join
                closest_s = None
                min_dist = 3.0 # Maximum distance to join a settlement
                for s in self.world_map.settlements:
                    dist = ((s.tile.x - x)**2 + (s.tile.y - y)**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        closest_s = s
                
                lx, ly = random.random(), random.random()
                Building(BuildingType.RESIDENTIAL, tile, (lx, ly), settlement=closest_s)

    def _spawn_new_settlements(self):
        sim_cfg = self.config["simulation"]
        # A settlement might spawn if there are "lonely" buildings clustering
        if random.random() < sim_cfg["settlement_spawn_chance"]:
            potential_tiles = []
            for (x, y), tile in self.world_map.tiles.items():
                # Only spawn if there are buildings but no nearby settlement
                if tile.buildings and not tile.has_water:
                    has_nearby_settlement = False
                    for s in self.world_map.settlements:
                        dist = ((s.tile.x - x)**2 + (s.tile.y - y)**2)**0.5
                        if dist < 5.0:
                            has_nearby_settlement = True
                            break
                    if not has_nearby_settlement:
                        potential_tiles.append(tile)
            
            if potential_tiles:
                target = random.choice(potential_tiles)
                new_s = Settlement(f"City {len(self.world_map.settlements)}", target)
                # Assign nearby lonely buildings to this new settlement
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        nb = self.world_map.get_tile(target.x + dx, target.y + dy)
                        if nb:
                            for b in nb.buildings:
                                if b.settlement is None:
                                    b.settlement = new_s
                                    new_s.buildings.append(b)
                                    
                self.world_map.settlements.append(new_s)
                print(f"New settlement founded at {target.x}, {target.y}")

class TurnManager:
    def __init__(self, simulation):
        self.simulation = simulation
        self.turn_count = 0
        self.action_queue = [] # List of (function, args, kwargs)
        
    def add_action(self, func, *args, **kwargs):
        """Add an action to be processed next turn."""
        self.action_queue.append((func, args, kwargs))

    def next_turn(self):
        self.turn_count += 1
        print(f"--- Turn {self.turn_count} ---")
        
        self.simulation.simulate_turn()
        
        while self.action_queue:
            func, args, kwargs = self.action_queue.pop(0)
            func(*args, **kwargs)
