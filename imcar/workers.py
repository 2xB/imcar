from PyQt5 import QtCore

class FittingWorker(QtCore.QThread):
    last_fit_info = None
    _fit_info = None

    # Bound Signals
    signal_new = QtCore.pyqtSignal()
    signal_update = QtCore.pyqtSignal()

    def __init__(self, parent):
        super(FittingWorker, self).__init__(parent)
        self.signal_new.connect(self.runfit)

    @property
    def fit_info(self):
        return self._fit_info    
    
    @fit_info.setter
    def fit_info(self, value):
        self._fit_info = value
        self.signal_new.emit()

    def runfit(self):
        if self.fit_info is not None:
            self.last_fit_info = self.fit_info
            self.fit_info = None
            self.last_fit_info.run()
            self.signal_update.emit()
