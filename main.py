import sys
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout,QLabel, QWidget,QPushButton, QMenu
from PyQt6.QtCore import QTimer, pyqtSignal ,Qt
from PyQt6.QtGui import QCursor, QAction
from engine import Game, TowerSlot, UpgradeSpec
from view import GameView
import math
import argparse
from client import Client
import json



_SPEED_LEVELS = (1, 2, 5, 10)



class ControlPanel(QWidget):

    pause_clicked = pyqtSignal()
    restart_clicked = pyqtSignal()

    def __init__(self,speed_idx, parent=None):
        super().__init__(parent)
        v_lay = QVBoxLayout(self)
        h_lay = QHBoxLayout()
        self._speed_idx = speed_idx
        self._gold = QLabel("Gold")
        self._hp = QLabel("HP")
        self._round = QLabel("Round")
        self._elapsed = QLabel("Elapsed")
        self._pause_btn = QPushButton("||")
        self._speed_btn = QPushButton("x1")
        self._restart_btn = QPushButton("rst")
        self._pause_btn.clicked.connect(self.pause_clicked.emit)
        self._restart_btn.clicked.connect(self.restart_clicked.emit)
        self._speed_btn.clicked.connect(self._cycle_speed)
        v_lay.addWidget(self._gold)
        v_lay.addWidget(self._hp)
        v_lay.addWidget(self._round)
        v_lay.addWidget(self._elapsed)
        h_lay.addWidget(self._restart_btn)
        h_lay.addWidget(self._pause_btn)
        h_lay.addWidget(self._speed_btn)
        v_lay.addLayout(h_lay)

    def speed_multiplier(self) -> int:
        return _SPEED_LEVELS[self._speed_idx]
    
    def _cycle_speed(self) -> None:
        self._speed_idx = (self._speed_idx + 1) % len(_SPEED_LEVELS)
        m = _SPEED_LEVELS[self._speed_idx]
        self._speed_btn.setText(f"x{m}")
    
    def set_gold(self, n: int) -> None:
        self._gold.setText(f"Gold: {n}")

    def set_round(self, n:int) -> None:
        self._round.setText(f"Round: {n}")

    def set_elapsed(self, n:int) -> None:
        self._elapsed.setText(f"Elapsed: {n:.0f}")
    
    def set_hp(self, n:int) -> None:
        self._hp.setText(f"HP: {n}")
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
    def __init__(self, engine):
        super().__init__()
        _HOST = '127.0.0.1'
        _PORT = 8080
        self.engine: Game = engine
        self.wsclient = Client(_HOST,_PORT)
        self.wsclient.start()
        self.game_view = GameView(self.engine)
        self.game_view.slot_clicked.connect(self._on_slot_clicked)
        self.control_panel = ControlPanel(self.engine.game_speed)
        self.setCentralWidget(GameContainer(self.game_view, self.control_panel))
        self._paused = False
        
        self._tick_ms = 16 
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_game_tick)
        self._timer.start(self._tick_ms)

        self.game_view.draw_debug_path()
        self.setWindowTitle("game")
        self.showFullScreen()
        self.control_panel.pause_clicked.connect(self._toggle_pause)
        self.control_panel.restart_clicked.connect(self._on_restart)
        self._on_game_tick()
        self._toggle_pause()
        
    
    def _on_restart(self):
        self.engine._load_game_config()
        self._paused = True
        self._timer.stop()
        self.control_panel.set_gold(self.engine.gold)
        self.game_view.sync_tower_slots()
        self.game_view.sync_towers()
        self.game_view.sync_bullets()
        self.game_view.sync_units()
        self.game_view.draw_debug_path()          
        self.game_view.update() 

    def _test_send_turret_pos(self):
        tows = self.engine.towers
        t_poss = []
        for t in tows:
            t_pos = (t.x,t.y)
            t_poss.append(t_pos)
        mes = json.dumps(t_poss)
        self.wsclient.send_message(mes)

    def _on_game_tick(self):
        dt = self._tick_ms / 1000.0 * self.control_panel.speed_multiplier()
        self.engine.tick(dt)
        self.game_view.sync_tower_slots()
        self.game_view.sync_towers()
        if not self._paused:
            self.game_view.sync_bullets()
            self.game_view.sync_units()
        self.control_panel.set_gold(self.engine.gold)
        self.control_panel.set_hp(self.engine.hp)
        self.control_panel.set_round(self.engine.round_index)
        self.control_panel.set_elapsed(self.engine.elapsed)
        self._test_send_turret_pos()

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._timer.stop()
        else:
            self._timer.start(self._tick_ms)

    def _on_slot_clicked(self, slot: TowerSlot):

        self.game_view.set_menu_range_tower(None)
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
            self.game_view.set_menu_range_tower(tower)
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
                "furthest"
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
                cat = spec.kind if spec.kind == "bullet" else spec.type
                label = f"{cat}: {spec.label}  ({cost} gold)"
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
                self.game_view.set_menu_range_tower(None)
                return
            data = chosen.data()
            if data == "sell":
                self.engine.sell_tower(slot)
                self._on_game_tick()
                self.game_view.set_menu_range_tower(None)
                return
            elif isinstance(data, tuple) and len(data) == 2 and data[0] == "target":
                tower.change_targeting_strategy(data[1])
            elif isinstance(data, UpgradeSpec):
                self.engine.apply_upgrade(tower, data)
        
        self.game_view.set_menu_range_tower(None)
        self._on_game_tick()




if __name__ == "__main__":
    app = QApplication(sys.argv)
    e = Game() 
    window = MainWindow(e)
    sys.exit(app.exec())