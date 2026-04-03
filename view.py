from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMainWindow
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPen, QColor, QBrush
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem
from engine import BeamBullet, Game, Unit,TowerSlot
unit_display_set = {
    "grunt": ["lime", 12],
    "tank": ["red", 20],
    "fast": ["blue", 8]
}
tower_display_set = {
    "basic": "white",
    "rocketeer": "orange",
    "beam": "yellow"
}
bullet_display_set = {
    "tier1": "white",
    "tier2": "blue"
}
class GameView(QGraphicsView):
    slot_clicked = pyqtSignal(object)
    def __init__(self, game_engine):
        super().__init__()
        self.engine = game_engine

        self.scene = QGraphicsScene(0, 0, 1600,900)
        self.setScene(self.scene)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._unit_items = {}
        self._towers = []
        self._tower_slots= []
        self._radius = 12
        self._bullet_items = {}
    
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
    

    def sync_units(self):
       
        #1. remove unit items that dont exist
        current_units = set(self.engine.units)
        to_remove = [u for u in self._unit_items if u not in current_units]
        for u in to_remove:
            item = self._unit_items.pop(u)
            self.scene.removeItem(item)

        #2. create new unit graphics
        for unit in self.engine.units:
            if unit not in self._unit_items:
                c,r = unit_display_set[unit.unit_type]
                item = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
                item.setBrush(QBrush(QColor(c)))
                self.scene.addItem(item)
                self._unit_items[unit] = item

        #3. update pos + update render
        for unit in self.engine.units:
            item = self._unit_items[unit]
            c,r = unit_display_set[unit.unit_type]
            item.setRect(-r, -r, 2 * r, 2 * r)
            item.setBrush(QBrush(QColor(c)))
            item.setPos(unit.x, unit.y)

    
    def sync_towers(self):
        r = self._radius
        def _draw_towers():
            while len(self._towers) < len(self.engine.towers):
                item = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
                item.setBrush(QBrush(QColor("white")))
                self.scene.addItem(item)
                self._towers.append(item)

        if len(self._towers) > len(self.engine.towers):
            t_len = len(self._towers)
            for t in range(t_len):
                self.scene.removeItem(self._towers.pop())
            self._towers = []
        
        _draw_towers()
        for item, tower in zip(self._towers, self.engine.towers):
            item.setPos(tower.x, tower.y)
            

        
        
        

    def sync_tower_slots(self):
        r = 15
        while len(self._tower_slots) < len(self.engine.tower_slots):
            item = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
            item.setBrush(QBrush(QColor("black")))
            self.scene.addItem(item)
            self._tower_slots.append(item)
        
        for item, t_slot in zip(self._tower_slots, self.engine.tower_slots):
            item.setPos(t_slot.x,t_slot.y)
            item.setData(0,t_slot)
            item.setAcceptHoverEvents(True)
    
    def sync_bullets(self):
         #1. remove bullet items that dont exist
        current_bullets = set(self.engine.bullets)
        to_remove = [b for b in self._bullet_items if b not in current_bullets]
        for b in to_remove:
            item = self._bullet_items.pop(b)
            self.scene.removeItem(item)

        #2. create new bullet graphics
        for bullet in self.engine.bullets:
            if bullet not in self._bullet_items:
                if isinstance(bullet,BeamBullet):
                    c = QColor("orange")
                    c.setAlpha(180)
                    item = QGraphicsLineItem(bullet.t_x,bullet.t_y,bullet.x,bullet.y)
                    pen = QPen(c,2* bullet.beam_radius)
                    item.setPen(pen)
                    self.scene.addItem(item)
                    self._bullet_items[bullet] = item


                else: 
                    c = QColor("white")
                    r = 5
                    item = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
                    item.setBrush(QBrush(QColor(c)))
                    self.scene.addItem(item)
                    self._bullet_items[bullet] = item

        #3. update pos + update render
        for bullet in self.engine.bullets:
            item = self._bullet_items[bullet]
            if isinstance(bullet,BeamBullet):
                item.setLine(bullet.t_x, bullet.t_y, bullet.x, bullet.y)
            else:
                item.setPos(bullet.x, bullet.y)
    
    def mousePressEvent(self, event):
        if event is None:
            return
        p = self.mapToScene(event.position().toPoint())
        for it in self.scene.items(p):
            d =it.data(0)
            if isinstance(d,TowerSlot):
                self.slot_clicked.emit(d)
                return
        super().mousePressEvent(event)