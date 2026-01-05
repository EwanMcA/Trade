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
    RESIDENTIAL_LOW = auto()
    RESIDENTIAL_HIGH = auto()
    LUMBER_YARD = auto()
    DOCK = auto()
    QUARRY = auto()
    MINE = auto()
    FARM = auto()

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
        self._spawn_new_settlements()

    def _get_nearest_settlement(self, x, y):
        best_s = None
        min_dist_sq = float('inf')
        for s in self.world_map.settlements:
            ds = (s.tile.x - x)**2 + (s.tile.y - y)**2
            if ds < min_dist_sq:
                min_dist_sq = ds
                best_s = s
        return best_s, (min_dist_sq**0.5 if best_s else float('inf'))

    def _is_water_edge(self, tile):
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
                nb = self.world_map.get_tile(tile.x + dx, tile.y + dy)
                if nb and nb.has_water:
                    return True
        return False

    def _rand_pos(self):
        return (random.random(), random.random())

    def _simulate_growth(self):
        # TODO: Have an initial state and then much less growth
        
        sim_cfg = self.config["simulation"]
        base_growth = sim_cfg.get("growth_chance", 0.0001)
        
        # TODO: optimization - probably don't need to loop the whole map
        for (x, y), tile in self.world_map.tiles.items():
            if tile.has_water or tile.buildings:
                continue

            if self._try_place_resource_building(tile):
                continue
                
            nearest_s, dist = self._get_nearest_settlement(x, y)
            
            if nearest_s:
                # Growth rules based on distance to settlement
                if dist < 3.0:
                    # High density residential core
                    if random.random() < 0.05:
                        Building(BuildingType.RESIDENTIAL_HIGH, tile, self._rand_pos(), nearest_s)
                        continue
                elif dist < 8.0:
                    # Low density residential outskirts
                    if random.random() < 0.02:
                        Building(BuildingType.RESIDENTIAL_LOW, tile, self._rand_pos(), nearest_s)
                        continue
                
            else:
                # Spontaneous growth to start new clusters
                if random.random() < base_growth:
                    Building(BuildingType.RESIDENTIAL_LOW, tile, self._rand_pos(), None)

    def _try_place_resource_building(self, tile):
        # don't place if there are other buildings within 9 tiles
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                nb = self.world_map.get_tile(tile.x + dx, tile.y + dy)
                if nb and nb.buildings:
                    return False

        # Lumber Yards on Forest
        if tile.type == TileType.FOREST:
            if random.random() < 0.0005:
                Building(BuildingType.LUMBER_YARD, tile, self._rand_pos())
                return True
        
        # Farms on non-arid Grassland
        if tile.type == TileType.GRASSLAND:
            if random.random() < 0.0005:
                Building(BuildingType.FARM, tile, self._rand_pos())
                return True
        
        # Docks on water edge
        if self._is_water_edge(tile):
            if random.random() < 0.0003:
                Building(BuildingType.DOCK, tile, self._rand_pos())
                return True
        
        # Mines and Quarries on metal/stone potential
        if tile.type == TileType.ROCKY or tile.type == TileType.TUNDRA:
            metals = [ResourceType.IRON, ResourceType.COAL, ResourceType.COPPER, 
                      ResourceType.TIN, ResourceType.GOLD, ResourceType.SILVER]
            has_metals = any(tile.potentials.get(m, 0) > 0 for m in metals)
            
            if has_metals or tile.type == TileType.ROCKY:
                if random.random() < 0.0004:
                    Building(BuildingType.MINE, tile, self._rand_pos())
                    return True
            
            if tile.potentials.get(ResourceType.STONE, 0) > 0.4:
                if random.random() < 0.0004:
                    Building(BuildingType.QUARRY, tile, self._rand_pos())
                    return True
        
        return False

    def _spawn_new_settlements(self):
        sim_cfg = self.config["simulation"]
        if random.random() < sim_cfg["settlement_spawn_chance"]:
            potential_tiles = []
            for (x, y), tile in self.world_map.tiles.items():
                if tile.buildings:
                    continue
                nearest_s, dist = self._get_nearest_settlement(x, y)
                if nearest_s is None or dist > sim_cfg["settlement_min_distance"]:
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
        self.action_queue = [] # List of (function, args, kwargs)
        
    def add_action(self, func, *args, **kwargs):
        """Add an action to be processed next turn."""
        self.action_queue.append((func, args, kwargs))

    def next_turn(self):
        self.turn_count += 1
        print(f"--- Turn {self.turn_count} ---")

        self.simulation.simulate_turn()

        # count building types
        btypes = {}
        for tile in self.simulation.world_map.tiles.values():
            for b in tile.buildings:
                btypes[b.type] = btypes.get(b.type, 0) + 1
        print("Building counts:", {bt.name: count for bt, count in btypes.items()})
        
        while self.action_queue:
            func, args, kwargs = self.action_queue.pop(0)
            func(*args, **kwargs)
