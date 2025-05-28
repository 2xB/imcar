import pyqtgraph as pg
import numpy as np
from matplotlib.colors import to_rgb

class ColoredGridAxis(pg.AxisItem):
    def __init__(self, *args, penColor, **kwargs):
        pg.AxisItem.__init__(self, *args, pen=penColor, **kwargs)
        
        self.gridColor = penColor
    
    def generateDrawSpecs(self, p):
        axisSpec, tickSpecs, textSpecs = pg.AxisItem.generateDrawSpecs(self, p)
        for tickSpec in tickSpecs:
            tickPen = tickSpec[0]
            alpha = tickPen.color().alpha()
            color = pg.mkColor(self.gridColor)
            color.setAlpha(alpha)
            tickPen.setColor(color)
            
        return (axisSpec, tickSpecs, textSpecs)

class CalibratedAxis(ColoredGridAxis):
    def __init__(self, originalAxis, orientation, shift=0, scale=1):
        
        self.originalAxis = originalAxis
        self.calShift = shift
        self.calScale = scale
        
        self.mn = 0
        self.mx = 0
        
        color = pg.mkColor(255*np.array(
                to_rgb(
                    "C1"
                    )
            ))
        
        ColoredGridAxis.__init__(self, orientation=orientation, penColor=color)
        
    def setCalibration(self, shift, scale):
        self.calShift = shift
        self.calScale = scale
        
        self.setRange(self.mn, self.mx)
        self.update()
    
    def setRange(self, mn, mx):
        self.mn = mn
        self.mx = mx
        
        calMN = (mn - self.calShift)*self.calScale
        calMX = (mx - self.calShift)*self.calScale
        return pg.AxisItem.setRange(self, calMN, calMX)
    
    def applyToValue(self, value):
        return (value - self.calShift)*self.calScale
    
    def applyToDistance(self, dist):
        return dist*np.abs(self.calScale)
        
if __name__ == '__main__':
    app = pg.mkQApp()
    
    pw = pg.PlotWidget()
    pw.show()
    pw.setWindowTitle('pyqtgraph example: MultipleXAxes')
    p1 = pw.plotItem
    p1.setLabels(left='axis 1')

    if False:
        color = pg.mkColor(255*np.array(
                to_rgb(
                    "C2"
                    )
            ))
        baxis = ColoredGridAxis(orientation="bottom", penColor=color)
        p1.setAxisItems({"bottom":baxis})

    caxis = CalibratedAxis(originalAxis=p1.getAxis("bottom"), orientation='top')
    caxis.setLabel('Calibrated axis')
    caxis.setCalibration(1, 0.003)
    p1.setAxisItems({"top":caxis})
    pw.showGrid(True, True)

    p1.plot(np.arange(1, 7), [1,2,4,8,16,32])
    
    app.exec_()
