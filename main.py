from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, Vec3
from direct.task import Task
from game_world import MapManager, TurnManager

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        
        props = WindowProperties()
        props.setTitle("Trade Simulation")
        self.win.requestProperties(props)
        
        self.disableMouse()
        
        # World setup
        self.map_mgr = MapManager(size=40)
        self.map_mgr.generate_map()
        self.map_mgr.render_map(self.render, self.loader)
        
        self.turn_mgr = TurnManager(self.map_mgr)
        
        # Camera setup
        self.camera.setPos(20, 20, 40)
        self.camera.setHpr(0, -90, 0) # Look straight down
        
        # Camera movement variables
        self.zoom_level = 40
        self.min_zoom = 5
        self.max_zoom = 100
        self.move_speed = 30
        
        # Keyboard state
        self.key_map = {"up": False, "down": False, "left": False, "right": False}
        self.accept("w", self.update_key_map, ["up", True])
        self.accept("w-up", self.update_key_map, ["up", False])
        self.accept("s", self.update_key_map, ["down", True])
        self.accept("s-up", self.update_key_map, ["down", False])
        self.accept("a", self.update_key_map, ["left", True])
        self.accept("a-up", self.update_key_map, ["left", False])
        self.accept("d", self.update_key_map, ["right", True])
        self.accept("d-up", self.update_key_map, ["right", False])
        
        # Turn control
        self.accept("space", self.next_turn)
        
        # Zoom controls
        self.accept("wheel_up", self.adjust_zoom, [-3.0])
        self.accept("wheel_down", self.adjust_zoom, [3.0])
        
        # Task for movement
        self.taskMgr.add(self.move_camera_task, "MoveCameraTask")

    def update_key_map(self, key, state):
        self.key_map[key] = state

    def adjust_zoom(self, amount):
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, self.zoom_level + amount))
        self.camera.setZ(self.zoom_level)

    def next_turn(self):
        self.turn_mgr.next_turn()
        self.map_mgr.update_visuals(self.loader)

    def move_camera_task(self, task):
        dt = globalClock.getDt()
        pos = self.camera.getPos()
        
        actual_speed = self.move_speed * (self.zoom_level / 40.0)
        
        if self.key_map["up"]:
            pos.setY(pos.getY() + actual_speed * dt)
        if self.key_map["down"]:
            pos.setY(pos.getY() - actual_speed * dt)
        if self.key_map["left"]:
            pos.setX(pos.getX() - actual_speed * dt)
        if self.key_map["right"]:
            pos.setX(pos.getX() + actual_speed * dt)
            
        self.camera.setPos(pos)
        return Task.cont

if __name__ == "__main__":
    game = Game()
    game.run()
