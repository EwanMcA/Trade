class WorldMap:
    def __init__(self, size=40):
        self.size = size
        self.tiles = {}
        self.settlements = []

    def get_tile(self, x, y):
        return self.tiles.get((x, y))
