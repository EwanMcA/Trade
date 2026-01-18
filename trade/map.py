from typing import Dict, Tuple, List, Optional
from .models import Tile, Settlement

class WorldMap:
    def __init__(self, size: int = 40):
        self.size = size
        self.tiles: Dict[Tuple[int, int], Tile] = {}
        self.settlements: List[Settlement] = []

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        return self.tiles.get((x, y))
