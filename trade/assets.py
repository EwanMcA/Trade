from panda3d.core import NodePath, Loader
from typing import Dict

class AssetManager:
    def __init__(self, loader: Loader):
        self.loader = loader
        self.models: Dict[str, NodePath] = {}
        self.textures: Dict[str, NodePath] = {}

    def get_model(self, path: str) -> NodePath:
        if path not in self.models:
            self.models[path] = self.loader.loadModel(path)
        # Return a copy to avoid modifying the original
        return self.models[path].copyTo(NodePath())

    def get_instance(self, path: str, parent: NodePath) -> NodePath:
        """Returns a copy of the model parented to the given node."""
        if path not in self.models:
            self.models[path] = self.loader.loadModel(path)
        return self.models[path].copyTo(parent)
