from cProfile import label
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMainWindow
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPen, QColor, QBrush, QPainterPath
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsPathItem, QGraphicsTextItem
from engine import BeamBullet, Game, RocketBullet, Unit,TowerSlot, VineBullet
import math
unit_display_set = {
    "grunt": ["lime", 12],
    "tank": ["red", 20],
    "fast": ["blue", 8]
}
tower_display_set = {
    "basic": "white",
    "rocketeer": "orange",
    "beam": "yellow",
    "vine": "green",
    "cluster": "black",
    "mini-cluster": "black"
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
        self._tower_labels = []
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
                label = QGraphicsTextItem()
                label.setDefaultTextColor(QColor("white"))
                font = label.font()
                font.setPointSize(8)
                label.setFont(font)
                self.scene.addItem(label)
                self._tower_labels.append(label)

        if len(self._towers) > len(self.engine.towers):
            while self._towers:
                self.scene.removeItem(self._towers.pop())
            while self._tower_labels:
                self.scene.removeItem(self._tower_labels.pop())
            
        
        _draw_towers()
        for it_tower, tower, label in zip(self._towers, self.engine.towers,self._tower_labels):
            it_tower.setPos(tower.x, tower.y)
            label.setPlainText(self._tower_info(tower))  # albo inline string
            br = label.boundingRect()
            label.setPos(tower.x - br.width() / 2, tower.y + r + 20)
            label.setZValue(100)   

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

        def _vine_path(b_x,b_y,b_t_x,b_t_y):
            t = self.engine.elapsed
            bend_fac = 0.22
            n_seg = 5

            dx = b_x - b_t_x
            dy = b_y - b_t_y
            dist = math.hypot(dx, dy)

            path = QPainterPath()
            path.moveTo(b_t_x, b_t_y)

            if dist < 1e-6:
                path.lineTo(b_x, b_y)
                return path

            perp_x = -dy / dist
            perp_y = dx / dist
            sag = bend_fac * dist
            print (t)
            for i in range(n_seg):
                t0 = i / n_seg
                t1 = (i + 1) / n_seg
                tm = (t0 + t1) / 2
                env = math.sin(math.pi * tm) ** 1.15
                wobble = 0.85 + 0.15 * (math.sin(t * 3.2 + i) * math.cos(t * 2.1))
                amp = sag * env * wobble
                cx = b_t_x + dx * tm + perp_x * amp
                cy = b_t_y + dy * tm + perp_y * amp
                ex = b_t_x + dx * t1
                ey = b_t_y + dy * t1
                path.quadTo(cx, cy, ex, ey)

            return path
        def _calc_rocket(bx, by, tx, ty, b_len):
            dx = tx - bx 
            dy = ty - by 
            v_len = math.hypot(dx,dy)
            ux = dx/v_len
            uy = dy/v_len
            return bx - ux * b_len, by - uy * b_len
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

                elif isinstance(bullet,VineBullet):
                    # parab
                
                    path = _vine_path(bullet.x,bullet.y,bullet.t_x,bullet.t_y)
                    rad = 3
                    c = QColor("green")
                    c.setAlpha(180)
                    item = QGraphicsPathItem(path)
                    pen = QPen(c,2* rad)
                    item.setPen(pen)
                    self.scene.addItem(item)
                    self._bullet_items[bullet] = item

                elif isinstance(bullet,RocketBullet):
                    bul_dict = {
                        "rocket": [2, 4, "red"],
                        "cluster": [3, 6, "black"],
                        "mini-cluster" : [2, 3, "black"]
                    }
                    bul_style = bul_dict[bullet.type]
                    c = QColor(bul_style[2])
                    c.setAlpha(180)
                    w = bul_style[0]
                    l = bul_style[1]


                    r_x, r_y = _calc_rocket(bullet.x,bullet.y,bullet.t_x,bullet.t_y,l)
                    item = QGraphicsLineItem(r_x,r_y,bullet.x,bullet.y)
                    pen = QPen(c,2* w)
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
            elif isinstance(bullet, VineBullet):
                path = _vine_path(bullet.x,bullet.y,bullet.t_x,bullet.t_y)
                item.setPath(path)

            elif isinstance(bullet,RocketBullet):
                r_x, r_y = _calc_rocket(bullet.x,bullet.y,bullet.t_x,bullet.t_y,3)
                item.setLine(r_x,r_y,bullet.x,bullet.y)

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
    
    def _tower_info(self,tower):
        bt = tower.bullet_type
        s = tower.get_stats()
        lines = [
            f"{s['type']}",
            f"D: {s['damage']} R: {s['range']} F: {s['fire_rate']:.1f} B: {bt}",
        ]
        if tower.pick_target == tower._pick_target_nearest:
            lines.append("T: nea")
        elif tower.pick_target == tower._pick_target_lowest_hp:
            lines.append("T: wea")
        elif tower.pick_target == tower._pick_target_highest_hp:
            lines.append("T: str")
        return "\n".join(lines)