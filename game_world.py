import random
from panda3d.core import NodePath, CardMaker, Vec3, Vec4

class Tile:
    def __init__(self, x, y, elevation, moisture):
        self.x = x
        self.y = y
        self.elevation = elevation
        self.moisture = moisture
        self.resource = None
        self.has_water = False
        self.settlement = None
        
        # Determine if it has fresh water
        if self.elevation < 0.4 and self.moisture > 0.6:
            self.has_water = True
            self.resource = "Fresh Water"

class Settlement:
    def __init__(self, name, tile):
        self.name = name
        self.tile = tile
        self.size = 1 # Population/Size level
        self.tile.settlement = self
        self.visual_node = None

    def grow(self):
        self.size += 1
        if self.visual_node:
            self.visual_node.setScale(1, 1, self.size * 0.5)

class MapManager:
    def __init__(self, size=40):
        self.size = size
        self.tiles = {}
        self.root = NodePath("MapRoot")
        self.settlements = []
        
    def generate_map(self):
        raw_data = {}
        for x in range(self.size):
            for y in range(self.size):
                elev = random.random()
                moist = random.random()
                raw_data[(x, y)] = [elev, moist]
        
        # Smoothing pass
        for _ in range(3):
            new_data = {}
            for x in range(self.size):
                for y in range(self.size):
                    e_sum, m_sum, count = 0, 0, 0
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            nx, ny = x + dx, y + dy
                            if (nx, ny) in raw_data:
                                e, m = raw_data[(nx, ny)]
                                e_sum += e
                                m_sum += m
                                count += 1
                    new_data[(x, y)] = [e_sum / count, m_sum / count]
            raw_data = new_data
            
        for (x, y), (e, m) in raw_data.items():
            self.tiles[(x, y)] = Tile(x, y, e, m)
            
    def render_map(self, parent, loader):
        self.root.reparentTo(parent)
        cm = CardMaker("tile")
        cm.setFrame(0, 1, 0, 1)
        
        for (x, y), tile in self.tiles.items():
            tile_node = self.root.attachNewNode(cm.generate())
            tile_node.setHpr(0, -90, 0)
            tile_node.setPos(x, y, 0)
            
            if tile.has_water:
                color = Vec4(0.2, 0.5, 0.9, 1)
            elif tile.elevation < 0.3:
                color = Vec4(0.3, 0.7, 0.3, 1)
            elif tile.elevation < 0.6:
                color = Vec4(0.4, 0.8, 0.4, 1)
            elif tile.elevation < 0.8:
                color = Vec4(0.6, 0.6, 0.5, 1)
            else:
                color = Vec4(0.9, 0.9, 0.9, 1)
                
            tile_node.setColor(color)

    def update_visuals(self, loader):
        # Render settlements
        for s in self.settlements:
            if not s.visual_node:
                s.visual_node = loader.loadModel("models/box")
                s.visual_node.reparentTo(self.root)
                s.visual_node.setPos(s.tile.x + 0.5, s.tile.y + 0.5, 0)
                s.visual_node.setScale(0.4, 0.4, 0.5)
                s.visual_node.setColor(0.8, 0.2, 0.2, 1)

class TurnManager:
    def __init__(self, map_manager):
        self.map_manager = map_manager
        self.turn_count = 0
        
    def next_turn(self):
        self.turn_count += 1
        print(f"--- Turn {self.turn_count} ---")
        self.simulate_growth()
        self.spawn_new_settlements()
        
    def simulate_growth(self):
        for s in self.map_manager.settlements:
            # Grow if near water
            near_water = False
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    neighbor = self.map_manager.tiles.get((s.tile.x + dx, s.tile.y + dy))
                    if neighbor and neighbor.has_water:
                        near_water = True
                        break
            
            if near_water and random.random() < 0.3:
                s.grow()
                print(f"Settlement at {s.tile.x}, {s.tile.y} grew to size {s.size}")

    def spawn_new_settlements(self):
        # Chance to spawn a new settlement near water if not already occupied
        if random.random() < 0.2:
            potential_tiles = []
            for (x, y), tile in self.map_manager.tiles.items():
                if not tile.settlement and not tile.has_water:
                    # Check for nearby water
                    has_nearby_water = False
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            neighbor = self.map_manager.tiles.get((x + dx, y + dy))
                            if neighbor and neighbor.has_water:
                                has_nearby_water = True
                                break
                    if has_nearby_water:
                        potential_tiles.append(tile)
            
            if potential_tiles:
                target = random.choice(potential_tiles)
                new_s = Settlement(f"City {len(self.map_manager.settlements)}", target)
                self.map_manager.settlements.append(new_s)
                print(f"New settlement founded at {target.x}, {target.y}")
