import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui, uic
import pyqtgraph as pg

import matplotlib.pyplot as plt

class ColorbarWidget(pg.GraphicsWidget):
    sigChanged = QtCore.pyqtSignal()
    sigUserChanged = QtCore.pyqtSignal()
    
    def __init__(self, parent=None, cmap=None):
        pg.GraphicsWidget.__init__(self, parent)
        
        if cmap is None:
            cmap = plt.get_cmap("viridis")
        
        self.cmap = cmap
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        self.layout = QtWidgets.QGraphicsGridLayout()
        self.layout.setContentsMargins(1,1,1,1)
        self.setLayout(self.layout)
        self.layout.setHorizontalSpacing(0)
        self.layout.setVerticalSpacing(0)
        
        self.vb = pg.ViewBox(enableMenu=False)
        self.item = ColorbarTickSliderItem(allowAdd=False, allowRemove=False)
        self.vb.sigXRangeChanged.connect(self.item.updateRange)
        
        self.axis = pg.AxisItem(orientation='top', linkView=self.vb, maxTickLength=-10)
        self.axis.setStyle(tickAlpha=200)
        
        self.layout.addItem(self.axis, 0, 1)
        
        self.vb.setFixedHeight(10)
        self.layout.addItem(self.vb, 1, 1)
        
        self.gradient = ColorbarGradientWidget(self.vb, self.axis, self.item, self.cmap)
        self.layout.addItem(self.gradient, 2, 1)
        
        self.layout.addItem(self.item, 3, 1)
        
        self.item.sigTicksChanged.connect(self.sigChanged.emit)
        self.item.sigUserChanged.connect(self.sigUserChanged.emit)
    
    def setLevels(self, left=None, right=None):
        if left is not None:
            self.item.left_tick_pos = left
        
        if right is not None:
            self.item.right_tick_pos = right
        
        self.item.rescaleTicks()
    
    def setCmap(self, cmap):
        self.cmap = cmap
        self.gradient.setCmap(cmap)
    
    def getLevels(self):
        return self.item.left_tick_pos, self.item.right_tick_pos
    
    def setRange(self, *args, **kwargs):
        self.vb.setRange(*args, **kwargs)

class ColorbarTickSliderItem(pg.TickSliderItem):
    sigUserChanged = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwds):
        pg.TickSliderItem.__init__(self, *args, **kwds)
        self.left_tick = self.addTick(0)
        self.right_tick = self.addTick(1)
        
        self.left_tick_pos = 0
        self.right_tick_pos = 1
        
        self._range = [0,1]
        
        self.sigUserChanged.connect(self.updateTicks)
    
    def showEvent(self, ev):
        """
        Post-init code to execute when widget is shown
        """
        self.rescaleTicks()
        self.resizeEvent = self.resizeEventHandler
    
    def getTickValueFromRange(self, tick, viewRange):
        origin = self.tickSize/2.
        length = self.length
        
        lengthIncludingPadding = length + self.tickSize + 2
        
        tickValueIncludingPadding = (self.tickValue(tick) * length + origin) / lengthIncludingPadding
        pos = tickValueIncludingPadding * (viewRange[1] - viewRange[0]) + viewRange[0]
        
        return pos
    
    def setTickValueFromRange(self, pos, tick, viewRange):
        origin = self.tickSize/2.
        length = self.length

        lengthIncludingPadding = length + self.tickSize + 2
        
        tickValueIncludingPadding = (pos - viewRange[0]) / (viewRange[1] - viewRange[0])
        tickValue = (tickValueIncludingPadding*lengthIncludingPadding - origin) / length
        
        self.setTickValue(tick, tickValue)
    
    def updateRange(self, vb, viewRange):
        self._range = viewRange
        
        self.rescaleTicks()
    
    def rescaleTicks(self):
        self.setTickValueFromRange(self.left_tick_pos, self.left_tick, self._range)
        self.setTickValueFromRange(self.right_tick_pos, self.right_tick, self._range)
    
    def setTickValue(self, tick, val):
        """
        Allow to set tick value outside visible range
        """
        tick = self.getTick(tick)
        x = val * self.length
        pos = tick.pos()
        pos.setX(x)
        tick.setPos(pos)
        self.ticks[tick] = val
        
        self.sigTicksChanged.emit(self)
        self.sigTicksChangeFinished.emit(self)
    
    def tickMoved(self, tick, pos):
        """
        Allow to move tick outside visible range
        """
        newX = pos.x()
        pos.setX(newX)
        tick.setPos(pos)
        self.ticks[tick] = float(newX) / self.length
        
        self.sigTicksChanged.emit(self)
        self.sigUserChanged.emit()
    
    def updateTicks(self):
        self.left_tick_pos = self.getTickValueFromRange(self.left_tick, self._range)
        self.right_tick_pos = self.getTickValueFromRange(self.right_tick, self._range)
    
    def resizeEventHandler(self, ev):
        pg.TickSliderItem.resizeEvent(self, ev)
        self.rescaleTicks()
        

class ColorbarGradientWidget(pg.GraphicsWidget):
    def __init__(self, viewBox, axis, tickSlider, cmap):
        pg.GraphicsWidget.__init__(self)
        
        self.setFixedHeight(20)
        
        self.picture = None
        
        self.viewBox = viewBox
        self.axis = axis
        self.tickSlider = tickSlider
        
        self.viewBox.sigXRangeChanged.connect(self.linkedViewChanged)
        self.tickSlider.sigTicksChanged.connect(self.ticksChanged)
        
        self.cmap = cmap
    
    def paint(self, p, *args):
        if self.picture is None:
            try:
                picture = QtGui.QPicture()
                painter = QtGui.QPainter(picture)
                bounds = self.mapRectFromParent(self.geometry())
                
                width = int(bounds.width())
                height = int(bounds.height())
                image = QtGui.QImage(width, 1, QtGui.QImage.Format_RGB32)
                _min, _max = self.axis.range
                
                _from = self.tickSlider.left_tick_pos
                _to = self.tickSlider.right_tick_pos
                for i in range(width):
                    curr_val = i/width*(_max-_min)+_min
                    
                    curr_val = (curr_val - _from) / (_to - _from)
                    
                    if curr_val > 0 and curr_val < 1:
                        r, g, b, a = self.cmap(curr_val)
                        image.setPixel(i, 0, 0xff000000 + int(r*0xff)*0x00010000 + int(g*0xff)*0x00000100 + int(b*0xff)*0x00000001)
                    else:
                        image.setPixel(i, 0, 0xff000000)
                painter.drawImage(bounds, image, QtCore.QRectF(0, 0, width, 1))
            finally:
                painter.end()
            self.picture = picture
        #p.setRenderHint(p.Antialiasing, False)   ## Sometimes we get a segfault here ???
        #p.setRenderHint(p.TextAntialiasing, True)
        self.picture.play(p)
    
    def resizeEvent(self, ev=None):
        self.picture = None
    
    def linkedViewChanged(self, view, newRange=None):
        self.picture = None
        self.update()
    
    def wheelEvent(self, ev):
        self.viewBox.wheelEvent(ev)

    def mouseDragEvent(self, ev):
        self.viewBox.mouseDragEvent(ev)
    
    def ticksChanged(self, *args, **kwargs):
        self.picture = None
        self.update()
    
    def setCmap(self, cmap):
        self.cmap = cmap
        self.picture = None
        self.update()

if __name__ == "__main__":
    app = pg.mkQApp()

    gw = pg.GraphicsView()
    pi = ColorbarWidget()
    gw.setCentralItem(pi)
    gw.show()

    app.exec_()
