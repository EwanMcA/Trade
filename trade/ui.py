from direct.gui.DirectGui import DirectFrame, DirectLabel
from panda3d.core import TextNode
from .constants import BuildingType

class HUD:
    def __init__(self, parent):
        # Semi-transparent background frame on the left
        self.frame = DirectFrame(
            frameColor=(0, 0, 0, 0.6),
            frameSize=(-0.45, 0.45, -0.7, 0.7),
            pos=(-1.2, 0, 0.2),
            parent=parent
        )
        
        self.title = DirectLabel(
            text="World Statistics",
            scale=0.07,
            pos=(0, 0, 0.6),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_font=loader.loadFont('models/cmss12'),
            text_align=TextNode.ACenter
        )
        
        self.turn_label = DirectLabel(
            text="Turn: 0",
            scale=0.05,
            pos=(-0.4, 0, 0.5),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft
        )
        
        self.settlements_label = DirectLabel(
            text="Settlements: 0",
            scale=0.05,
            pos=(-0.4, 0, 0.43),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft
        )
        
        self.building_labels = {}
        y_pos = 0.3
        for b_type in BuildingType:
            label = DirectLabel(
                text=f"{b_type.name.replace('_', ' ').title()}: 0",
                scale=0.045,
                pos=(-0.4, 0, y_pos),
                parent=self.frame,
                frameColor=(0, 0, 0, 0),
                text_fg=(0.9, 0.9, 0.9, 1),
                text_align=TextNode.ALeft
            )
            self.building_labels[b_type] = label
            y_pos -= 0.055

    def update(self, turn, stats):
        self.turn_label["text"] = f"Turn: {turn}"
        self.settlements_label["text"] = f"Settlements: {stats['settlements']}"
        
        # Update counts for all building types
        for b_type in BuildingType:
            count = stats["buildings"].get(b_type, 0)
            name = b_type.name.replace('_', ' ').title()
            if b_type in self.building_labels:
                self.building_labels[b_type]["text"] = f"{name}: {count}"

    def toggle_visibility(self):
        if self.frame.is_hidden():
            self.frame.show()
        else:
            self.frame.hide()
