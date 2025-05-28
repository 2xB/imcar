import os, sys
import numpy as np

from pyqtgraph.Qt import QtGui, QtCore, QT_LIB, QtWidgets, uic
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
            print("Already visible")
            return
        
        print("Open dialog")
        
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
        
        self.show()

        self.updateVisibilities() # Has to happen after show, otherwise recognizing visibilities is broken


if __name__ == "__main__":
    import faulthandler
    faulthandler.enable()
    
    app = pg.mkQApp()
    
    def show():
        CalibrationDialog.showDialog(cal1=(-1, 1), cal2=(-2, 2), calnew=None)
    show()
    CalibrationDialog.instance.accepted.connect(show)
    
    sys.exit(app.exec_())
