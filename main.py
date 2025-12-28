import tomllib
from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties
from direct.task import Task
from game_world import WorldGenerator, MapRenderer, WorldSimulation, TurnManager

def load_config():
    with open("config.toml", "rb") as f:
        return tomllib.load(f)

class InputHandler:
    def __init__(self, base):
        self.base = base
        self.key_map = {"up": False, "down": False, "left": False, "right": False}
        
        self.base.accept("w", self._update_key_map, ["up", True])
        self.base.accept("w-up", self._update_key_map, ["up", False])
        self.base.accept("s", self._update_key_map, ["down", True])
        self.base.accept("s-up", self._update_key_map, ["down", False])
        self.base.accept("a", self._update_key_map, ["left", True])
        self.base.accept("a-up", self._update_key_map, ["left", False])
        self.base.accept("d", self._update_key_map, ["right", True])
        self.base.accept("d-up", self._update_key_map, ["right", False])

    def _update_key_map(self, key, state):
        self.key_map[key] = state

    def is_active(self, key):
        return self.key_map.get(key, False)

class CameraController:
    def __init__(self, base, input_handler, config):
        self.base = base
        self.camera = base.camera
        self.input_handler = input_handler
        self.config = config
        
        # Camera configuration
        cam_cfg = config["camera"]
        self.zoom_level = cam_cfg["start_pos"][2]
        self.min_zoom = cam_cfg["min_zoom"]
        self.max_zoom = cam_cfg["max_zoom"]
        self.move_speed = cam_cfg["move_speed"]
        self.zoom_speed = cam_cfg["zoom_speed"]
        
        self.camera.setPos(*cam_cfg["start_pos"])
        self.camera.setHpr(0, -90, 0) # Look straight down
        self.base.camLens.setFov(cam_cfg["fov"])
        
        self.base.accept("wheel_up", self.adjust_zoom, [-self.zoom_speed])
        self.base.accept("wheel_down", self.adjust_zoom, [self.zoom_speed])
        
        self.base.taskMgr.add(self.update, "CameraControllerUpdate")

    def adjust_zoom(self, amount):
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, self.zoom_level + amount))
        self.camera.setZ(self.zoom_level)

    def update(self, task):
        dt = globalClock.getDt()
        pos = self.camera.getPos()
        
        # Speed scales with zoom for smoother navigation
        # We use the initial start zoom (40) as a reference point for scaling
        actual_speed = self.move_speed * (self.zoom_level / 40.0)
        
        if self.input_handler.is_active("up"):
            pos.setY(pos.getY() + actual_speed * dt)
        if self.input_handler.is_active("down"):
            pos.setY(pos.getY() - actual_speed * dt)
        if self.input_handler.is_active("left"):
            pos.setX(pos.getX() - actual_speed * dt)
        if self.input_handler.is_active("right"):
            pos.setX(pos.getX() + actual_speed * dt)
            
        self.camera.setPos(pos)
        return Task.cont

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.game_config = load_config()
        
        self._setup_window()
        self.disableMouse()
        self.render.setShaderAuto()
        
        # Input and Camera
        self.input_handler = InputHandler(self)
        self.camera_controller = CameraController(self, self.input_handler, self.game_config)
        
        # World setup
        map_size = self.game_config["map"]["size"]
        self.generator = WorldGenerator(map_size, self.game_config)
        self.world_map = self.generator.generate()
        self.renderer = MapRenderer(self.world_map, self.game_config)
        self.renderer.render(self.render, self.loader)
        
        self.simulation = WorldSimulation(self.world_map, self.game_config)
        self.turn_mgr = TurnManager(self.simulation)

        # Global input for game control
        self.accept("space", self.next_turn)

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
