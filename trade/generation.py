import random
from panda3d.core import PerlinNoise2
from game_world import Tile, TileType, WorldMap

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
                
                bias_strength = gen_cfg.get("ocean_bias_strength", 0.0)
                bias_direction = gen_cfg.get("ocean_bias_direction", "west").lower()
                
                bias_factor = 0.0
                if bias_direction == "west":
                    bias_factor = (1.0 - (x / self.size)) ** 4
                elif bias_direction == "east":
                    bias_factor = (x / self.size) ** 4
                elif bias_direction == "south":
                    bias_factor = (1.0 - (y / self.size)) ** 4
                elif bias_direction == "north":
                    bias_factor = (y / self.size) ** 4
                    
                e -= bias_strength * bias_factor
                
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
