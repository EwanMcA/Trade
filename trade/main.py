import tomllib
from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties

from game_world import WorldSimulation, TurnManager
from generation import WorldGenerator
from input import InputHandler
from camera import CameraController
from render import MapRenderer


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
        
        map_size = self.game_config["map"]["size"]
        self.generator = WorldGenerator(map_size, self.game_config)
        self.world_map = self.generator.generate()
        self.renderer = MapRenderer(self.world_map, self.game_config)
        self.renderer.render(self.render, self.loader)
        
        self.simulation = WorldSimulation(self.world_map, self.game_config)
        self.turn_mgr = TurnManager(self.simulation)

        self.accept("space", self.next_turn)
        self.accept("t", self.renderer.set_view_mode, ["TERRAIN"])
        
        from game_world import ResourceType
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

    def next_turn(self):
        self.turn_mgr.next_turn()
        self.renderer.update_settlements(self.loader)

if __name__ == "__main__":
    game = Game()
    game.run()
