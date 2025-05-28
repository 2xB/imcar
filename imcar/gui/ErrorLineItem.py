import pyqtgraph as pg
import numpy as np
import warnings

class ErrorLineItem(pg.ErrorBarItem):
    def __init__(self, *args, **kwargs):
        pg.ErrorBarItem.__init__(self, *args, **kwargs)
        self.xlog = False
        self.ylog = False
    
    def setLogMode(self, xState, yState):
        self.xlog = xState
        self.ylog = yState
        self.path = None
        self.update()
        
    def drawPath(self):
        p = pg.QtGui.QPainterPath()
        
        x, y = self.opts['x'], self.opts['y']
        if x is None or y is None:
            self.path = p
            return
        
        beam = self.opts['beam']
        
        top, bottom = self.opts['top'], self.opts['bottom']
        if top is not None or bottom is not None:
            if beam is not None and beam > 0:
                x1 = x - beam/2.
                x2 = x + beam/2.
                
                if self.xlog:
                    with warnings.catch_warnings():
                        warnings.filterwarnings('ignore', r'divide by zero encountered in log10')
                        warnings.filterwarnings('ignore', r'invalid value encountered in log10')
                        x1 = np.log10(x1)
                        x2 = np.log10(x2)

                x1_x2 = pg.functions.interweaveArrays(x1, x2)
                if top is not None:
                    y2 = y + top
                    if self.ylog:
                        with warnings.catch_warnings():
                            warnings.filterwarnings('ignore', r'divide by zero encountered in log10')
                            warnings.filterwarnings('ignore', r'invalid value encountered in log10')
                            y2 = np.log10(y2)
                    
                    y2s = pg.functions.interweaveArrays(y2, y2)
                    topEnds = pg.functions.arrayToQPath(x1_x2, y2s, connect="pairs")
                    p.addPath(topEnds)

                if bottom is not None:
                    y1 = y - bottom
                    if self.ylog:
                        with warnings.catch_warnings():
                            warnings.filterwarnings('ignore', r'divide by zero encountered in log10')
                            warnings.filterwarnings('ignore', r'invalid value encountered in log10')
                            y1 = np.log10(y1)
                    
                    y1s = pg.functions.interweaveArrays(y1, y1)
                    bottomEnds = pg.functions.arrayToQPath(x1_x2, y1s, connect="pairs")
                    p.addPath(bottomEnds)
                    
        self.path = p
        self.prepareGeometryChange()
