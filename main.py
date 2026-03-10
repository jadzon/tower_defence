import sys
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget,QPushButton
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

        self.engine = Game()
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

        self.game_view.draw_debug_path()
        self.setWindowTitle("game")
        self.showFullScreen()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())