from random import randint
import sys
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import *

class Tiles:
    def __init__(self,pixmap,tsizex,tsizey):
        self.pixmap = pixmap
        self.tsizex = tsizex
        self.tsizey = tsizey
        self.tiles = {}

    def addTile(self,key,i,j):
        self.tiles[key] = self.pixmap.copy(
                j*self.tsizex, i*self.tsizey, self.tsizex, self.tsizey)

    def getTile(self,key):
        return self.tiles[key]

class Keys:
    HIDDEN = 0
    FLAGGED = 1
    MINE = 2
    PRESSED = 3
    RADAR = { 0:3, 1:4, 2:5, 3:6, 4:7, 5:8, 6:9, 7:10, 8:11 }

class Box(QGraphicsPixmapItem):
    def __init__(self, pixmap):
        super(Box, self).__init__()
        self.key = Keys.HIDDEN
        self.shown = 1
        self.mine = False
        self.radar = 0
        self.setPixmap(pixmap)

    def setKey(self, key, pixmap):
        self.key = key
        self.setPixmap(pixmap)

    def getKey(self):
        return self.key

class Board(QGraphicsScene):
    def __init__(self, tilemap_path, tsizex, tsizey, rows, columns,
            nmines, parent=None):
        super(Board, self).__init__()

        # Init tiles
        self.tsizex = tsizex # Size of single tile
        self.tsizey = tsizey
        self.tiles = Tiles(QPixmap(tilemap_path),tsizex,tsizey)
        self._initTiles()

        self.initBoard(rows,columns,nmines)

    # Init all tiles
    def _initTiles(self):
        for i in range(12):
            self.tiles.addTile(i, int(i/4), int(i%4))

    # Initialize board. This method will also be called from outside.
    def initBoard(self, rows, columns, nmines):
        self.clear()
        self.setSceneRect(QRectF(0.0, 0.0, float(self.tsizex*columns), float(self.tsizey*rows)))

        self.rows = rows
        self.columns = columns
        self.nmines = nmines

        tileh = self.tiles.getTile(Keys.HIDDEN)
        self.board = [[Box(tileh) for i in range(self.columns)] for j in \
                range(self.rows)]
        self._initScene()

        self.begin = True

        self.pressed = False
        self.pressed2 = False

        self.secure = False

    # Add all boxes to the graphics scene
    def _initScene(self):
        for i in range(self.rows):
            for j in range(self.columns):
                self.board[i][j].setOffset(j*self.tsizex,i*self.tsizey)
                self.addItem(self.board[i][j])

    # Distributes mines randomly in board
    def _initMines(self, i, j):
        rest = self.nmines
        # Wraps matrix in one dimensional list
        indices = [k for k in range(self.rows * self.columns) if not(
                i-1 <= int(k/self.columns) <= i+1 and j-1 <= k%self.columns <= j+1)]
        while rest != 0:
            ind = indices.pop(randint(0,len(indices)-1))
            self.board[int(ind/self.columns)][ind%self.columns].mine = True
            rest -= 1

    # After distributing, calculates the radar on each box
    def _calcRadar(self):
        for i in range(0,self.rows):
            for j in range(0,self.columns):
                k = 0
                for y in range(max(0,i-1),min(self.rows,i+2)):
                    for x in range(max(0,j-1),min(self.columns,j+2)):
                        if not (y == i and x == j) and self.board[y][x].mine:
                            k += 1
                self.board[i][j].radar = k

    # MOUSE ACTIONS
    # - self.pressed   : left click being pressed
    # - self.pressed2  : right click being pressed
    # - self.hoverItem : previous box being pointed by the cursor
    # - self.secure    : dissables left click action

    def mousePressEvent(self, event):
        # Left click
        if event.button() == Qt.LeftButton:
            self.pressed = True
            pos = event.scenePos()
            item = self.itemAt(pos, QTransform())
            self.hoverItem = item
            if item is not None and item.shown == 1:
                tile = self.tiles.getTile(Keys.PRESSED)
                item.setKey(Keys.PRESSED, tile)

        # Right click
        elif event.button() == Qt.RightButton:
            self.pressed2 = True
            if not self.pressed:
                pos = event.scenePos()
                i = int(pos.y()/self.tsizey)
                j = int(pos.x()/self.tsizex)
                item = self.board[i][j]
                if item.shown != 0:
                    # Flags or unflags the box
                    if item.getKey() == Keys.FLAGGED:
                        tile = self.tiles.getTile(Keys.HIDDEN)
                        item.setKey(Keys.HIDDEN, tile)
                        item.shown = 1
                    else:
                        tile = self.tiles.getTile(Keys.FLAGGED)
                        item.setKey(Keys.FLAGGED, tile)
                        item.shown = 2

    # Checks if the box pointed by the cursor has changed
    def mouseMoveEvent(self, event):
        if self.pressed:
            pos = event.scenePos()
            item = self.itemAt(pos, QTransform())
            if self.hoverItem != item:
                # Changes previously pressed box to unpressed
                if self.hoverItem.shown == 1:
                    tileh = self.tiles.getTile(Keys.HIDDEN)
                    self.hoverItem.setKey(Keys.HIDDEN,tileh)
                if item.shown == 1:
                    tilep = self.tiles.getTile(Keys.PRESSED)
                    item.setKey(Keys.PRESSED,tilep)
                self.hoverItem = item

    def mouseReleaseEvent(self, event):
        pos = event.scenePos()
        i = int(pos.y()/self.tsizey)
        j = int(pos.x()/self.tsizex)

        if not self.pressed2 and event.button() == Qt.LeftButton:
            self.pressed = False
            # Secure makes sure that no action can be triggered by left click
            if not self.secure:
                self._openBox(i,j)
            elif self.board[i][j].shown == 1:
                self.secure = False
                # Simply unpress that box
                tile = self.tiles.getTile(Keys.HIDDEN)
                self.board[i][j].setKey(Keys.HIDDEN,tile)

        elif not self.pressed and event.button() == Qt.RightButton:
            self.pressed2 = False

        elif self.pressed and self.pressed2 and (
                event.button() == Qt.LeftButton or event.button() == Qt.RightButton):

            # Which of the buttons has been released
            if event.button() == Qt.LeftButton:
                self.pressed = False
                if self.board[i][j].shown == 1:
                    # Simply unpress that box
                    tilep = self.tiles.getTile(Keys.HIDDEN)
                    self.board[i][j].setKey(Keys.HIDDEN,tilep)
            elif event.button() == Qt.RightButton:
                # Enters secure mode
                self.secure = True
                self.pressed2 = False

            # Open boxes expanded
            self._openMultiple(i,j)

    def _openBox(self, i, j):
        item = self.board[i][j]
        if item.shown == 1:
            # Game begins, first click
            if self.begin:
                self._initMines(i,j)
                self._calcRadar()
                self.begin = False

            # Dig box
            if item.mine:
                # Player looses
                item.shown = 0
                tilep = self.tiles.getTile(Keys.MINE)
                item.setKey(Keys.MINE,tilep)
                dialog = QDialog()
                layout = QVBoxLayout()
                layout.addWidget(QLabel("NOOO LA CONCHETUMARE WEON KE ISISTE!!!!111"))
                dialog.setLayout(layout)
                dialog.exec()
            else:
                self._expand(i,j)

    # Recursive function to open boxes around a radar whose value is zero
    def _expand(self, i, j):
        item = self.board[i][j]
        item.shown = 0
        radar = item.radar
        tilep = self.tiles.getTile(Keys.RADAR[radar])
        item.setKey(Keys.RADAR[radar], tilep)
        if radar == 0:
            for y in range(max(0,i-1),min(self.rows,i+2)):
                for x in range(max(0,j-1),min(self.columns,j+2)):
                    if not (y == i and x == j) and self.board[y][x].shown == 1:
                        self._expand(y,x)

    # Open all boxes around one given
    def _openMultiple(self, i, j):
        if self.board[i][j].shown == 0:
            # Counts the number of flagged boxes
            flags = 0
            for y in range(max(0,i-1),min(self.rows,i+2)):
                for x in range(max(0,j-1),min(self.columns,j+2)):
                    if self.board[y][x].shown == 2:
                        flags += 1
            # If equals radar, open all boxes around that box
            if flags == self.board[i][j].radar:
                for y in range(max(0,i-1),min(self.rows,i+2)):
                    for x in range(max(0,j-1),min(self.columns,j+2)):
                        self._openBox(y,x)

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        # Niveles de dificultad
        self.nivel = 3 # Nivel por defecto (Principiante = 1, Avanzado = 2, Experto = 3)
        self.filas = {1:8,2:16,3:16}
        self.columnas = {1:8,2:16,3:30}
        self.minas = {1:10,2:40,3:99}

        # Menú desplegable
        self.menu = self.menuBar()
        self.difi = self.menu.addMenu("Dificultad")

        self.prin = QAction("Principiante",self)
        self.avan = QAction("Avanzado",self)
        self.expe = QAction("Experto",self)

        self.prin.triggered.connect(lambda: self.cambiarDificultad(1))
        self.avan.triggered.connect(lambda: self.cambiarDificultad(2))
        self.expe.triggered.connect(lambda: self.cambiarDificultad(3))

        self.difi.addAction(self.prin)
        self.difi.addAction(self.avan)
        self.difi.addAction(self.expe)

        # Widgets
        self.button = QPushButton("Reiniciar")
        self.button.clicked.connect(self.reiniciarPartida)
        self.board = Board("tiles.png", 24, 24,
                self.filas[self.nivel], self.columnas[self.nivel], self.minas[self.nivel], self)
        self.view = QGraphicsView(self.board)
        self.view.resize(self.view.sceneRect().size().toSize())
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.view)

        self.widget = QWidget()
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

    def cambiarDificultad(self,dificultad):
        self.nivel = dificultad
        self.board.initBoard(self.filas[dificultad], self.columnas[dificultad], self.minas[dificultad])

    def reiniciarPartida(self):
        self.board.initBoard(self.filas[self.nivel], self.columnas[self.nivel], self.minas[self.nivel])

if __name__ == '__main__':
    app = QApplication([])

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
