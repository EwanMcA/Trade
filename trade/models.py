import random
import math
from typing import List, Dict, Tuple, Optional, Any
from .constants import TileType, ResourceType, BuildingType

class Building:
    def __init__(self, b_type: BuildingType, tile: 'Tile', local_pos: Tuple[float, float], settlement: Optional['Settlement'] = None):
        self.type = b_type
        self.tile = tile
        self.local_pos = local_pos # (x, y) relative to tile origin, 0-1
        self.settlement = settlement
        self.inventory: Dict[ResourceType, int] = {res: 0 for res in ResourceType}
        self._resource_buffers: Dict[ResourceType, float] = {res: 0.0 for res in ResourceType}
        self.primary_resource: Optional[ResourceType] = None

        if self.type == BuildingType.MINE:
            self._select_primary_resource()

        if settlement:
            settlement.buildings.append(self)
        self.tile.buildings.append(self)

    def add_resource(self, res: ResourceType, amount: float) -> None:
        """Adds (or removes) a fractional amount of a resource, updating the integer inventory using floor."""
        self._resource_buffers[res] += amount

        # Clamp total amount to zero to prevent negative inventory
        if self.inventory[res] + self._resource_buffers[res] < 0:
            self.inventory[res] = 0
            self._resource_buffers[res] = 0.0
            return

        # floor() ensures we only count "full barrels/crates"
        change = math.floor(self._resource_buffers[res])
        if change != 0:
            self.inventory[res] += change
            self._resource_buffers[res] -= change

    def get_production_rates(self, config: Dict[str, Any]) -> Dict[ResourceType, float]:
        """Calculates effective production rates based on building type and tile potentials."""
        prod_cfg = config.get("production", {})
        rates = {}
        
        b_name = self.type.name
        if b_name not in prod_cfg:
            return {}
            
        cfg_rates = prod_cfg[b_name]
        
        if self.type == BuildingType.MINE:
            if self.primary_resource:
                rate = cfg_rates.get(self.primary_resource.name, 0.0)
                rates[self.primary_resource] = rate
        elif self.type == BuildingType.QUARRY:
            for r_name, rate in cfg_rates.items():
                res = ResourceType[r_name]
                if res == ResourceType.STONE:
                    rates[res] = rate
                else:
                    # Secondary resources based on potential
                    potential = self.tile.potentials.get(res, 0.0)
                    if potential > 0:
                        rates[res] = rate * potential
        else:
            for r_name, rate in cfg_rates.items():
                rates[ResourceType[r_name]] = rate
                
        return rates

    def get_consumption_rates(self, config: Dict[str, Any]) -> Dict[ResourceType, float]:
        """Calculates effective consumption rates."""
        cons_cfg = config.get("consumption", {})
        rates = {}
        
        b_name = self.type.name
        if b_name not in cons_cfg:
            return {}
            
        cfg_rates = cons_cfg[b_name]
        for r_name, rate in cfg_rates.items():
            rates[ResourceType[r_name]] = rate
            
        return rates

    def _select_primary_resource(self) -> None:
        """Selects the single most abundant metal/mineral on the tile as the primary resource."""
        metals = [
            ResourceType.IRON, ResourceType.COAL, ResourceType.COPPER,
            ResourceType.TIN, ResourceType.SILVER, ResourceType.GOLD
        ]
        best_res = None
        best_val = -1.0
        
        for res in metals:
            val = self.tile.potentials.get(res, 0.0)
            if val > best_val and val > 0:
                best_val = val
                best_res = res
        
        self.primary_resource = best_res

class Tile:
    def __init__(self, x: int, y: int, elevation: float, moisture: float, thresholds: Dict[str, float]):
        self.x = x
        self.y = y
        self.elevation = elevation
        self.moisture = moisture
        self.resources: Dict[ResourceType, float] = {res: 0.0 for res in ResourceType}
        self.potentials: Dict[ResourceType, float] = {res: 0.0 for res in ResourceType}
        self.buildings: List[Building] = []
        self.thresholds = thresholds
        self.type: TileType = self._determine_type()
        self._init_potentials()
        
    def _init_potentials(self) -> None:
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

    def _determine_type(self) -> TileType:
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
    def has_water(self) -> bool:
        return self.type in [TileType.OCEAN, TileType.FRESH_WATER]

class Settlement:
    def __init__(self, name: str, tile: Tile):
        self.name = name
        self.tile = tile
        self.buildings: List[Building] = []

    @property
    def size(self) -> int:
        return len(self.buildings)
