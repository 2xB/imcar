import numpy as np

from pyqtgraph.Qt import QtGui, QtCore, QT_LIB
import pyqtgraph as pg

import matplotlib.pyplot as plt

class RegionIndicatorWidget(pg.GraphicsWidget):
    def __init__(self, vb, linearRegionItem, color):
        pg.GraphicsWidget.__init__(self)
        
        self.setFixedHeight(12)
        
        self.vb = vb
        self.vb.sigXRangeChanged.connect(self.update)
        self.linearRegionItem = linearRegionItem
        self.linearRegionItem.sigRegionChanged.connect(self.update)
        self.color = color
        
    def paint(self, p, *args):
        bounds = self.mapRectFromParent(self.geometry())
        
        fullWidth = int(bounds.width())
        height = int(bounds.height())
        
        fromAxis, toAxis = self.vb.state['viewRange'][0]
        fromValue, toValue = self.linearRegionItem.getRegion()
        
        regionWidth = fullWidth*(toValue-fromValue)/(toAxis-fromAxis)
        fromValueInAxisFrame = (fromValue-fromAxis)*fullWidth/(toAxis-fromAxis)
        
        padding = 5
        p.fillRect(QtCore.QRectF(fromValueInAxisFrame, 0, regionWidth, height - padding), pg.mkBrush(self.color))
    
if __name__ == "__main__":
    app = pg.mkQApp()
    
    p = pg.plot()
    region = pg.LinearRegionItem()
    p.addItem(region)
    pi = RegionIndicatorWidget(p.plotItem.vb, region, "b")
    p.plotItem.layout.addItem(pi, 0, 1)

    app.exec_()
