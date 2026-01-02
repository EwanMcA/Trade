from panda3d.core import NodePath, Vec4, Vec3
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomTriangles, GeomNode
from panda3d.core import DirectionalLight, AmbientLight

from game_world import TileType


class MapRenderer:
    def __init__(self, world_map, config):
        self.world_map = world_map
        self.config = config
        self.root = NodePath("MapRoot")
        self.settlement_nodes = {} # Settlement -> NodePath
        self.vdata = None
        self.view_mode = "TERRAIN" # "TERRAIN" or ResourceType

    def _get_elev(self, x, y):
        size = self.world_map.size
        # Map corners to tile elevations
        tx = max(0, min(size - 1, x))
        ty = max(0, min(size - 1, y))
        return self.world_map.get_tile(tx, ty).elevation

    def set_view_mode(self, mode):
        """mode can be 'TERRAIN' or a ResourceType"""
        self.view_mode = mode
        self.update_colors()

    def update_colors(self):
        if not self.vdata:
            return
            
        color_writer = GeomVertexWriter(self.vdata, 'color')
        color_writer.setRow(0)
        
        color_cfg = self.config["colors"]
        type_colors = {
            TileType.OCEAN: Vec4(*color_cfg["OCEAN"]),
            TileType.FRESH_WATER: Vec4(*color_cfg["FRESH_WATER"]),
            TileType.ARID: Vec4(*color_cfg["ARID"]),
            TileType.GRASSLAND: Vec4(*color_cfg["GRASSLAND"]),
            TileType.FOREST: Vec4(*color_cfg["FOREST"]),
            TileType.TUNDRA: Vec4(*color_cfg["TUNDRA"]),
            TileType.ROCKY: Vec4(*color_cfg["ROCKY"]),
        }
        
        for (x, y), tile in self.world_map.tiles.items():
            if self.view_mode == "TERRAIN":
                c = type_colors.get(tile.type, Vec4(1, 1, 1, 1))
            else:
                amount = tile.resources.get(self.view_mode, 0.0)
                if amount == 0:
                    val = tile.potentials.get(self.view_mode, 0.0)
                    c = Vec4(0.2, 0.2, 0.2 + val * 0.8, 1.0) # Blue for potential
                else:
                    val = min(1.0, amount / 100.0) # Normalize
                    c = Vec4(val, 0.2, 0.2, 1.0) # Red for amount
            
            for _ in range(4):
                color_writer.addData4(c)

    def render(self, parent, loader):
        self.root.reparentTo(parent)
        
        vis_cfg = self.config["visuals"]
        height_scale = vis_cfg["height_scale"]
        
        format = GeomVertexFormat.getV3n3c4()
        self.vdata = GeomVertexData('map_data', format, Geom.UHDynamic)
        
        vertex = GeomVertexWriter(self.vdata, 'vertex')
        normal = GeomVertexWriter(self.vdata, 'normal')
        
        prim = GeomTriangles(Geom.UHStatic)
        
        v_idx = 0
        for y in range(self.world_map.size):
            for x in range(self.world_map.size):
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
                
                # Calculate normal
                side1 = v1 - v0
                side2 = v3 - v0
                n = side1.cross(side2)
                n.normalize()
                
                for _ in range(4):
                    normal.addData3(n)
                    
                prim.addVertices(v_idx, v_idx + 1, v_idx + 2)
                prim.addVertices(v_idx, v_idx + 2, v_idx + 3)
                v_idx += 4
            
        self.update_colors() # Initial color set
        
        geom = Geom(self.vdata)
        geom.addPrimitive(prim)
        
        node = GeomNode('map_geom')
        node.addGeom(geom)
        self.root.attachNewNode(node)
        
        self._setup_lighting(parent)
        
        self.update_settlements(loader)

    def _setup_lighting(self, parent):
        light_cfg = self.config["lighting"]
        
        dlight = DirectionalLight('sun')
        dlight.setColor(Vec4(*light_cfg["sun_color"]))
        dlnp = parent.attachNewNode(dlight)
        dlnp.setHpr(0, light_cfg.get("sun_tilt", -60.0), 0) # Tilt it down

        dir = Vec3(*light_cfg["sun_direction"])
        dlnp.lookAt(dir)
        parent.setLight(dlnp)
        
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
                # on top of the tile
                h = s.tile.elevation * height_scale
                node.setPos(s.tile.x + 0.5, s.tile.y + 0.5, h)
                node.setColor(*vis_cfg["settlement_color"])
                self.settlement_nodes[s] = node
            
            # Update scale based on size
            base_scale = vis_cfg["settlement_scale"]
            self.settlement_nodes[s].setScale(base_scale[0], base_scale[1], s.size * base_scale[2])
