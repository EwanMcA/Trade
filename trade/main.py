import tomllib
from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, CollisionTraverser, CollisionNode, CollisionHandlerQueue, CollisionRay, NodePath, GeomNode
from direct.gui.DirectGui import DirectButton

from .simulation import WorldSimulation, TurnManager
from .constants import ResourceType
from .generation import WorldGenerator
from .input import InputHandler
from .camera import CameraController
from .render import MapRenderer
from .assets import AssetManager
from .ui import HUD, BuildingInfoUI


def load_config():
    with open("config.toml", "rb") as f:
        return tomllib.load(f)

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.game_config = load_config()
        
        self._setup_window()
        self.disableMouse()
        self.render.setShaderAuto()
        
        self.input_handler = InputHandler(self)
        self.camera_controller = CameraController(self, self.input_handler, self.game_config)
        self.asset_mgr = AssetManager(self.loader)
        
        map_size = self.game_config["map"]["size"]
        self.generator = WorldGenerator(map_size, self.game_config)
        self.world_map = self.generator.generate()
        self.simulation = WorldSimulation(self.world_map, self.game_config)

        self.renderer = MapRenderer(self.world_map, self.game_config)
        self.renderer.render(self.render, self.asset_mgr)
        
        self.turn_mgr = TurnManager(self.simulation)

        self._setup_ui()
        self._setup_picking()

        self.accept("space", self.next_turn)
        self.accept("tab", self.hud.toggle_visibility)
        self.accept("t", self.renderer.set_view_mode, ["TERRAIN"])
        self.accept("mouse1", self.handle_click)
        
        res_keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        resources = list(ResourceType)
        for i, res in enumerate(resources):
            if i < len(res_keys):
                self.accept(res_keys[i], self.renderer.set_view_mode, [res])

    def _setup_window(self):
        win_cfg = self.game_config["window"]
        props = WindowProperties()
        props.setTitle(win_cfg["title"])
        props.setSize(win_cfg["width"], win_cfg["height"])
        self.win.requestProperties(props)

    def _setup_ui(self):
        self.hud = HUD(self.aspect2d)
        self.hud.update(self.turn_mgr.turn_count, self.simulation.get_stats())
        self.building_info_ui = BuildingInfoUI(self.aspect2d)
        
        self.end_turn_btn = DirectButton(
            text="End Turn",
            scale=0.1,
            pos=(1.4, 0, -0.9),
            frameColor=(0.2, 0.9, 0.2, 1),
            text_scale=0.6,
            command=self.next_turn
        )

    def _setup_picking(self):
        self.picker = CollisionTraverser()
        self.pq = CollisionHandlerQueue()
        self.picker_node = CollisionNode('mouseRay')
        self.picker_np = self.camera.attachNewNode(self.picker_node)
        self.picker_node.setFromCollideMask(GeomNode.getDefaultCollideMask())
        self.picker_ray = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)
        self.picker.addCollider(self.picker_np, self.pq)

    def handle_click(self):
        if not self.mouseWatcherNode.hasMouse():
            return

        mpos = self.mouseWatcherNode.getMouse()
        self.picker_ray.setFromLens(self.camNode, mpos.getX(), mpos.getY())
        self.picker.traverse(self.render)

        if self.pq.getNumEntries() > 0:
            self.pq.sortEntries()
            entry = self.pq.getEntry(0)
            picked_obj = entry.getIntoNodePath()
            
            # Find the parent that has the tag
            building_node = picked_obj.findNetTag("building_idx")
            if not building_node.isEmpty():
                idx = int(building_node.getTag("building_idx"))
                building = self.renderer._index_to_building.get(idx)
                if building:
                    self.renderer.selected_building = building
                    self.building_info_ui.show(building, self.game_config)
                    return

        # If we clicked nothing
        self.renderer.selected_building = None
        self.building_info_ui.hide()

    def next_turn(self):
        self.turn_mgr.next_turn()
        self.renderer.update_buildings(self.asset_mgr)
        self.hud.update(self.turn_mgr.turn_count, self.simulation.get_stats())
        self.building_info_ui.refresh(self.game_config)

if __name__ == "__main__":
    game = Game()
    game.run()
