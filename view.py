from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMainWindow
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPen, QColor, QBrush
from PyQt6.QtWidgets import QGraphicsEllipseItem
from engine import Game, Unit
unit_display_set = {
    "grunt": ["lime", 12],
    "tank": ["red", 20],
    "fast": ["blue", 8]
}
class GameView(QGraphicsView):
    def __init__(self, game_engine):
        super().__init__()
        self.engine = game_engine

        self.scene = QGraphicsScene(0, 0, 1600,900)
        self.setScene(self.scene)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._unit_items = []
        self._towers = []
        self._tower_slots= []
        self._radius = 12
    
    def setFullScreen(self,event):
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def draw_debug_path(self):
        pen = QPen(QColor("red"), 5)
        drawn = set()

        for node in self.engine.nodes:
            x1, y1 = node.x, node.y
            for neighbor in node.neighbors:
                key = tuple(sorted((id(node), id(neighbor))))
                if key in drawn:
                    continue
                drawn.add(key)
                self.scene.addLine(x1, y1, neighbor.x, neighbor.y, pen)
                print(f"Drawing {neighbor}")
    

    def _ensure_unit_graphics(self):
        r = self._radius
        while len(self._unit_items) < len(self.engine.units):
            item = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
            item.setBrush(QBrush(QColor("lime")))
            self.scene.addItem(item)
            self._unit_items.append(item)

    def sync_units(self):
        self._ensure_unit_graphics()
        while len(self._unit_items) > len(self.engine.units):
            item = self._unit_items.pop()
            self.scene.removeItem(item)
            
        for item, unit in zip(self._unit_items, self.engine.units):
            item.setPos(unit.x, unit.y)
            # print(f"Unit type: {unit.unit_type}")
            # print(f"Color: {unit_colors[unit.unit_type]}")
            c, r = unit_display_set[unit.unit_type] 
            item.setRect(-r, -r, 2 * r, 2 * r)
            item.setBrush(QBrush(QColor(c)))
    
    def sync_towers(self):
        r = self._radius
        while len(self._towers) < len(self.engine.towers):
            item = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
            item.setBrush(QBrush(QColor("white")))
            self.scene.addItem(item)
            self._towers.append(item)
        
        for item, tower in zip(self._towers, self.engine.towers):
            item.setPos(tower.x,tower.y)

    def sync_tower_slots(self):
        r = 15
        while len(self._tower_slots) < len(self.engine.tower_slots):
            item = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
            item.setBrush(QBrush(QColor("black")))
            self.scene.addItem(item)
            self._tower_slots.append(item)
        
        for item, t_slot in zip(self._tower_slots, self.engine.tower_slots):
            item.setPos(t_slot.x,t_slot.y)