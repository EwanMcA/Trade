import tomllib
from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.core import WindowProperties, Vec2, Vec3, Quat
from direct.task import Task
from game_world import WorldGenerator, MapRenderer, WorldSimulation, TurnManager

def load_config():
    with open("config.toml", "rb") as f:
        return tomllib.load(f)

class InputHandler:
    def __init__(self, base):
        self.base = base
        self.key_map = {"up": False, "down": False, "left": False, "right": False, "mouse2": False, "mouse3": False}
        
        self.base.accept("w", self._update_key_map, ["up", True])
        self.base.accept("w-up", self._update_key_map, ["up", False])
        self.base.accept("s", self._update_key_map, ["down", True])
        self.base.accept("s-up", self._update_key_map, ["down", False])
        self.base.accept("a", self._update_key_map, ["left", True])
        self.base.accept("a-up", self._update_key_map, ["left", False])
        self.base.accept("d", self._update_key_map, ["right", True])
        self.base.accept("d-up", self._update_key_map, ["right", False])
        
        self.base.accept("mouse2", self._update_key_map, ["mouse2", True])
        self.base.accept("mouse2-up", self._update_key_map, ["mouse2", False])
        self.base.accept("mouse3", self._update_key_map, ["mouse3", True])
        self.base.accept("mouse3-up", self._update_key_map, ["mouse3", False])

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
        
        cam_cfg = config["camera"]
        self.zoom_level = cam_cfg["start_pos"][2]
        self.min_zoom = cam_cfg["min_zoom"]
        self.max_zoom = cam_cfg["max_zoom"]
        self.move_speed = cam_cfg["move_speed"]
        self.zoom_speed = cam_cfg["zoom_speed"]
        self.pan_speed = cam_cfg["pan_speed"]
        self.rotate_speed = cam_cfg["rotate_speed"]
        self.zoom_ref = cam_cfg["zoom_ref"]
        self.pitch_limit_min = cam_cfg["pitch_limit_min"]
        self.pitch_limit_max = cam_cfg["pitch_limit_max"]
        
        self.last_mouse_pos = None
        
        self.camera.setPos(*cam_cfg["start_pos"])
        self.camera.setHpr(*cam_cfg["start_hpr"])
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
        hpr = self.camera.getHpr()
        
        # Scale speed with zoom
        zoom_scale = (self.zoom_level / self.zoom_ref)
        actual_speed = self.move_speed * zoom_scale
        
        h_quat = Quat()
        h_quat.setHpr(Vec3(hpr.getX(), 0, 0))
        forward = h_quat.getForward()
        right = h_quat.getRight()

        # Keyboard
        if self.input_handler.is_active("up"):
            pos += forward * actual_speed * dt
        if self.input_handler.is_active("down"):
            pos -= forward * actual_speed * dt
        if self.input_handler.is_active("left"):
            pos -= right * actual_speed * dt
        if self.input_handler.is_active("right"):
            pos += right * actual_speed * dt
            
        # Mouse
        if self.base.mouseWatcherNode.hasMouse():
            mpos = self.base.mouseWatcherNode.getMouse()
            if self.input_handler.is_active("mouse2"): # Panning
                if self.last_mouse_pos:
                    delta = mpos - self.last_mouse_pos
                    pos -= right * delta.getX() * self.pan_speed * zoom_scale
                    pos -= forward * delta.getY() * self.pan_speed * zoom_scale
                self.last_mouse_pos = Vec2(mpos.getX(), mpos.getY())
            elif self.input_handler.is_active("mouse3"): # Rotation
                if self.last_mouse_pos:
                    delta = mpos - self.last_mouse_pos
                    hpr.setX(hpr.getX() - delta.getX() * self.rotate_speed)
                    hpr.setY(max(self.pitch_limit_min, min(self.pitch_limit_max, hpr.getY() + delta.getY() * self.rotate_speed)))
                self.last_mouse_pos = Vec2(mpos.getX(), mpos.getY())
            else:
                self.last_mouse_pos = None
        else:
            self.last_mouse_pos = None
            
        self.camera.setPos(pos)
        self.camera.setHpr(hpr)
        return Task.cont

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
