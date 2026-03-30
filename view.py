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
        for item, unit in zip(self._unit_items, self.engine.units):
            item.setPos(unit.x, unit.y)
            # print(f"Unit type: {unit.unit_type}")
            # print(f"Color: {unit_colors[unit.unit_type]}")
            c, r = unit_display_set[unit.unit_type] 
            item.setRect(-r, -r, 2 * r, 2 * r)
            item.setBrush(QBrush(QColor(c)))