class InputHandler:
    def __init__(self, base):
        self.base = base
        self.key_map = {
            "up": False, "down": False, "left": False, "right": False, 
            "mouse1": False, "mouse2": False, "mouse3": False
        }
        
        self.base.accept("w", self._update_key_map, ["up", True])
        self.base.accept("w-up", self._update_key_map, ["up", False])
        self.base.accept("s", self._update_key_map, ["down", True])
        self.base.accept("s-up", self._update_key_map, ["down", False])
        self.base.accept("a", self._update_key_map, ["left", True])
        self.base.accept("a-up", self._update_key_map, ["left", False])
        self.base.accept("d", self._update_key_map, ["right", True])
        self.base.accept("d-up", self._update_key_map, ["right", False])
        
        self.base.accept("mouse1", self._update_key_map, ["mouse1", True])
        self.base.accept("mouse1-up", self._update_key_map, ["mouse1", False])
        self.base.accept("mouse2", self._update_key_map, ["mouse2", True])
        self.base.accept("mouse2-up", self._update_key_map, ["mouse2", False])
        self.base.accept("mouse3", self._update_key_map, ["mouse3", True])
        self.base.accept("mouse3-up", self._update_key_map, ["mouse3", False])

    def _update_key_map(self, key, state):
        self.key_map[key] = state

    def is_active(self, key):
        return self.key_map.get(key, False)
