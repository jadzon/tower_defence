from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMainWindow
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPen, QColor

class GameView(QGraphicsView):
    def __init__(self, game_engine):
        super().__init__()
        self.engine = game_engine

        self.scene = QGraphicsScene(0, 0, 1600,900)
        self.setScene(self.scene)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    def setFullScreen(self,event):
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def draw_debug_path(self):
        pen = QPen(QColor("red"), 5)
        path = self.engine.waypoints
        for i in range(len(path) - 1):
            self.scene.addLine(path[i][0], path[i][1], path[i+1][0], path[i+1][1], pen)