import sys
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget,QPushButton
from PyQt6.QtCore import QTimer
from engine import Game
from view import GameView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout= QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setSpacing(0)

        self.engine: Game = Game()
        self.game_view = GameView(self.engine)
        self.main_layout.addWidget(self.game_view)

        self.bottom_bar_widget = QWidget()
        self.bottom_bar_widget.setFixedHeight(120)
        self.bottom_bar_widget.setStyleSheet("background-color: White;")
        self.bottom_bar_layout = QHBoxLayout(self.bottom_bar_widget)

        self.btn = QPushButton("kup wieze")
        self.btn.setStyleSheet("background-color: Black;")
        self.bottom_bar_layout.addWidget(self.btn)

        self.main_layout.addWidget(self.bottom_bar_widget)

        # game settings
        self._tick_ms = 16 
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_game_tick)
        self._timer.start(self._tick_ms)

        self.game_view.draw_debug_path()
        self.setWindowTitle("game")
        self.showFullScreen()
    
    def _on_game_tick(self):
        dt = self._tick_ms / 1000.0
        self.engine.tick(dt)
        self.game_view.sync_tower_slots()
        self.game_view.sync_towers()
        self.game_view.sync_bullets()
        self.game_view.sync_units()
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())