from panda3d.core import NodePath, Vec4, Vec3
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomTriangles, GeomNode
from panda3d.core import DirectionalLight, AmbientLight
from typing import Dict, Any, Optional

from .constants import TileType, BuildingType
from .assets import AssetManager
from .models import Building
from .map import WorldMap


# TODO: SLOW AT HIGH BUILDING COUNTS

class MapRenderer:
    def __init__(self, world_map: WorldMap, config: Dict[str, Any]):
        self.world_map = world_map
        self.config = config
        self.root = NodePath("MapRoot")
        self.building_nodes: Dict[Building, NodePath] = {}
        self.vdata: Optional[GeomVertexData] = None
        self.view_mode: str = "TERRAIN" # "TERRAIN" or ResourceType
        
        self.type_styles = {
            BuildingType.RESIDENTIAL_HIGH: {"color": (0.7, 0.2, 0.2, 1.0), "scale": (0.35, 0.35, 0.6)},
            BuildingType.RESIDENTIAL_LOW: {"color": (0.5, 0.5, 0.5, 1.0), "scale": (0.25, 0.25, 0.25)},
            BuildingType.LUMBER_YARD: {"color": (0.4, 0.2, 0.0, 1.0), "scale": (0.4, 0.4, 0.3)},
            BuildingType.FARM: {"color": (0.8, 0.8, 0.2, 1.0), "scale": (0.6, 0.6, 0.1)},
            BuildingType.DOCK: {"color": (0.1, 0.3, 0.6, 1.0), "scale": (0.4, 0.6, 0.15)},
            BuildingType.MINE: {"color": (0.2, 0.2, 0.2, 1.0), "scale": (0.3, 0.3, 0.4)},
            BuildingType.QUARRY: {"color": (0.6, 0.6, 0.6, 1.0), "scale": (0.5, 0.5, 0.2)},
        }

    def _get_elev(self, x: int, y: int) -> float:
        size = self.world_map.size
        # Map corners to tile elevations
        tx = max(0, min(size - 1, x))
        ty = max(0, min(size - 1, y))
        return self.world_map.get_tile(tx, ty).elevation

    def _get_interpolated_elev(self, x: int, y: int, lx: float, ly: float) -> float:
        h00 = self._get_elev(x, y)
        h10 = self._get_elev(x + 1, y)
        h11 = self._get_elev(x + 1, y + 1)
        h01 = self._get_elev(x, y + 1)
        
        h_bottom = h00 * (1 - lx) + h10 * lx
        h_top = h01 * (1 - lx) + h11 * lx
        return h_bottom * (1 - ly) + h_top * ly

    def set_view_mode(self, mode: str):
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
        
        for y in range(self.world_map.size):
            for x in range(self.world_map.size):
                tile = self.world_map.get_tile(x, y)
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

    def render(self, parent: NodePath, asset_mgr: AssetManager):
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
        
        self.update_buildings(asset_mgr)

    def _setup_lighting(self, parent: NodePath):
        light_cfg = self.config["lighting"]
        
        dlight = DirectionalLight('sun')
        dlight.setColor(Vec4(*light_cfg["sun_color"]))
        dlnp = parent.attachNewNode(dlight)
        dlnp.setHpr(0, light_cfg.get("sun_tilt", -60.0), 0) # Tilt it down

        direction = Vec3(*light_cfg["sun_direction"])
        dlnp.lookAt(direction)
        parent.setLight(dlnp)
        
        alight = AmbientLight('ambient')
        alight.setColor(Vec4(*light_cfg["ambient_color"]))
        alnp = parent.attachNewNode(alight)
        parent.setLight(alnp)

    def update_buildings(self, asset_mgr: AssetManager):
        vis_cfg = self.config["visuals"]
        height_scale = vis_cfg["height_scale"]
        
        for (x, y), tile in self.world_map.tiles.items():
            for building in tile.buildings:
                if building not in self.building_nodes:
                    # Use AssetManager to get a copy instead of loading from disk every time
                    node = asset_mgr.get_instance("models/box", self.root)
                    
                    # Position: tile origin + local offset
                    h = self._get_interpolated_elev(tile.x, tile.y, building.local_pos[0], building.local_pos[1]) * height_scale
                    node.setPos(tile.x + building.local_pos[0],
                                tile.y + building.local_pos[1],
                                h)
                    
                    style = self.type_styles.get(building.type, {"color": (1, 1, 1, 1), "scale": (0.3, 0.3, 0.3)})
                    
                    node.setColor(*style["color"])
                    node.setScale(*style["scale"])
                    node.setTextureOff(1) # Ensure color is visible even if model has texture
                    
                    self.building_nodes[building] = node
