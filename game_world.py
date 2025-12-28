import random
from enum import Enum, auto
from panda3d.core import NodePath, Vec4, Vec3, PerlinNoise2
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomTriangles, GeomNode
from panda3d.core import DirectionalLight, AmbientLight

class TileType(Enum):
    OCEAN = auto()
    FRESH_WATER = auto()
    ARID = auto()
    GRASSLAND = auto()
    FOREST = auto()
    TUNDRA = auto()
    ROCKY = auto()

class Tile:
    def __init__(self, x, y, elevation, moisture, thresholds):
        self.x = x
        self.y = y
        self.elevation = elevation
        self.moisture = moisture
        self.resource = None
        self.settlement = None
        self.thresholds = thresholds
        self.type = self._determine_type()
        
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
            
        elev_noise = PerlinNoise2(8, 8, 256, seed)
        moist_noise = PerlinNoise2(8, 8, 256, seed + 1)
        
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
        sources = [t for t in world_map.tiles.values() if t.elevation > sim_cfg["river_source_min_elevation"] and t.type == TileType.ROCKY]
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

class MapRenderer:
    def __init__(self, world_map, config):
        self.world_map = world_map
        self.config = config
        self.root = NodePath("MapRoot")
        self.settlement_nodes = {} # Settlement -> NodePath

    def _get_elev(self, x, y):
        size = self.world_map.size
        # Map corners to tile elevations
        tx = max(0, min(size - 1, x))
        ty = max(0, min(size - 1, y))
        return self.world_map.get_tile(tx, ty).elevation

    def render(self, parent, loader):
        self.root.reparentTo(parent)
        
        color_cfg = self.config["colors"]
        vis_cfg = self.config["visuals"]
        height_scale = vis_cfg["height_scale"]
        
        type_colors = {
            TileType.OCEAN: Vec4(*color_cfg["OCEAN"]),
            TileType.FRESH_WATER: Vec4(*color_cfg["FRESH_WATER"]),
            TileType.ARID: Vec4(*color_cfg["ARID"]),
            TileType.GRASSLAND: Vec4(*color_cfg["GRASSLAND"]),
            TileType.FOREST: Vec4(*color_cfg["FOREST"]),
            TileType.TUNDRA: Vec4(*color_cfg["TUNDRA"]),
            TileType.ROCKY: Vec4(*color_cfg["ROCKY"]),
        }
        
        # Use V3n3c4 format for vertex, normal, and color
        format = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData('map_data', format, Geom.UHStatic)
        
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        color = GeomVertexWriter(vdata, 'color')
        
        prim = GeomTriangles(Geom.UHStatic)
        
        v_idx = 0
        for (x, y), tile in self.world_map.tiles.items():
            c = type_colors.get(tile.type, Vec4(1, 1, 1, 1))
            
            # Corner heights
            h00 = self._get_elev(x, y) * height_scale
            h10 = self._get_elev(x + 1, y) * height_scale
            h11 = self._get_elev(x + 1, y + 1) * height_scale
            h01 = self._get_elev(x, y + 1) * height_scale
            
            # Vertices
            v0 = Vec3(x, y, h00)
            v1 = Vec3(x + 1, y, h10)
            v2 = Vec3(x + 1, y + 1, h11)
            v3 = Vec3(x, y + 1, h01)
            
            vertex.addData3(v0)
            vertex.addData3(v1)
            vertex.addData3(v2)
            vertex.addData3(v3)
            
            # Calculate normal for the quad (simplified as average of two triangles)
            side1 = v1 - v0
            side2 = v3 - v0
            n = side1.cross(side2)
            n.normalize()
            
            for _ in range(4):
                normal.addData3(n)
                color.addData4(c)
                
            prim.addVertices(v_idx, v_idx + 1, v_idx + 2)
            prim.addVertices(v_idx, v_idx + 2, v_idx + 3)
            v_idx += 4
            
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        
        node = GeomNode('map_geom')
        node.addGeom(geom)
        self.root.attachNewNode(node)
        
        # Enable lighting and set a basic material
        self._setup_lighting(parent)
        
        self.update_settlements(loader)

    def _setup_lighting(self, parent):
        light_cfg = self.config["lighting"]
        
        # Directional light (Sun)
        dlight = DirectionalLight('sun')
        dlight.setColor(Vec4(*light_cfg["sun_color"]))
        dlnp = parent.attachNewNode(dlight)
        dlnp.setHpr(0, -60, 0) # Tilt it down
        # We can also use sun_direction from config
        dir = Vec3(*light_cfg["sun_direction"])
        dlnp.lookAt(dir)
        parent.setLight(dlnp)
        
        # Ambient light
        alight = AmbientLight('ambient')
        alight.setColor(Vec4(*light_cfg["ambient_color"]))
        alnp = parent.attachNewNode(alight)
        parent.setLight(alnp)

    def update_settlements(self, loader):
        vis_cfg = self.config["visuals"]
        height_scale = vis_cfg["height_scale"]
        
        for s in self.world_map.settlements:
            if s not in self.settlement_nodes:
                node = loader.loadModel("models/box")
                node.reparentTo(self.root)
                # Position on top of the tile
                h = s.tile.elevation * height_scale
                node.setPos(s.tile.x + 0.5, s.tile.y + 0.5, h)
                node.setColor(*vis_cfg["settlement_color"])
                self.settlement_nodes[s] = node
            
            # Update scale based on size
            base_scale = vis_cfg["settlement_scale"]
            self.settlement_nodes[s].setScale(base_scale[0], base_scale[1], s.size * base_scale[2])

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
