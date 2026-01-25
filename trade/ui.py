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

class BuildingInfoUI:
    def __init__(self, parent):
        self.frame = DirectFrame(
            frameColor=(0, 0, 0, 0.8),
            frameSize=(-0.4, 0.4, -0.5, 0.5),
            pos=(1.1, 0, 0.3),
            parent=parent
        )
        self.frame.hide()
        
        self.title = DirectLabel(
            text="Building Info",
            scale=0.06,
            pos=(0, 0, 0.4),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter
        )
        
        self.type_label = DirectLabel(
            text="Type: -",
            scale=0.05,
            pos=(-0.35, 0, 0.3),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft
        )
        
        self.prod_title = DirectLabel(
            text="Production:",
            scale=0.045,
            pos=(-0.35, 0, 0.2),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(0.7, 1, 0.7, 1),
            text_align=TextNode.ALeft
        )
        self.prod_label = DirectLabel(
            text="-",
            scale=0.04,
            pos=(-0.3, 0, 0.13),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(0.9, 0.9, 0.9, 1),
            text_align=TextNode.ALeft
        )

        self.cons_title = DirectLabel(
            text="Consumption:",
            scale=0.045,
            pos=(-0.35, 0, 0.0),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 0.7, 0.7, 1),
            text_align=TextNode.ALeft
        )
        self.cons_label = DirectLabel(
            text="-",
            scale=0.04,
            pos=(-0.3, 0, -0.07),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(0.9, 0.9, 0.9, 1),
            text_align=TextNode.ALeft
        )

        self.inv_title = DirectLabel(
            text="Inventory:",
            scale=0.045,
            pos=(-0.35, 0, -0.2),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(0.7, 0.7, 1, 1),
            text_align=TextNode.ALeft
        )
        self.inv_label = DirectLabel(
            text="-",
            scale=0.04,
            pos=(-0.3, 0, -0.27),
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            text_fg=(0.9, 0.9, 0.9, 1),
            text_align=TextNode.ALeft
        )

        self.current_building = None

    def show(self, building, config):
        self.current_building = building
        self.refresh(config)
        self.frame.show()

    def hide(self):
        self.current_building = None
        self.frame.hide()

    def refresh(self, config):
        if not self.current_building:
            return
            
        b = self.current_building
        name = b.type.name.replace('_', ' ').title()
        if b.type == BuildingType.MINE and b.primary_resource:
            name = f"{b.primary_resource.name.title()} Mine"
            
        self.type_label["text"] = f"Type: {name}"
        
        # Production
        prod = b.get_production_rates(config)
        prod_text = "\n".join([f"{res.name}: {rate:.2f}/turn" for res, rate in prod.items()])
        self.prod_label["text"] = prod_text if prod_text else "None"
        
        # Consumption
        cons = b.get_consumption_rates(config)
        cons_text = "\n".join([f"{res.name}: {rate:.2f}/turn" for res, rate in cons.items()])
        self.cons_label["text"] = cons_text if cons_text else "None"
        
        # Inventory
        inv_text = "\n".join([f"{res.name}: {amt}" for res, amt in b.inventory.items() if amt != 0])
        self.inv_label["text"] = inv_text if inv_text else "Empty"
