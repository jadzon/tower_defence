import sys
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout,QLabel, QWidget,QPushButton, QMenu
from PyQt6.QtCore import QTimer, pyqtSignal ,Qt
from PyQt6.QtGui import QCursor, QAction
from engine import Game, TowerSlot, UpgradeSpec
from view import GameView
import math

class ControlPanel(QWidget):
    pause_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        self._gold = QLabel("Gold")
        self._btn = QPushButton("||")
        self._btn.clicked.connect(self.pause_clicked.emit)
        lay.addWidget(self._gold)
        lay.addWidget(self._btn)
    
    def set_gold(self, n: int) -> None:
        self._gold.setText(f"Gold: {n}")

class GameContainer(QWidget):
    def __init__(self,game_view,ui,margin=16):
        super().__init__()
        self._game_view = game_view
        self._ui = ui
        self._margin = margin
        game_view.setParent(self)
        ui.setParent(self)
        ui.raise_()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(),self.height()
        self._game_view.setGeometry(0, 0, w, h)
        self._ui.adjustSize()
        x = max(0, w - self._ui.width() - self._margin)
        y = max(0, h - self._ui.height() - self._margin)
        self._ui.move(x, y)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.engine: Game = Game()
        self.game_view = GameView(self.engine)
        self.game_view.slot_clicked.connect(self._on_slot_clicked)
        self.control_panel = ControlPanel()
        self.setCentralWidget(GameContainer(self.game_view, self.control_panel))
        self._paused = False
        # game settings
        self._tick_ms = 16 
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_game_tick)
        self._timer.start(self._tick_ms)

        self.game_view.draw_debug_path()
        self.setWindowTitle("game")
        self.showFullScreen()
        self.control_panel.pause_clicked.connect(self._toggle_pause)
        
        self._on_game_tick()
        self._toggle_pause()
        
    
    def _on_game_tick(self):
        dt = self._tick_ms / 1000.0
        self.engine.tick(dt)
        self.game_view.sync_tower_slots()
        self.game_view.sync_towers()
        self.game_view.sync_bullets()
        self.game_view.sync_units()
        self.control_panel.set_gold(self.engine.gold)
    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._timer.stop()
        else:
            self._timer.start(self._tick_ms)
    # opcjonalnie: self.control_panel.set_paused(self._paused)  # zmiana napisu na przycisku
    def _on_slot_clicked(self, slot: TowerSlot):
        menu = QMenu(self)
        if not slot.occupied:

            for tower_type, cost in self.engine.tower_costs.items():
                label = f"{tower_type} ({cost} gold)"
                act = QAction(label, self)
                act.setData(tower_type)
                menu.addAction(act)

            chosen = menu.exec(QCursor.pos())
            if chosen is None:
                return
            tower_type = chosen.data()
            self.engine.buy_tower(slot, tower_type)
        
        else:
            tower = slot.tower
            if tower is None:
                return
            menu = QMenu(self)
            refund = math.trunc(
                self.engine.tower_costs[tower.tower_type]
                     * self.engine.tower_sell_return_ratio
                        )
            sell_act = QAction(f"Sell (+{refund} gold)", self)
            sell_act.setData("sell")
            menu.addAction(sell_act)
            strategy_menu = QMenu("targeting strategy", self)
            for key in (
                "nearest",
                "weakest",
                "strongest",
            ):
                a = QAction(key, self)
                a.setData(("target", key))
                strategy_menu.addAction(a)
            menu.addMenu(strategy_menu)
            upgrade_menu = QMenu("upgrade",self)
            for spec in tower.possible_upgrades():
                cost = self.engine.upgrade_cost(tower, spec)
                if cost is None:
                    cost = 0
                label = f"{spec.type}: {spec.label}  ({cost} gold)"
                act = QAction(label, self)
                act.setData(spec)
                act.setEnabled(cost <= self.engine.gold)
                upgrade_menu.addAction(act)
                if upgrade_menu.actions():
                    menu.addMenu(upgrade_menu)
            if upgrade_menu.actions():
                menu.addMenu(upgrade_menu)
            chosen = menu.exec(QCursor.pos())
            if chosen is None:
                return
            data = chosen.data()
            if data == "sell":
                self.engine.sell_tower(slot)
                return
            elif isinstance(data, tuple) and len(data) == 2 and data[0] == "target":
                tower.change_targeting_strategy(data[1])
            elif isinstance(data, UpgradeSpec):
                self.engine.apply_upgrade(tower, data)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())