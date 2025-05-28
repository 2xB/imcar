import os, sys
import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui, uic
import pyqtgraph as pg
from matplotlib.colors import to_rgb

import matplotlib.pyplot as plt

class CalibrationDialog(QtWidgets.QDialog):
    instance = None
    
    def __init__(self, *args, **kwargs):
        QtWidgets.QDialog.__init__(self, *args, **kwargs)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'calibration_editor.ui'), self)
        
        self.c1widgets = (self.remove1, self.channel1, self.value1)
        self.c2widgets = (self.remove2, self.channel2, self.value2)
        self.c3widgets = (self.remove3, self.channel3, self.value3, self.label3)
        
        self.remove1.clicked.connect(lambda: self.removePoint(1))
        self.remove2.clicked.connect(lambda: self.removePoint(2))
        self.remove3.clicked.connect(lambda: self.removePoint(3))
        
        for widget in self.c1widgets[1:3] + self.c2widgets[1:3] + self.c3widgets[1:3]:
            widget.setMinimum(-np.inf)
            widget.setMaximum(np.inf)
            widget.setDecimals(6)
            widget.valueChanged.connect(lambda *args, **kwargs: self.updateVisibilities())
        
        self.add.clicked.connect(self.addClicked)
    
    def addClicked(self):
        if not self.channel3.isVisible():
            for widget in self.c3widgets:
                widget.setVisible(True)
            self.channel3.setValue(0)
            self.value3.setValue(0)

        elif not self.channel1.isVisible(): # C3 visible but not C1
            for widget in self.c1widgets:
                widget.setVisible(True)
            self.channel1.setValue(self.channel3.value())
            self.value1.setValue(self.value3.value())
            
            self.channel3.setValue(0)
            self.value3.setValue(0)

        self.updateVisibilities()
    
    def removePoint(self, id):
        if id == 1:
            for widget in self.c1widgets:
                widget.setVisible(False)
        
        if id == 2:
            for widget in self.c2widgets:
                widget.setVisible(False)
        
        if id == 3:
            for widget in self.c3widgets:
                widget.setVisible(False)
        
        self.updateVisibilities()
    
    def updateVisibilities(self):
        cal = self.getCalibration()
        visibleCount = len(cal)
        noteShown = visibleCount == 2 and \
                        (
                            cal[0][0] == cal[1][0] or \
                            cal[0][1] == cal[1][1]
                        )
        self.note.setVisible(noteShown)
        
        acceptable = visibleCount <= 2 and not noteShown
            
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(acceptable)
        
        self.add.setVisible(visibleCount < 2)

        return acceptable
    
    def getCalibration(self):
        
        # Assert always shown for "isVisible" to work
        visible = self.isVisible()
        self.show()
        
        cal = []
        for channel, value in [(self.channel1, self.value1), (self.channel2, self.value2), (self.channel3, self.value3)]:
            if channel.isVisible():
                cal.append((channel.value(), value.value()))
        
        self.setVisible(visible)
        
        return cal
    
    def showDialog(*args, cal1, cal2, calnew, **kwargs):
        if CalibrationDialog.instance is None:
            CalibrationDialog.instance = CalibrationDialog(*args, **kwargs)

        self = CalibrationDialog.instance
        
        if self.isVisible():
            return
        
        self.show()
        
        # Prepare UI
        c1visible =  cal1 is not None
        for widget in self.c1widgets:
            widget.setVisible(c1visible)
        
        if c1visible:
            self.channel1.setValue(cal1[0])
            self.value1.setValue(cal1[1])
        
        c2visible =  cal2 is not None
        for widget in self.c2widgets:
            widget.setVisible(c2visible)
        
        if c2visible:
            self.channel2.setValue(cal2[0])
            self.value2.setValue(cal2[1])
        
        c3visible =  calnew is not None
        for widget in self.c3widgets:
            widget.setVisible(c3visible)
        
        if c3visible:
            self.channel3.setValue(calnew[0])
            self.value3.setValue(calnew[1])

        self.updateVisibilities() # Has to happen after show, otherwise recognizing visibilities is broken
        

class CalibrationWidget(pg.GraphicsWidget):
    sigChanged = QtCore.pyqtSignal()
    sigUserChanged = QtCore.pyqtSignal()
    sigCalibrationChanged = QtCore.pyqtSignal()
    
    def __init__(self, parent, vb):
        pg.GraphicsWidget.__init__(self, parent)
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        self.layout = QtWidgets.QGraphicsGridLayout()
        self.layout.setContentsMargins(1,1,1,1)
        self.setLayout(self.layout)
        self.layout.setHorizontalSpacing(0)
        self.layout.setVerticalSpacing(0)
        
        self.label = pg.LabelItem(text="Calibration", parent=self)
        self.layout.addItem(self.label, 0, 1)
        
        self.vb = vb
        self.item = CalibrationTickSliderItem(parent=self, label=self.label, allowAdd=False, allowRemove=False, orientation="top")
        self.vb.sigXRangeChanged.connect(self.item.updateRange)
        
        self.layout.addItem(self.item, 1, 1)
        
        self.item.sigTicksChanged.connect(self.sigChanged.emit)
        self.item.sigUserChanged.connect(self.sigUserChanged.emit)
        self.item.sigCalibrationChanged.connect(self.sigCalibrationChanged)
        
        self.getCalibration = self.item.getCalibration

class CalibrationTickSliderItem(pg.TickSliderItem):
    sigUserChanged = QtCore.pyqtSignal()
    sigCalibrationChanged = QtCore.pyqtSignal()
    
    def __init__(self, parent, label, **kwds):
        pg.TickSliderItem.__init__(self, parent=parent, **kwds)

        self.color = np.array(to_rgb("C1"))*255*0.2
        
        self.tickPositions = {}
        self.label = label
        
        editText = "Calibration: Edit point"
        addManuallyText  = "Calibration: Add point manually"
        addFittedText  = "Calibration: Add fitted point"
        
        self.tickUser = self.addTick(0.7, color=None, hoverColor="C2", hoverText=addManuallyText, clickCallback=self.addUserTick, movable=False)
        self.tickFit = self.addTick(0.5, color="C1", hoverColor="C2", hoverText=addFittedText, clickCallback=self.addFitTick, movable=False)
        self.tickCal1 = self.addTick(0, color="C2", hoverColor="C2", hoverText=editText, clickCallback=self.editTick, movable=False)
        self.tickCal2 = self.addTick(1, color="C2", hoverColor="C2", hoverText=editText, clickCallback=self.editTick, movable=False)
        
        self._range = [0,1]
        
        self.sigUserChanged.connect(self.updateTicks)
        
        self.cal1 = None
        self.cal2 = None
        
        CalibrationDialog.instance.accepted.connect(self.calibrationUpdated)
        self.updateVisibilities()
        self.updateFittedTick(False)
    
    def updateFittedTick(self, visible, pos=0):
        self.tickFit.setVisible(visible)
        self.tickPositions[self.tickFit] = pos
        self.rescaleTicks()
        
    def calibrationUpdated(self):
        cal = CalibrationDialog.instance.getCalibration()
        if len(cal) == 0:
            self.cal1 = None
            self.cal2 = None
        
        if len(cal) == 1:
            self.cal1, = cal
            self.cal2 = None
        
        if len(cal) == 2:
            self.cal1, self.cal2 = cal

        self.updateVisibilities()
        self.sigCalibrationChanged.emit()
    
    def updateVisibilities(self):
        self.tickCal1.setVisible(False)
        self.tickCal2.setVisible(False)
        if self.cal1 is not None:
            self.tickPositions[self.tickCal1] = self.cal1[0]
            self.tickCal1.setVisible(True)
        if self.cal2 is not None:
            self.tickPositions[self.tickCal2] = self.cal2[0]
            self.tickCal2.setVisible(True)
        self.rescaleTicks()
    
    def editTick(self):
        CalibrationDialog.showDialog(cal1=self.cal1, cal2=self.cal2, calnew=None)
    
    def addFitTick(self):
        CalibrationDialog.showDialog(cal1=self.cal1, cal2=self.cal2, calnew=(self.tickPositions[self.tickFit], 0))
    
    def addUserTick(self):
        CalibrationDialog.showDialog(cal1=self.cal1, cal2=self.cal2, calnew=(self.tickPositions[self.tickUser], 0))
    
    def addTick(self, pos, *args, color, hoverColor, hoverText, clickCallback, **kwargs):
        tick = pg.TickSliderItem.addTick(self, pos, *args, **kwargs)
        
        # Colors
        if color is not None:
            tick.color = np.array(to_rgb(color))*255
            tick.pen = pg.mkPen(np.array(to_rgb(color))*255*0.5, width=3)
        else:
            tick.color = None
            tick.pen = pg.mkPen(None)
        if hoverColor is not None:
            tick.hoverPen = pg.mkPen(np.array(to_rgb(hoverColor))*255*0.7, width=3)
        else:
            tick.hoverPen = tick.pen
        tick.currentPen = tick.pen
        tick.update()
        tick.sigClicked.connect(clickCallback)
        
        self.tickPositions[tick] = pos
        
        # Monkey patch tick to have hover signals
        
        label = self.label
        
        pgTick = tick.__class__
        class HoverSignalTick(pgTick):
            def hoverEvent(self, ev):
                if not ev.isExit() and ev.acceptClicks(QtCore.Qt.LeftButton):
                    label.setText(hoverText)
                pgTick.hoverEvent(self, ev)
        
        tick.__class__ = HoverSignalTick
        
        return tick
    
    def hoverEvent(self, ev):
        if (not ev.isExit()):
            if ev.acceptClicks(QtCore.Qt.LeftButton):
                # If top level item
                pos = ev.pos()
                pos.setY(self.tickUser.pos().y())
                self.tickMoved(self.tickUser, pos)
        else:
            # Hover out
            self.label.setText("Calibration")
            
    
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
        for tick, pos in self.tickPositions.items():
            self.setTickValueFromRange(pos, tick, self._range)
    
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
        for tick in self.tickPositions:
            self.tickPositions[tick] = self.getTickValueFromRange(tick, self._range)
    
    def resizeEventHandler(self, ev):
        pg.TickSliderItem.resizeEvent(self, ev)
        self.rescaleTicks()
    
    def getCalibration(self):
        # val1 = (orig1 - shift) * scale
        # val2 = (orig2 - shift) * scale
        # val1 - val2 = (orig1-orig2) * scale
        # => scale = (val1 - val2) / (orig1-orig2)
        # shift = orig1 - val1/scale
        
        if self.cal1 is None or self.cal2 is None:
            return None
        
        orig1, val1 = self.cal1
        orig2, val2 = self.cal2
        
        scale = (val1 - val2) / (orig1-orig2)
        shift = orig1 - val1/scale
        return shift, scale

    def paint(self, p, *args):
        bounds = self.mapRectFromParent(self.geometry())
        
        fullWidth = int(bounds.width())
        height = int(bounds.height())
        
        padding_top = 10
        padding_bottom = 5
        p.fillRect(QtCore.QRectF(0, padding_bottom, fullWidth, height - padding_top - padding_bottom), pg.mkBrush(self.color))

if __name__ == "__main__":
    import faulthandler
    faulthandler.enable()

    from custom_axes import ColoredGridAxis, CalibratedAxis
    
    app = pg.mkQApp()

    pw = pg.PlotWidget()
    pw.show()
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
    
    CalibrationDialog.instance = CalibrationDialog(parent=pw)

    caxis = CalibratedAxis(originalAxis=p1.getAxis("bottom"), orientation='top')
    caxis.setLabel('Calibrated axis')
    caxis.setCalibration(1, 0.003)
    p1.setAxisItems({"top":caxis})
    pw.showGrid(True, True)
    
    caxis.setVisible(False)

    p1.plot(np.arange(1, 7), [1,2,4,8,16,32])
    
    cw = CalibrationWidget(parent=p1, vb=p1.getViewBox())
    
    def calibrationChanged():
        cal = cw.getCalibration()
        if cal is not None:
            caxis.setCalibration(*cal)
            caxis.setVisible(True)
        else:
            caxis.setVisible(False)
    
    cw.sigCalibrationChanged.connect(calibrationChanged)
    p1.layout.addItem(cw, 0,1)
    
    sys.exit(app.exec_())
