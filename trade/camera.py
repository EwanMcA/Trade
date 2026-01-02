from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.core import Vec2, Vec3, Quat
from direct.task import Task

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
