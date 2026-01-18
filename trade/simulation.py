import random
from .constants import TileType, BuildingType, ResourceType
from .models import Building, Settlement

class WorldSimulation:
    def __init__(self, world_map, config):
        self.world_map = world_map
        self.config = config
        self._simulate_growth(0.5)

    def simulate_turn(self):
        base_growth = self.config["simulation"].get("growth_chance", 0.0001)
        self._simulate_growth(base_growth)
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

    def _simulate_growth(self, growth_modifier):
        # TODO: optimization - probably don't need to loop the whole map
        for (x, y), tile in self.world_map.tiles.items():
            if tile.has_water or tile.buildings:
                continue
            if random.random() > growth_modifier:
                continue

            if self._try_place_resource_building(tile):
                continue
                
            nearest_s, dist = self._get_nearest_settlement(x, y)
            
            if nearest_s:
                # Growth rules based on distance to settlement
                if dist < 5.0:
                    # High density residential core
                    if random.random() < 0.1:
                        Building(BuildingType.RESIDENTIAL_HIGH, tile, self._rand_pos(), nearest_s)
                        continue
                elif dist < 10.0:
                    # Low density residential outskirts
                    if random.random() < 0.1:
                        Building(BuildingType.RESIDENTIAL_LOW, tile, self._rand_pos(), nearest_s)
                        continue

    def _try_place_resource_building(self, tile):
        # don't place if there are other buildings within 9 tiles
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                nb = self.world_map.get_tile(tile.x + dx, tile.y + dy)
                if nb and nb.buildings:
                    return False

        # Lumber Yards on Forest
        if tile.type == TileType.FOREST:
            if random.random() < 0.001:
                Building(BuildingType.LUMBER_YARD, tile, self._rand_pos())
                return True
        
        # Farms on non-arid Grassland
        if tile.type == TileType.GRASSLAND:
            if random.random() < 0.001:
                Building(BuildingType.FARM, tile, self._rand_pos())
                return True
        
        # Docks on water edge
        if self._is_water_edge(tile):
            if random.random() < 0.003:
                Building(BuildingType.DOCK, tile, self._rand_pos())
                return True
        
        # Mines and Quarries on metal/stone potential
        if tile.type == TileType.ROCKY or tile.type == TileType.TUNDRA:
            metals = [ResourceType.IRON, ResourceType.COAL, ResourceType.COPPER, 
                      ResourceType.TIN, ResourceType.GOLD, ResourceType.SILVER]
            has_metals = any(tile.potentials.get(m, 0) > 0 for m in metals)
            
            if has_metals or tile.type == TileType.ROCKY:
                if random.random() < 0.04:
                    Building(BuildingType.MINE, tile, self._rand_pos())
                    return True
            
            if tile.potentials.get(ResourceType.STONE, 0) > 0.4:
                if random.random() < 0.04:
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
