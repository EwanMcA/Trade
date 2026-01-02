import random
from enum import Enum, auto
from panda3d.core import PerlinNoise2


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

class WorldGenerator:
    def __init__(self, size, config):
        self.size = size
        self.config = config

    def generate(self):
        world_map = WorldMap(self.size)
        gen_cfg = self.config["generation"]
        seed = gen_cfg["seed"]
        if seed == -1:
            seed = random.randint(0, 10000)
            
        octaves = gen_cfg.get("noise_octaves", 8)
        freq = gen_cfg.get("noise_frequency", 8)
        table_size = gen_cfg.get("noise_table_size", 256)
            
        elev_noise = PerlinNoise2(octaves, freq, table_size, seed)
        moist_noise = PerlinNoise2(octaves, freq, table_size, seed + 1)
        
        thresholds = self.config["thresholds"]
        
        for x in range(self.size):
            for y in range(self.size):
                # Elevation generation
                blend = gen_cfg["elevation_blend"]
                e = (elev_noise.noise(x * gen_cfg["elevation_scale_1"], y * gen_cfg["elevation_scale_1"]) * blend + 
                     elev_noise.noise(x * gen_cfg["elevation_scale_2"], y * gen_cfg["elevation_scale_2"]) * (1.0 - blend))
                e = (e + 1.0) / 2.0
                e = (e - gen_cfg["norm_offset"]) / gen_cfg["norm_range"]
                e = max(0, min(1, e))
                
                # Moisture generation
                m = (moist_noise.noise(x * gen_cfg["moisture_scale"], y * gen_cfg["moisture_scale"]) + 1.0) / 2.0
                m = (m - gen_cfg["norm_offset"]) / gen_cfg["norm_range"]
                m = max(0, min(1, m))
                
                world_map.tiles[(x, y)] = Tile(x, y, e, m, thresholds)

        self._generate_rivers(world_map)
        return world_map
            
    def _generate_rivers(self, world_map):
        sim_cfg = self.config["simulation"]
        gen_cfg = self.config["generation"]
        sources = [t for t in world_map.tiles.values() if t.elevation > sim_cfg["river_source_min_elevation"] and t.type == TileType.ROCKY]
        
        min_ratio = gen_cfg.get("river_count_min_ratio", 0.1)
        max_ratio = gen_cfg.get("river_count_max_ratio", 0.2)
        num_rivers = random.randint(int(self.size * min_ratio), int(self.size * max_ratio))
        
        if not sources:
            return

        for _ in range(min(num_rivers, len(sources))):
            current = random.choice(sources)
            sources.remove(current)
            
            path = []
            visited = set()
            
            while current and current.type != TileType.OCEAN:
                path.append(current)
                visited.add((current.x, current.y))
                
                neighbors = []
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0: continue
                        nx, ny = current.x + dx, current.y + dy
                        neighbor = world_map.tiles.get((nx, ny))
                        if neighbor and (nx, ny) not in visited:
                            neighbors.append(neighbor)
                
                if not neighbors:
                    break
                    
                neighbors.sort(key=lambda t: t.elevation)
                next_tile = neighbors[0]
                
                if next_tile.elevation >= current.elevation:
                    if random.random() > sim_cfg["river_stop_chance"]:
                        break
                
                current = next_tile
                
            for tile in path:
                if tile.type != TileType.OCEAN:
                    tile.type = TileType.FRESH_WATER

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
