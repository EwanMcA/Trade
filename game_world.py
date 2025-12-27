import random
from enum import Enum, auto
from panda3d.core import NodePath, Vec4, PerlinNoise2
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomTriangles, GeomNode

class TileType(Enum):
    OCEAN = auto()
    FRESH_WATER = auto()
    ARID = auto()
    GRASSLAND = auto()
    FOREST = auto()
    TUNDRA = auto()
    ROCKY = auto()

class Tile:
    def __init__(self, x, y, elevation, moisture):
        self.x = x
        self.y = y
        self.elevation = elevation
        self.moisture = moisture
        self.resource = None
        self.settlement = None
        self.type = self._determine_type()
        
    def _determine_type(self):
        if self.elevation < 0.3:
            return TileType.OCEAN
        if self.elevation > 0.85:
            return TileType.ROCKY
            
        if self.elevation > 0.7 and self.moisture < 0.3:
            return TileType.TUNDRA
            
        if self.moisture < 0.25:
            return TileType.ARID
        if self.moisture < 0.55:
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
        self.visual_node = None

    def grow(self):
        self.size += 1
        if self.visual_node:
            self.visual_node.setScale(1, 1, self.size * 0.5)

class MapManager:
    def __init__(self, size=40):
        self.size = size
        self.tiles = {}
        self.root = NodePath("MapRoot")
        self.settlements = []
        
    def generate_map(self):
        seed = random.randint(0, 10000)
        elev_noise = PerlinNoise2(8, 8, 256, seed)
        moist_noise = PerlinNoise2(8, 8, 256, seed + 1)
        
        for x in range(self.size):
            for y in range(self.size):
                e = (elev_noise.noise(x * 0.15, y * 0.15) * 0.8 + 
                     elev_noise.noise(x * 0.4, y * 0.4) * 0.2)
                e = (e + 1) / 2.0
                e = (e - 0.1) / 0.8
                e = max(0, min(1, e))
                
                m = (moist_noise.noise(x * 0.2, y * 0.2) + 1) / 2.0
                m = (m - 0.1) / 0.8
                m = max(0, min(1, m))
                
                self.tiles[(x, y)] = Tile(x, y, e, m)

        self.generate_rivers()
            
    def generate_rivers(self):
        sources = [t for t in self.tiles.values() if t.elevation > 0.8 and t.type == TileType.ROCKY]
        num_rivers = random.randint(int(self.size/10), int(self.size/5))
        
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
                        neighbor = self.tiles.get((nx, ny))
                        if neighbor and (nx, ny) not in visited:
                            neighbors.append(neighbor)
                
                if not neighbors:
                    break
                    
                neighbors.sort(key=lambda t: t.elevation)
                next_tile = neighbors[0]
                
                if next_tile.elevation >= current.elevation:
                    if random.random() > 0.2:
                        break
                
                current = next_tile
                
            for tile in path:
                if tile.type != TileType.OCEAN:
                    tile.type = TileType.FRESH_WATER

    def render_map(self, parent, loader):
        self.root.reparentTo(parent)
        
        type_colors = {
            TileType.OCEAN: Vec4(0.1, 0.3, 0.6, 1),
            TileType.FRESH_WATER: Vec4(0.3, 0.6, 0.9, 1),
            TileType.ARID: Vec4(0.8, 0.7, 0.4, 1),
            TileType.GRASSLAND: Vec4(0.4, 0.7, 0.3, 1),
            TileType.FOREST: Vec4(0.1, 0.4, 0.1, 1),
            TileType.TUNDRA: Vec4(0.7, 0.7, 0.8, 1),
            TileType.ROCKY: Vec4(0.5, 0.5, 0.5, 1),
        }
        
        format = GeomVertexFormat.getV3c4()
        vdata = GeomVertexData('map_data', format, Geom.UHStatic)
        
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')
        
        prim = GeomTriangles(Geom.UHStatic)
        
        v_idx = 0
        for (x, y), tile in self.tiles.items():
            c = type_colors.get(tile.type, Vec4(1, 1, 1, 1))
            
            vertex.addData3(x, y, 0)
            vertex.addData3(x + 1, y, 0)
            vertex.addData3(x + 1, y + 1, 0)
            vertex.addData3(x, y + 1, 0)
            
            for _ in range(4):
                color.addData4(c)
                
            prim.addVertices(v_idx, v_idx + 1, v_idx + 2)
            prim.addVertices(v_idx, v_idx + 2, v_idx + 3)
            v_idx += 4
            
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        
        node = GeomNode('map_geom')
        node.addGeom(geom)
        self.root.attachNewNode(node)

    def update_visuals(self, loader):
        for s in self.settlements:
            if not s.visual_node:
                s.visual_node = loader.loadModel("models/box")
                s.visual_node.reparentTo(self.root)
                s.visual_node.setPos(s.tile.x + 0.5, s.tile.y + 0.5, 0)
                s.visual_node.setScale(0.4, 0.4, 0.5)
                s.visual_node.setColor(0.8, 0.2, 0.2, 1)

class TurnManager:
    def __init__(self, map_manager):
        self.map_manager = map_manager
        self.turn_count = 0
        
    def next_turn(self):
        self.turn_count += 1
        print(f"--- Turn {self.turn_count} ---")
        self.simulate_growth()
        self.spawn_new_settlements()
        
    def simulate_growth(self):
        for s in self.map_manager.settlements:
            near_water = False
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    neighbor = self.map_manager.tiles.get((s.tile.x + dx, s.tile.y + dy))
                    if neighbor and neighbor.has_water:
                        near_water = True
                        break
            
            if near_water and random.random() < 0.3:
                s.grow()
                print(f"Settlement at {s.tile.x}, {s.tile.y} grew to size {s.size}")

    def spawn_new_settlements(self):
        if random.random() < 0.2:
            potential_tiles = []
            for (x, y), tile in self.map_manager.tiles.items():
                if not tile.settlement and not tile.has_water:
                    has_nearby_water = False
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            neighbor = self.map_manager.tiles.get((x + dx, y + dy))
                            if neighbor and neighbor.has_water:
                                has_nearby_water = True
                                break
                    if has_nearby_water:
                        potential_tiles.append(tile)
            
            if potential_tiles:
                target = random.choice(potential_tiles)
                new_s = Settlement(f"City {len(self.map_manager.settlements)}", target)
                self.map_manager.settlements.append(new_s)
                print(f"New settlement founded at {target.x}, {target.y}")
